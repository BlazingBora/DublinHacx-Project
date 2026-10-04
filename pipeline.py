import base64
import json
import mimetypes
import os
import time
from datetime import date, datetime

from dotenv import load_dotenv
from openai import OpenAI


# ==========================================
# SETUP
# ==========================================

load_dotenv()

API_KEY = os.getenv("AZURE_API_KEY")
ENDPOINT = os.getenv("AZURE_ENDPOINT")

if not API_KEY or not ENDPOINT:
    # Don't crash at import - that turns every page (even the home page)
    # into a 500 on Vercel. AI calls will fail and show an error instead.
    print(
        "WARNING: AZURE_API_KEY / AZURE_ENDPOINT is not set. Add them to "
        ".env locally, or to the project's Environment Variables on Vercel."
    )

AI_NOT_CONFIGURED = (
    "The AI service isn't configured on this server: AZURE_API_KEY / "
    "AZURE_ENDPOINT are not set."
)

client = OpenAI(
    api_key=API_KEY or "missing-azure-api-key",
    base_url=ENDPOINT or "https://missing-azure-endpoint.invalid",
    # Default is a 10 minute timeout with retries - far longer than
    # gunicorn's 120s worker timeout, so a stalled call would hang the page.
    timeout=45,
    max_retries=1
)

MODEL = "DeepSeek-V4.1-Flash"


# ==========================================
# OCR (via the model's vision input, instead of
# a local OCR engine - keeps the deployed app
# small and fast enough to run as a serverless
# function, with no model weights to load)
# ==========================================

def _encode_image(image_path):
    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or "image/jpeg"

    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def _vision_ocr(image_path, instruction, attempts=3, attempt_timeout=20):
    """
    The vision endpoint is unreliable in practice: a normal call finishes
    in a few seconds, but it occasionally just hangs until something
    aborts it. Waiting out the client's full default timeout (tuned for
    the much more consistent text-only calls) on every attempt would mean
    minutes of waiting before giving up, so each attempt here gets its own
    short timeout and we retry a few times with backoff instead.
    """

    image_data_url = _encode_image(image_path)
    fast_client = client.with_options(timeout=attempt_timeout, max_retries=0)

    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            response = fast_client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": instruction},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_data_url}
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )

            if not response.choices:
                last_error = "No response choices."
            else:
                message = response.choices[0].message

                if message is None or message.content is None:
                    last_error = "No OCR text returned."
                else:
                    return message.content.strip()

        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"

        print(f"\nOCR attempt {attempt}/{attempts} failed: {last_error}")

        if attempt < attempts:
            time.sleep(1.5 * attempt)

    print("\n========================================")
    print("OCR ERROR (all retries exhausted)")
    print("========================================")
    print(last_error)

    return ""


# ==========================================
# RECEIPT OCR
# ==========================================

def scan_receipt(image_path):

    print("\nScanning receipt with OCR...")

    return _vision_ocr(
        image_path,
        "Transcribe every line of text visible on this grocery receipt "
        "image, exactly as printed, preserving line breaks. Output only "
        "the transcribed text - no extra commentary."
    )


# ==========================================
# OCR TEXT → PRODUCTS
# ==========================================

