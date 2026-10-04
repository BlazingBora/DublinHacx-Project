import os
import uuid

from flask import Flask, redirect, render_template, request, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

from api import api as api_blueprint
from inventory_db import add_items, list_items, remove_all_items, remove_items
from pipeline import (
    check_interactions,
    enrich_items,
    generate_recipe,
    process_medication,
    process_receipt,
    process_statement,
)
from recalls import check_food_recalls

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

CORS(app, resources={r"/api/*": {"origins": "*"}})
app.register_blueprint(api_blueprint)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def _save_upload(file):
    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    image_path = os.path.join(UPLOAD_DIR, filename)
    file.save(image_path)
    return image_path


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/scan", methods=["POST"])
def scan():
    file = request.files.get("receipt")

    if file is None or file.filename == "":
        return render_template(
            "index.html",
            error="Please choose a receipt image to upload."
        )

    if not allowed_file(file.filename):
        return render_template(
            "index.html",
            error="Unsupported file type. Please upload a PNG, JPG, or WEBP image."
        )

    image_path = _save_upload(file)

    try:
        inventory, receipt_date, error = process_receipt(image_path)
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

    if error:
        return render_template("index.html", error=error)

    add_items(inventory, source="grocery", purchase_date=receipt_date)

    return redirect(url_for("inventory", added=len(inventory)))


@app.route("/add-statement", methods=["POST"])
def add_statement():
    statement = request.form.get("statement", "")

    inventory, purchase_date, error = process_statement(statement)

    if error:
        return render_template("index.html", error=error)

    add_items(inventory, source="grocery", purchase_date=purchase_date)

    return redirect(url_for("inventory", added=len(inventory)))


@app.route("/scan-medication", methods=["POST"])
def scan_medication():
    file = request.files.get("medication")

    if file is None or file.filename == "":
        return render_template(
            "index.html",
            error="Please choose a medication label photo to upload."
        )

    if not allowed_file(file.filename):
        return render_template(
            "index.html",
            error="Unsupported file type. Please upload a PNG, JPG, or WEBP image."
        )

    image_path = _save_upload(file)

    try:
        medications, error = process_medication(image_path)
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

    if error:
        return render_template("index.html", error=error)

    for med in medications:
        med["estimated_expiration"] = med.get("expiration_date")

    add_items(medications, source="medication")

    return redirect(url_for("inventory", added=len(medications)))


@app.route("/recipe", methods=["POST"])
def recipe():
    ingredients = [name for name in request.form.getlist("ingredient") if name]

    if not ingredients:
        return render_template(
            "index.html",
            error="Select at least one ingredient to build a recipe."
        )

    recipe_data = generate_recipe(ingredients)

    if recipe_data is None:
        return render_template(
            "index.html",
            error="Couldn't generate a recipe from those ingredients. Try again."
        )

    return render_template("recipe.html", recipe=recipe_data)


@app.route("/inventory", methods=["GET"])
def inventory():
    groceries = enrich_items(list_items(source="grocery"))
    medications = enrich_items(list_items(source="medication"))

    grocery_names = [g.get("name") for g in groceries if g.get("name")]

    interactions = check_interactions(
        [m.get("name") for m in medications if m.get("name")],
        grocery_names
    )

    return render_template(
        "inventory.html",
        groceries=groceries,
        medications=medications,
        interactions=interactions,
        removed=request.args.get("removed", type=int),
        added=request.args.get("added", type=int)
    )


@app.route("/inventory/remove", methods=["POST"])
def inventory_remove():
    ids = request.form.getlist("item_id")
    removed = remove_items(ids)

    return redirect(url_for("inventory", removed=removed))


@app.route("/inventory/remove-all/<source>", methods=["POST"])
def inventory_remove_all(source):
    if source not in ("grocery", "medication"):
        return redirect(url_for("inventory"))

    removed = remove_all_items(source)

    return redirect(url_for("inventory", removed=removed))


@app.route("/recalls", methods=["GET"])
def recalls_page():
    grocery_names = [
        item.get("name") for item in list_items(source="grocery") if item.get("name")
    ]

    return render_template("recalls.html", recalls=check_food_recalls(grocery_names))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
