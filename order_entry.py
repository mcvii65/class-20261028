"""Create and verify a customer order using the Supabase API."""

import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from postgrest.exceptions import APIError
from tabulate import tabulate

from database import get_supabase_client


def display_customers(customers: list[dict[str, Any]]) -> None:
    """Print customer IDs and names in a readable table."""
    table = [
        {"Customer ID": customer["customer_id"], "Customer Name": customer["name"]}
        for customer in customers
    ]
    print("\nCustomers")
    print(tabulate(table, headers="keys", tablefmt="grid"))


def display_products(products: list[dict[str, Any]]) -> None:
    """Print product IDs, names, and prices in a readable table."""
    table = [
        {
            "Product ID": product["product_id"],
            "Product Name": product["product_name"],
            "Current Price": f"${Decimal(str(product['price'])):.2f}",
        }
        for product in products
    ]
    print("\nProducts")
    print(tabulate(table, headers="keys", tablefmt="grid"))


def prompt_for_existing_id(
    prompt: str,
    records: list[dict[str, Any]],
    id_field: str,
) -> int:
    """Prompt until the user enters an ID present in the supplied records."""
    valid_ids = {int(record[id_field]) for record in records}
    while True:
        value = input(prompt).strip()
        try:
            record_id = int(value)
        except ValueError:
            print("Enter a whole-number ID from the table.")
            continue
        if record_id in valid_ids:
            return record_id
        print("That ID is not in the table. Choose one of the displayed IDs.")


def prompt_for_quantity() -> int:
    """Prompt until the user enters a positive whole-number quantity."""
    while True:
        value = input("Quantity: ").strip()
        try:
            quantity = int(value)
        except ValueError:
            print("Enter a whole-number quantity greater than zero.")
            continue
        if quantity > 0:
            return quantity
        print("Quantity must be greater than zero.")


def prompt_for_confirmation() -> bool:
    """Return whether the user confirms, re-prompting for anything but Y or N."""
    while True:
        answer = input("Confirm order? (Y/N): ").strip().lower()
        if answer == "y":
            return True
        if answer == "n":
            return False
        print("Please enter Y to confirm or N to cancel.")


def main() -> int:
    """Fetch choices, create an order, and retrieve it to verify the insert."""
    try:
        supabase = get_supabase_client()
        customers = (
            supabase.table("customers")
            .select("customer_id,name")
            .order("customer_id")
            .execute()
            .data
        )
        products = (
            supabase.table("products")
            .select("product_id,product_name,price")
            .order("product_id")
            .execute()
            .data
        )
        if not customers:
            print("No customers were returned from Supabase; cannot create an order.")
            return 1
        if not products:
            print("No products were returned from Supabase; cannot create an order.")
            return 1

        display_customers(customers)
        display_products(products)

        customer_id = prompt_for_existing_id(
            "Customer ID: ", customers, "customer_id"
        )
        product_id = prompt_for_existing_id("Product ID: ", products, "product_id")
        quantity = prompt_for_quantity()

        selected_product = next(
            product for product in products if int(product["product_id"]) == product_id
        )
        selected_customer = next(
            customer
            for customer in customers
            if int(customer["customer_id"]) == customer_id
        )
        unit_price = Decimal(str(selected_product["price"]))
        order_total = unit_price * quantity

        print("\nOrder summary")
        print(f"Customer: {selected_customer['name']}")
        print(f"Product: {selected_product['product_name']}")
        print(f"Quantity: {quantity}")
        print(f"Current unit price: ${unit_price:.2f}")
        print(f"Order total: ${order_total:.2f}")
        if not prompt_for_confirmation():
            print("Order canceled. Nothing was saved.")
            return 0

        order_payload = {
            "customer_id": customer_id,
            "product_id": product_id,
            "quantity": quantity,
            "order_date": date.today().isoformat(),
            "unit_price": str(unit_price),
        }
        try:
            inserted = (
                supabase.table("orders")
                .insert(order_payload)
                .select("order_id")
                .single()
                .execute()
                .data
            )
        except APIError as error:
            print(f"Order could not be saved: {error}", file=sys.stderr)
            return 1

        order_id = inserted.get("order_id") if inserted else None
        if order_id is None:
            print(
                "Supabase did not return the generated order ID. "
                "The order cannot be verified; do not submit it again automatically.",
                file=sys.stderr,
            )
            return 1

        try:
            saved_order = (
                supabase.table("orders")
                .select(
                    "order_id,quantity,order_date,unit_price,"
                    "customers(name),products(product_name)"
                )
                .eq("order_id", order_id)
                .maybe_single()
                .execute()
                .data
            )
        except APIError as error:
            print(
                f"Order {order_id} may have been inserted, but verification "
                f"could not be completed: {error}",
                file=sys.stderr,
            )
            return 1

        if saved_order is None:
            print(
                f"Order {order_id} may have been inserted, but verification "
                "found no matching record. Do not submit it again automatically.",
                file=sys.stderr,
            )
            return 1

        stored_unit_price = Decimal(str(saved_order["unit_price"]))
        stored_quantity = int(saved_order["quantity"])

        print("\nOrder saved and verified:")
        verification_table = {
            "Order ID": saved_order["order_id"],
            "Customer": saved_order["customers"]["name"],
            "Product": saved_order["products"]["product_name"],
            "Quantity": stored_quantity,
            "Unit Price": f"${stored_unit_price:.2f}",
            "Total": f"${stored_unit_price * stored_quantity:.2f}",
            "Order Date": saved_order["order_date"],
        }
        print(
            tabulate(
                [verification_table],
                headers="keys",
                tablefmt="grid",
            )
        )
    except APIError as error:
        print(f"Supabase request failed: {error}", file=sys.stderr)
        print(
            "Confirm that .env contains the correct project URL and secret key, "
            "and that the class database starter SQL has been run.",
            file=sys.stderr,
        )
        return 1
    except InvalidOperation as error:
        raise RuntimeError("Supabase returned an invalid product price.") from error

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