def extract_products(receipt_text):

    print("\nCleaning receipt with AI...")

    prompt = f"""
You are an intelligent grocery receipt parser.

The text below was extracted from a grocery receipt using OCR.

OCR is imperfect and may contain:
- Misspelled words
- Letters mistaken for numbers
- Numbers mistaken for letters
- Product names split across multiple lines
- Product names mixed with barcodes
- Incorrect spacing

Your job is to reconstruct ONLY the products that were purchased.

========================================
REMOVE RECEIPT INFORMATION
========================================

Remove:

- Store name
- Store address
- Store phone number
- Date
- Time
- Transaction numbers
- Register numbers
- Cashier information
- Payment information
- Credit/debit card information
- Subtotal
- Tax
- Total
- Change
- Discounts
- Coupons
- Loyalty information
- Rewards points
- Barcode numbers
- Receipt IDs
- Random numbers
- "Thank you for shopping"
- Other receipt metadata

========================================
KEEP PRODUCTS
========================================

Keep:

- Food
- Vegetables
- Fruit
- Meat
- Dairy
- Drinks
- Snacks
- Canned food
- Frozen food
- Household products
- Personal care products

========================================
CORRECT OCR ERRORS
========================================

Use context to correct obvious OCR mistakes.

Examples:

"HAWAIIAN HULAPENO" → "Hawaiian Jalapeno"
"bananna" → "banana"
"m1lk" → "milk"
"CHKN BRST" → "Chicken Breast"

If a product name is split across multiple lines,
combine the lines.

For example:

"SIG PINTO"
"BEANS"

should become:

"Pinto Beans"

Do NOT invent products.

Only include products that are reasonably supported
by the OCR text.

========================================
RECEIPT DATE
========================================

Also find the transaction date printed on the receipt itself
(when it was purchased) - not an expiration date on a product,
a due date, or anything else. Receipts usually print this near
the top or bottom, often next to a time stamp.

========================================
OUTPUT
========================================

Return ONLY valid JSON.

Use exactly this structure:

{{
    "receipt_date": "YYYY-MM-DD",
    "items": [
        {{
            "name": "Hawaiian Jalapeno",
            "quantity": 1,
            "price": 2.99
        }}
    ]
}}

Rules:

1. Every item must represent something actually purchased.
2. Do not include receipt metadata.
3. Correct obvious OCR spelling mistakes.
4. Combine product names split across lines.
5. Keep names simple and readable.
6. If quantity is unclear, use 1.
7. If price is unclear, use null.
8. Never invent products.
9. receipt_date is the purchase date in YYYY-MM-DD format. If no
   date appears on the receipt, or it's too garbled to trust, use null.
   Never invent a date or substitute today's date.
10. Return ONLY JSON.
11. Do not explain your answer.

OCR TEXT:

{receipt_text}
"""

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=2000
        )

        if not response.choices:
            print("ERROR: No response choices.")
            return [], None

        message = response.choices[0].message

        if message is None:
            print("ERROR: No message returned.")
            return [], None

        result = message.content

        if result is None:
            print("\nERROR: Model returned no text.")
            return [], None

        # Remove markdown code fences
        result = result.replace("```json", "")
        result = result.replace("```", "")
        result = result.strip()

        # Find JSON object if model included extra text
        start = result.find("{")
        end = result.rfind("}")

        if start != -1 and end != -1:
            result = result[start:end + 1]

        data = json.loads(result)

        return data.get("items", []), data.get("receipt_date")

    except Exception as e:

        print("\n========================================")
        print("AI PROCESSING ERROR")
        print("========================================")

        print(type(e).__name__)
        print(str(e))

        return [], None


# ==========================================
# PRODUCTS → EXPIRATION DATES
# ==========================================

def estimate_expiration(items, purchase_date=None):

    print("\nEstimating expiration dates...")

    today = date.today()
    reference_date = purchase_date or today.isoformat()

    prompt = f"""
You are a grocery inventory assistant.

These products were purchased on {reference_date}. Today's date is {today}.

Given the grocery products below, estimate how long each product
typically remains usable when stored properly, COUNTING FROM THE
PURCHASE DATE ({reference_date}), not from today. Food starts aging
from the moment it's bought, not from when it happens to get scanned.

These are estimates only.

Do NOT claim to know the manufacturer's exact
expiration date.

========================================
OUTPUT
========================================

Return ONLY valid JSON:

{{
    "items": [
        {{
            "name": "Milk",
            "quantity": 1,
            "price": 4.99,
            "estimated_days": 7,
            "estimated_expiration": "YYYY-MM-DD",
            "storage": "refrigerator",
            "storage_tip": "Keep toward the back of the fridge, not the door, to stay coldest.",
            "stale_use_tip": null,
            "grace_days": 0,
            "category": "grocery"
        }}
    ]
}}

========================================
RULES
========================================

- category is "medication" for medicines and health products taken
  as a drug: OTC or prescription pills, cough/cold syrups, pain
  relievers, allergy tablets, antacids, vitamins and supplements.
  Everything else (food, drinks, household and personal care items
  like soap or shampoo) is "grocery".
- For a medication, estimate a typical unopened shelf-life (often
  1-3 years), use "medicine cabinet" or similar for storage, and use
  null for stale_use_tip and 0 for grace_days - expired medicine
  should never be used.

- Use reasonable typical shelf-life estimates.
- Consider refrigeration, freezing, or pantry storage.
- Calculate estimated_expiration as the purchase date ({reference_date})
  plus the typical shelf-life, not today's date plus shelf-life.
- Do not invent exact manufacturer expiration dates.
- If an item cannot reasonably be estimated, use null.
- Keep the original product name.
- storage_tip is one short, practical sentence (under 15 words) that
  would meaningfully extend this specific item's freshness. If there
  is nothing non-obvious to add, use null.
- stale_use_tip and grace_days describe what happens shortly AFTER the
  estimated_expiration date passes:
    - For items that are genuinely unsafe once expired (raw meat, fish,
      dairy, eggs, deli/prepared food, leftovers) use null for
      stale_use_tip and 0 for grace_days - there is no "still fine"
      window, they should be thrown away right at expiration.
    - For items that degrade gracefully and stay USABLE (not necessarily
      tasty-fresh) for a while past their date - bread, hard cheese,
      root vegetables, rice, pasta, crackers, many pantry/canned goods -
      set grace_days to a reasonable number of extra days they're still
      usable for, and stale_use_tip to one short, practical suggestion
      for using it in that stale state (e.g. "Past its best, but fine
      toasted or turned into croutons/breadcrumbs.").
    - stale_use_tip must never suggest eating something unsafe. If in
      doubt, use null/0.
- Return ONLY JSON.
- Do not explain your answer.

PRODUCTS:

{json.dumps(items, indent=2)}
"""

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=2000
        )

        if not response.choices:
            print("ERROR: No response choices.")
            return []

        message = response.choices[0].message

        if message is None:
            print("ERROR: No message returned.")
            return []

        result = message.content

        if result is None:
            print("\nERROR: Model returned no text.")
            return []

        result = result.replace("```json", "")
        result = result.replace("```", "")
        result = result.strip()

        start = result.find("{")
        end = result.rfind("}")

        if start != -1 and end != -1:
            result = result[start:end + 1]

        data = json.loads(result)

        return data.get("items", [])

    except Exception as e:

        print("\n========================================")
        print("EXPIRATION AI ERROR")
        print("========================================")

        print(type(e).__name__)
        print(str(e))

        return []


