import os

from pipeline import process_receipt


# ==========================================
# DISPLAY INVENTORY
# ==========================================

def display_inventory(items):

    print("\n")

    print("=" * 65)
    print("                    INVENTORY")
    print("=" * 65)

    for i, item in enumerate(items, 1):

        name = item.get("name", "Unknown")
        quantity = item.get("quantity", 1)
        price = item.get("price")
        expiration = item.get("estimated_expiration", "Unknown")
        storage = item.get("storage", "Unknown")

        print(f"\n{i}. {name}")
        print(f"   Quantity: {quantity}")

        if price is not None:
            try:
                print(f"   Price: ${float(price):.2f}")
            except (TypeError, ValueError):
                print(f"   Price: {price}")
        else:
            print("   Price: Unknown")

        print(f"   Estimated expiration: {expiration}")
        print(f"   Storage: {storage}")

    print("\n" + "=" * 65)


# ==========================================
# MAIN
# ==========================================

def main():

    print("=" * 65)
    print("                 XPIRE SCAN")
    print("=" * 65)

    image_path = input(
        "\nEnter the path to your receipt image: "
    ).strip().strip('"')

    if not os.path.exists(image_path):
        print("\nERROR: File does not exist.")
        return

    inventory, receipt_date, error = process_receipt(image_path)

    if error:
        print(f"\nERROR: {error}")
        return

    display_inventory(inventory)


if __name__ == "__main__":
    main()
