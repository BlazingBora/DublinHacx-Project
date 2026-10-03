import os
import json
import pytesseract

from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI


# -----------------------------
# CONFIG
# -----------------------------

load_dotenv()

API_KEY = os.getenv("AZURE_API_KEY")
ENDPOINT = os.getenv("AZURE_ENDPOINT")

if not API_KEY or not ENDPOINT:
    raise ValueError(
        "AZURE_API_KEY / AZURE_ENDPOINT is missing from your .env file."
    )

client = OpenAI(
    api_key=API_KEY,
    base_url=ENDPOINT
)

MODEL = "DeepSeek-V4.1-Flash"

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# -----------------------------
# OCR
# -----------------------------

def scan_receipt(image_path):
    print("\n📷 Scanning receipt...")

    image = Image.open(image_path)

    text = pytesseract.image_to_string(image)

    print("\n--- OCR RESULT ---")
    print(text)
    print("------------------")

    return text


# -----------------------------
# EXTRACT PRODUCTS
# -----------------------------

def extract_products(receipt_text):

    print("\nFinding products...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": """
You extract purchased products from grocery receipts.

Ignore:
- store names
- subtotal
- tax
- total
- payment information
- credit/debit card information
- transaction numbers
- cashier information
- addresses
- dates unless they are clearly associated with a product

Return ONLY valid JSON.

The JSON must be an array of objects with:
- name
- quantity
- price

Example:

[
  {
    "name": "Milk",
    "quantity": 1,
    "price": 5.99
  }
]

Do not include markdown.
"""
            },
            {
                "role": "user",
                "content": receipt_text
            }
        ]
    )

    result = response.choices[0].message.content

    try:
        products = json.loads(result)
    except json.JSONDecodeError:
        print("Could not parse product response:")
        print(result)
        return []

    print("\n🛒 PRODUCTS FOUND:")

    for product in products:
        print(
            f"- {product['quantity']}x "
            f"{product['name']} "
            f"(${product['price']:.2f})"
        )

    return products


# -----------------------------
# EXPIRATION DATES
# -----------------------------

def generate_expiration_dates(products):

    print("\n🥬 Estimating expiration dates...")

    product_text = json.dumps(products, indent=2)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": """
You estimate food expiration/use-by dates.

Today is October 3, 2026.

For every grocery product, estimate a reasonable
use-by date based on typical storage conditions.

Important:
- These are ESTIMATES, not guaranteed expiration dates.
- Consider normal storage conditions.
- Refrigerated products should assume refrigeration.
- Fresh meat should have a relatively short timeframe.
- Produce varies significantly.
- Shelf-stable products can last much longer.
- If the product is ambiguous, make a reasonable assumption.

Return ONLY valid JSON.

Format:

[
  {
    "product": "Milk",
    "estimated_expiration": "2026-10-10",
    "confidence": "medium",
    "assumption": "Refrigerated and unopened"
  }
]

Confidence must be:
"high", "medium", or "low".
"""
            },
            {
                "role": "user",
                "content": product_text
            }
        ]
    )

    result = response.choices[0].message.content

    try:
        expiration_data = json.loads(result)
    except json.JSONDecodeError:
        print("Could not parse expiration response:")
        print(result)
        return []

    return expiration_data


# -----------------------------
# DISPLAY INVENTORY
# -----------------------------

def display_inventory(products, expiration_data):

    print("\n")
    print("=" * 50)
    print("              🛒 MY INVENTORY")
    print("=" * 50)

    for item in expiration_data:

        print(f"\n🥫 {item['product']}")
        print(f"   Estimated use-by: {item['estimated_expiration']}")
        print(f"   Confidence: {item['confidence']}")
        print(f"   Assumption: {item['assumption']}")

    print("\n" + "=" * 50)
    print("⚠️ These dates are estimates. Check the package.")
    print("=" * 50)


# -----------------------------
# MAIN
# -----------------------------

def main():

    print("====================================")
    print("     GROCERY INVENTORY SCANNER")
    print("====================================")

    image_path = input(
        "\nEnter receipt image path: "
    ).strip()

    if not os.path.exists(image_path):
        print("❌ Image not found.")
        return

    # 1. OCR
    receipt_text = scan_receipt(image_path)

    if not receipt_text.strip():
        print("❌ OCR found no text.")
        return

    # 2. Extract products
    products = extract_products(receipt_text)

    if not products:
        print("❌ No products found.")
        return

    # 3. Generate expiration estimates
    expiration_data = generate_expiration_dates(products)

    if not expiration_data:
        print("❌ Could not generate expiration dates.")
        return

    # 4. Display inventory
    display_inventory(products, expiration_data)


if __name__ == "__main__":
    main()