# ==========================================
# FULL PIPELINE
# ==========================================

def process_receipt(image_path):
    """
    Runs OCR -> product extraction -> expiration estimation
    on a receipt image and returns (inventory, receipt_date, error_message).
    """

    if not API_KEY or not ENDPOINT:
        return [], None, AI_NOT_CONFIGURED

    receipt_text = scan_receipt(image_path)

    if not receipt_text:
        return [], None, "OCR found no text in this image."

    products, receipt_date = extract_products(receipt_text)

    if not products:
        return [], receipt_date, "No products were detected on this receipt."

    inventory = estimate_expiration(products, purchase_date=receipt_date)

    if not inventory:
        return [], receipt_date, "Expiration estimation failed."

    return inventory, receipt_date, None


# ==========================================
# FREE-TEXT STATEMENT -> PRODUCTS
# ==========================================

def extract_products_from_statement(statement):
    """
    Parses a plain-language sentence about a purchase (e.g. "bought 2
    avocados and a gallon of milk yesterday") into structured items,
    without needing a receipt photo.
    """

    print("\nParsing grocery statement with AI...")

    today = date.today()

    prompt = f"""
You are an intelligent grocery inventory assistant.

Today's date is {today}.

A user typed a casual, plain-language sentence describing groceries
they bought. Extract the individual products mentioned.

Examples of input:

"bought 2 avocados and a gallon of milk yesterday"
"got some bread, a dozen eggs, and 3 bananas"
"picked up chicken breast and spinach on Monday"

========================================
OUTPUT
========================================

Return ONLY valid JSON, using exactly this structure:

{{
    "purchase_date": "YYYY-MM-DD",
    "items": [
        {{
            "name": "Avocado",
            "quantity": 2,
            "price": null
        }}
    ]
}}

Rules:

1. Extract every distinct grocery product mentioned.
2. Use singular, capitalized product names (e.g. "Avocado" not "avocados").
3. If a quantity is given, use it. Otherwise use 1.
4. Never invent a price - always use null unless a price is explicitly stated.
5. purchase_date: resolve any relative time reference ("yesterday",
   "last Monday", "3 days ago") against today's date ({today}) into an
   absolute YYYY-MM-DD date. If no time is mentioned at all, use today's
   date ({today}).
6. Ignore anything that isn't a purchasable product. Keep store-bought
   medications too (e.g. "Tylenol", "NyQuil", "vitamin D") - they are
   sorted into a separate medications list later.
7. If nothing resembling a grocery purchase is found, return an empty
   items list.
8. Return ONLY JSON. Do not explain your answer.

STATEMENT:

{statement}
"""

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=1200
        )

        if not response.choices:
            print("ERROR: No response choices.")
            return [], None

        message = response.choices[0].message

        if message is None:
            print("ERROR: No message returned.")
            return [], None

        result = message.content

        if result is None:
            print("\nERROR: Model returned no text.")
            return [], None

        result = result.replace("```json", "")
        result = result.replace("```", "")
        result = result.strip()

        start = result.find("{")
        end = result.rfind("}")

        if start != -1 and end != -1:
            result = result[start:end + 1]

        data = json.loads(result)

        return data.get("items", []), data.get("purchase_date")

    except Exception as e:

        print("\n========================================")
        print("STATEMENT PARSING ERROR")
        print("========================================")

        print(type(e).__name__)
        print(str(e))

        return [], None


