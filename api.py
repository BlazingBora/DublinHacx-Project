import json
import os
import tempfile
import uuid

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from device import get_device_id
from inventory_db import add_classified_items, add_items, list_items, remove_items
from pipeline import (
    check_interactions,
    enrich_items,
    generate_recipe,
    process_medication,
    process_receipt,
    process_statement,
)
from recalls import check_food_recalls

api = Blueprint("api", __name__, url_prefix="/api")

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "xpirescan-uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

os.makedirs(UPLOAD_DIR, exist_ok=True)


def _allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def _save_upload(file):
    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    image_path = os.path.join(UPLOAD_DIR, filename)
    file.save(image_path)
    return image_path


def _parse_name_list(raw):
    """Parses an optional JSON-array-of-strings form field, e.g. '["Milk","Warfarin"]'."""

    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []

    if not isinstance(parsed, list):
        return []

    return [str(name) for name in parsed if name]


@api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@api.route("/scan", methods=["POST"])
def api_scan():
    file = request.files.get("receipt")

    if file is None or file.filename == "":
        return jsonify({"error": "Please attach a receipt image."}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type. Use PNG, JPG, or WEBP."}), 400

    known_medications = _parse_name_list(request.form.get("known_medications"))

    image_path = _save_upload(file)

    try:
        inventory, receipt_date, error = process_receipt(image_path)
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

    if error:
        return jsonify({"error": error}), 422

    groceries, medications = add_classified_items(inventory, get_device_id(), purchase_date=receipt_date)

    grocery_names = [item.get("name") for item in groceries if item.get("name")]
    medication_names = [item.get("name") for item in medications if item.get("name")]
    interactions = check_interactions(known_medications + medication_names, grocery_names)
    recalls = check_food_recalls(grocery_names)

    return jsonify({
        "items": enrich_items(inventory),
        "names": grocery_names,
        "interactions": interactions,
        "recalls": recalls,
        "receipt_date": receipt_date
    })


@api.route("/add-statement", methods=["POST"])
def api_add_statement():
    data = request.get_json(silent=True) or {}
    statement = data.get("statement", "")
    known_medications = [str(n) for n in data.get("known_medications", []) if n]

    inventory, purchase_date, error = process_statement(statement)

    if error:
        return jsonify({"error": error}), 422

    groceries, medications = add_classified_items(inventory, get_device_id(), purchase_date=purchase_date)

    grocery_names = [item.get("name") for item in groceries if item.get("name")]
    medication_names = [item.get("name") for item in medications if item.get("name")]
    interactions = check_interactions(known_medications + medication_names, grocery_names)
    recalls = check_food_recalls(grocery_names)

    return jsonify({
        "items": enrich_items(inventory),
        "names": grocery_names,
        "interactions": interactions,
        "recalls": recalls,
        "purchase_date": purchase_date
    })


@api.route("/scan-medication", methods=["POST"])
def api_scan_medication():
    file = request.files.get("medication")

    if file is None or file.filename == "":
        return jsonify({"error": "Please attach a medication label photo."}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type. Use PNG, JPG, or WEBP."}), 400

    known_groceries = _parse_name_list(request.form.get("known_groceries"))

    image_path = _save_upload(file)

    try:
        medications, error = process_medication(image_path)
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

    if error:
        return jsonify({"error": error}), 422

    for med in medications:
        med["estimated_expiration"] = med.get("expiration_date")

    add_items(medications, source="medication", device_id=get_device_id())

    medication_names = [med.get("name") for med in medications if med.get("name")]
    interactions = check_interactions(medication_names, known_groceries)

    return jsonify({
        "items": enrich_items(medications),
        "names": medication_names,
        "interactions": interactions
    })


@api.route("/inventory", methods=["GET"])
def api_inventory():
    groceries = enrich_items(list_items(get_device_id(), source="grocery"))
    medications = enrich_items(list_items(get_device_id(), source="medication"))

    grocery_names = [g.get("name") for g in groceries if g.get("name")]

    interactions = check_interactions(
        [m.get("name") for m in medications if m.get("name")],
        grocery_names
    )
    recalls = check_food_recalls(grocery_names)

    return jsonify({
        "groceries": groceries,
        "medications": medications,
        "interactions": interactions,
        "recalls": recalls
    })


@api.route("/inventory/remove", methods=["POST"])
def api_inventory_remove():
    data = request.get_json(silent=True) or {}
    ids = data.get("ids", [])

    removed = remove_items(ids, get_device_id())

    return jsonify({"removed": removed})


@api.route("/recipe", methods=["POST"])
def api_recipe():
    data = request.get_json(silent=True) or {}
    ingredients = [name for name in data.get("ingredients", []) if name]

    if not ingredients:
        return jsonify({"error": "Select at least one ingredient."}), 400

    recipe_data = generate_recipe(ingredients)

    if recipe_data is None:
        return jsonify({"error": "Couldn't generate a recipe from those ingredients."}), 422

    return jsonify({"recipe": recipe_data})