def process_statement(statement):
    """
    Runs free-text parsing -> expiration estimation on a typed grocery
    statement and returns (inventory, purchase_date, error_message).
    """

    if not API_KEY or not ENDPOINT:
        return [], None, AI_NOT_CONFIGURED

    statement = (statement or "").strip()

    if not statement:
        return [], None, "Type something about what you bought first."

    products, purchase_date = extract_products_from_statement(statement)

    if not products:
        return [], purchase_date, "Couldn't find any groceries in that. Try describing what you bought."

    inventory = estimate_expiration(products, purchase_date=purchase_date)

    if not inventory:
        return [], purchase_date, "Expiration estimation failed."

    return inventory, purchase_date, None


# ==========================================
# MEDICATION LABEL OCR
# ==========================================

def scan_medication_label(image_path):
    """
    OCR a medication bottle/box label. Labels are denser and less
    structured than receipts, so this keeps more of the raw text
    and leaves filtering to the LLM extraction step.
    """

    print("\nScanning medication label with OCR...")

    return _vision_ocr(
        image_path,
        "Transcribe every line of text visible on this medication "
        "bottle/box label image, exactly as printed, preserving line "
        "breaks. Output only the transcribed text - no extra commentary."
    )


# ==========================================
# OCR TEXT -> MEDICATIONS
# ==========================================

def extract_medications(label_text):

    print("\nExtracting medication details with AI...")

    prompt = f"""
You are an intelligent medication label parser.

The text below was extracted from a prescription or OTC
medication bottle/box using OCR. OCR is imperfect and may
contain misspellings, split words, or jumbled line order.

========================================
EXTRACT
========================================

For each distinct medication on the label, extract:

- name (drug name, generic or brand; correct obvious OCR errors)
- dosage (e.g. "500mg", "10mg/5mL"), null if not present
- quantity (number of pills/tablets/mL in the container), null if unclear
- expiration_date in YYYY-MM-DD format, EXACTLY as printed on the
  label (do not estimate or invent one). If the label only has a
  month/year, use the first day of that month. If no expiration
  date appears, use null.
- refills_left (integer), null if not present
- instructions (short, e.g. "Take 1 tablet by mouth twice daily"),
  null if not present

========================================
OUTPUT
========================================

Return ONLY valid JSON, using exactly this structure:

{{
    "items": [
        {{
            "name": "Amoxicillin",
            "dosage": "500mg",
            "quantity": 30,
            "expiration_date": "2027-03-01",
            "refills_left": 2,
            "instructions": "Take 1 capsule by mouth three times daily"
        }}
    ]
}}

Rules:

1. Never invent an expiration date that is not supported by the text.
2. Correct obvious OCR spelling mistakes in drug names.
3. If nothing resembling a medication is found, return an empty list.
4. Return ONLY JSON. Do not explain your answer.

LABEL TEXT:

{label_text}
"""

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=2000
        )

        if not response.choices:
            print("ERROR: No response choices.")
            return []

        message = response.choices[0].message

        if message is None:
            print("ERROR: No message returned.")
            return []

        result = message.content

        if result is None:
            print("\nERROR: Model returned no text.")
            return []

        result = result.replace("```json", "")
        result = result.replace("```", "")
        result = result.strip()

        start = result.find("{")
        end = result.rfind("}")

        if start != -1 and end != -1:
            result = result[start:end + 1]

        data = json.loads(result)

        return data.get("items", [])

    except Exception as e:

        print("\n========================================")
        print("MEDICATION PROCESSING ERROR")
        print("========================================")

        print(type(e).__name__)
        print(str(e))

        return []


# ==========================================
# MEDICATION FULL PIPELINE
# ==========================================

def process_medication(image_path):
    """
    Runs OCR -> medication extraction on a label image and returns
    (medications, error_message).
    """

    if not API_KEY or not ENDPOINT:
        return [], AI_NOT_CONFIGURED

    label_text = scan_medication_label(image_path)

    if not label_text:
        return [], "OCR found no text on this label."

    medications = extract_medications(label_text)

    if not medications:
        return [], "No medication details were detected on this label."

    return medications, None


# ==========================================
# RECIPE GENERATION
# ==========================================

def generate_recipe(ingredient_names):
    """
    Generates one recipe that makes use of the given ingredient
    names. Returns a dict on success, or None on failure.
    """

    print("\nGenerating recipe...")

    prompt = f"""
You are a helpful home cooking assistant.

The user has these ingredients available, which are nearing
their expiration date and should be used soon:

{json.dumps(ingredient_names, indent=2)}

Suggest ONE simple recipe that uses as many of these
ingredients as possible. You may assume the user has common
pantry staples (salt, pepper, oil, water, basic spices) even
if not listed, but call those out separately from the
tracked ingredients.

========================================
OUTPUT
========================================

Return ONLY valid JSON, using exactly this structure:

{{
    "title": "Leftover Veggie Stir Fry",
    "servings": 2,
    "uses_ingredients": ["Broccoli", "Chicken Breast"],
    "additional_ingredients": ["salt", "oil", "soy sauce"],
    "steps": [
        "Heat oil in a pan over medium-high heat.",
        "..."
    ]
}}

Rules:

1. Prioritize using the tracked ingredients listed above.
2. Keep steps concise and practical.
3. Do not invent ingredients that contradict the list.
4. Return ONLY JSON. Do not explain your answer.
"""

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4,
            max_tokens=1200
        )

        if not response.choices:
            print("ERROR: No response choices.")
            return None

        message = response.choices[0].message

        if message is None:
            print("ERROR: No message returned.")
            return None

        result = message.content

        if result is None:
            print("\nERROR: Model returned no text.")
            return None

        result = result.replace("```json", "")
        result = result.replace("```", "")
        result = result.strip()

        start = result.find("{")
        end = result.rfind("}")

        if start != -1 and end != -1:
            result = result[start:end + 1]

        return json.loads(result)

    except Exception as e:

        print("\n========================================")
        print("RECIPE GENERATION ERROR")
        print("========================================")

        print(type(e).__name__)
        print(str(e))

        return None


# ==========================================
# FOOD / MEDICATION INTERACTION CHECKER
# ==========================================
#
# A small, curated set of well-documented food-drug interactions.
# This is a reference list for awareness only, not medical advice -
# matching is a simple keyword lookup, not a clinical system.

INTERACTION_RULES = [
    {
        "drug_keywords": ["warfarin", "coumadin"],
        "food_keywords": [
            "spinach", "kale", "broccoli", "leafy green",
            "collard", "brussels sprout", "cabbage"
        ],
        "risk": "High vitamin K content can reduce warfarin's blood-thinning effect.",
        "severity": "high"
    },
    {
        "drug_keywords": [
            "statin", "atorvastatin", "lipitor", "simvastatin",
            "zocor", "lovastatin"
        ],
        "food_keywords": ["grapefruit"],
        "risk": "Grapefruit can raise statin levels in the blood, increasing side-effect risk.",
        "severity": "high"
    },
    {
        "drug_keywords": [
            "tetracycline", "doxycycline", "ciprofloxacin", "cipro",
            "levofloxacin"
        ],
        "food_keywords": ["milk", "cheese", "yogurt", "dairy", "calcium"],
        "risk": "Calcium in dairy can bind to the antibiotic and reduce its absorption.",
        "severity": "medium"
    },
    {
        "drug_keywords": [
            "phenelzine", "tranylcypromine", "nardil", "parnate",
            "isocarboxazid", "maoi"
        ],
        "food_keywords": [
            "aged cheese", "cured meat", "salami", "pepperoni",
            "soy sauce", "wine", "beer"
        ],
        "risk": "Tyramine-rich foods can cause a dangerous blood pressure spike with MAOIs.",
        "severity": "high"
    },
    {
        "drug_keywords": [
            "lisinopril", "enalapril", "losartan", "valsartan",
            "spironolactone"
        ],
        "food_keywords": [
            "banana", "potato", "orange juice", "avocado", "coconut water"
        ],
        "risk": "High-potassium foods can push potassium to unsafe levels with this medication.",
        "severity": "medium"
    },
    {
        "drug_keywords": ["metronidazole", "flagyl", "disulfiram"],
        "food_keywords": ["beer", "wine", "alcohol"],
        "risk": "Alcohol with this medication can cause severe nausea, flushing, and vomiting.",
        "severity": "high"
    },
    {
        "drug_keywords": ["levothyroxine", "synthroid"],
        "food_keywords": ["coffee", "soy", "walnut", "calcium"],
        "risk": "These foods can reduce absorption of thyroid medication if taken too close together.",
        "severity": "low"
    },
]


def check_interactions(medication_names, grocery_names):
    """
    Cross-references tracked medications against tracked groceries
    using a curated keyword table. Returns a list of warning dicts:
    {drug, food, risk, severity}. Not medical advice.
    """

    warnings = []

    meds = [m.lower() for m in medication_names if m]
    foods = [g.lower() for g in grocery_names if g]

    for rule in INTERACTION_RULES:

        matched_drug = next(
            (
                med_name for med_name in meds
                if any(kw in med_name for kw in rule["drug_keywords"])
            ),
            None
        )

        if matched_drug is None:
            continue

        matched_food = next(
            (
                food_name for food_name in foods
                if any(kw in food_name for kw in rule["food_keywords"])
            ),
            None
        )

        if matched_food is None:
            continue

        warnings.append({
            "drug": matched_drug.title(),
            "food": matched_food.title(),
            "risk": rule["risk"],
            "severity": rule["severity"]
        })

    return warnings


# ==========================================
# RESULT ENRICHMENT (shared by web app + API)
# ==========================================

def _friendly_span(days):
    """Converts a day count into weeks/months/years wording for readability."""

    if days < 60:
        weeks = round(days / 7)
        return f"{weeks} week{'s' if weeks != 1 else ''}"

    if days < 330:
        months = round(days / 30)
        return f"{months} month{'s' if months != 1 else ''}"

    years = round(days / 365, 1)
    if years == int(years):
        years = int(years)
    return f"{years} year{'s' if years != 1 else ''}"


def humanize_expiration(date_str):
    """Turns 'YYYY-MM-DD' into ('In 5 days (Sat, Oct 10)', urgency, days_left)."""

    if not date_str:
        return "Unknown", "unknown", None

    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return date_str, "unknown", None

    days_left = (target - date.today()).days
    nice_date = target.strftime("%a, %b %d")

    if days_left < 0:
        words = f"Expired {abs(days_left)} day{'s' if abs(days_left) != 1 else ''} ago"
        urgency = "past"
    elif days_left == 0:
        words = "Expires today"
        urgency = "urgent"
    elif days_left == 1:
        words = "Expires tomorrow"
        urgency = "urgent"
    elif days_left <= 3:
        words = f"In {days_left} days"
        urgency = "urgent"
    elif days_left <= 7:
        words = f"In {days_left} days"
        urgency = "soon"
    else:
        words = f"In {_friendly_span(days_left)}"
        urgency = "fresh"

    return f"{words} ({nice_date})", urgency, days_left


def _should_suggest_freezing(item, urgency):
    """Flags perishable, refrigerated items that are about to expire."""

    if urgency not in ("urgent", "soon"):
        return False

    storage = (item.get("storage") or "").lower()

    return "refrigerat" in storage or "fridge" in storage


def _classify_past_expiration(item, days_left):
    """
    For an item already past its date, decides whether it's still usable
    in a diminished way (stale) or should be thrown out (danger).
    """

    overdue = abs(days_left)
    grace_days = item.get("grace_days") or 0
    stale_use_tip = item.get("stale_use_tip")

    if stale_use_tip and overdue <= grace_days:
        return "stale", stale_use_tip

    return "danger", None


def enrich_items(items):
    """Adds expiration_words, urgency, freeze_tip, stale_tip, and discard_tip to each item."""

    for item in items:
        words, urgency, days_left = humanize_expiration(item.get("estimated_expiration"))
        item["expiration_words"] = words

        stale_tip = None
        discard_tip = False

        if urgency == "past":
            urgency, stale_tip = _classify_past_expiration(item, days_left)
            discard_tip = stale_tip is None

            # An item past its date is either being used up stale or thrown
            # out - freshness-extension advice no longer applies either way.
            item["storage_tip"] = None

        item["urgency"] = urgency
        item["stale_tip"] = stale_tip
        item["discard_tip"] = discard_tip
        item["freeze_tip"] = _should_suggest_freezing(item, urgency)

    # Soonest-expiring first; items with no date sink to the bottom.
    items.sort(
        key=lambda i: i.get("estimated_expiration") or "9999-99-99"
    )

    return items
