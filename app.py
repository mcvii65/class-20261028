"""Password-protected Streamlit order-entry app for the Campus Store."""

import hmac
import os
from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd
import streamlit as st
import httpx
from postgrest.exceptions import APIError
from streamlit.errors import StreamlitSecretNotFoundError

from database import get_supabase_client

st.set_page_config(page_title="Campus Store Order Entry", page_icon="🛍️", layout="wide")

SUPABASE_ERRORS = (APIError, httpx.HTTPError)


def get_setting(name: str) -> str | None:
    """Get a setting from the environment or Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value

    try:
        value = st.secrets.get(name)
    except StreamlitSecretNotFoundError:
        return None
    return str(value) if value else None


def require_app_password() -> bool:
    """Require the configured shared classroom password before database access."""
    expected_password = get_setting("APP_PASSWORD")
    st.title("Campus Store Order Entry")
    st.write("View classroom customers and products, then create and verify an order.")

    if not expected_password:
        st.error(
            "The app is not configured with an access password. Set APP_PASSWORD "
            "in your local .env file or Streamlit deployment secrets."
        )
        return False

    if st.session_state.get("app_authenticated"):
        return True

    with st.form("access_form"):
        entered_password = st.text_input("Classroom app password", type="password")
        submitted = st.form_submit_button("Unlock app")

    if submitted:
        if hmac.compare_digest(entered_password, expected_password):
            st.session_state["app_authenticated"] = True
            st.rerun()
        else:
            st.error("That password is not correct.")
    return False


def fetch_app_data(client: Any) -> dict[str, list[dict[str, Any]]]:
    """Retrieve customers, products, and order history from Supabase."""
    customers = (
        client.table("customers")
        .select("customer_id,name")
        .order("customer_id")
        .execute()
        .data
    )
    products = (
        client.table("products")
        .select("product_id,product_name,category,price")
        .order("product_id")
        .execute()
        .data
    )
    orders = fetch_order_history(client)
    return {"customers": customers, "products": products, "orders": orders}


def fetch_order_history(client: Any) -> list[dict[str, Any]]:
    """Retrieve saved orders and their related customer and product names."""
    return (
        client.table("orders")
        .select(
            "order_id,quantity,order_date,unit_price,customers(name),products(product_name)"
        )
        .order("order_id", desc=True)
        .execute()
        .data
    )


def format_products(products: list[dict[str, Any]]) -> pd.DataFrame:
    """Create the product table with currency-formatted prices."""
    return pd.DataFrame(
        [
            {
                "Product ID": product["product_id"],
                "Product Name": product["product_name"],
                "Category": product["category"],
                "Price": f"${Decimal(str(product['price'])):.2f}",
            }
            for product in products
        ],
        columns=["Product ID", "Product Name", "Category", "Price"],
    )


def format_orders(orders: list[dict[str, Any]]) -> pd.DataFrame:
    """Format retrieved orders for history and verification tables."""
    return pd.DataFrame(
        [
            {
                "Order ID": order["order_id"],
                "Customer": order["customers"]["name"],
                "Product": order["products"]["product_name"],
                "Quantity": int(order["quantity"]),
                "Unit Price": f"${Decimal(str(order['unit_price'])):.2f}",
                "Total": (
                    f"${Decimal(str(order['unit_price'])) * int(order['quantity']):.2f}"
                ),
                "Order Date": order["order_date"],
            }
            for order in orders
        ],
        columns=[
            "Order ID",
            "Customer",
            "Product",
            "Quantity",
            "Unit Price",
            "Total",
            "Order Date",
        ],
    )


def run_app() -> None:
    """Render the authenticated order workflow."""
    if not require_app_password():
        st.stop()

    url = get_setting("SUPABASE_URL")
    secret_key = get_setting("SUPABASE_SECRET_KEY")
    if not url or not secret_key:
        st.error(
            "Supabase is not configured. Set SUPABASE_URL and "
            "SUPABASE_SECRET_KEY in .env or Streamlit secrets."
        )
        st.stop()

    try:
        client = get_supabase_client(url=url, secret_key=secret_key)
    except RuntimeError as error:
        st.error(str(error))
        st.stop()

    refresh_clicked = st.button("Refresh Data")
    if "app_data" not in st.session_state or refresh_clicked:
        try:
            st.session_state["app_data"] = fetch_app_data(client)
        except SUPABASE_ERRORS as error:
            st.error(f"Could not load data from Supabase: {error}")
            st.stop()

    data = st.session_state["app_data"]
    customers = data["customers"]
    products = data["products"]
    if not customers or not products:
        st.error("Supabase returned no customers or products; an order cannot be created.")
        st.stop()

    st.subheader("Customers")
    customer_frame = pd.DataFrame(
        [
            {"Customer ID": customer["customer_id"], "Customer Name": customer["name"]}
            for customer in customers
        ],
        columns=["Customer ID", "Customer Name"],
    )
    st.dataframe(customer_frame, hide_index=True, width="stretch")

    st.subheader("Products")
    st.dataframe(format_products(products), hide_index=True, width="stretch")

    customer_by_id = {int(row["customer_id"]): row for row in customers}
    product_by_id = {int(row["product_id"]): row for row in products}

    st.subheader("Create an order")
    customer_id = st.selectbox(
        "Customer",
        options=list(customer_by_id),
        format_func=lambda value: (
            f"{customer_by_id[value]['name']} (ID {value})"
        ),
    )
    product_id = st.selectbox(
        "Product",
        options=list(product_by_id),
        format_func=lambda value: (
            f"{product_by_id[value]['product_name']} (ID {value})"
        ),
    )
    quantity = st.number_input(
        "Quantity",
        min_value=1,
        step=1,
        value=1,
    )

    selected_customer = customer_by_id[customer_id]
    selected_product = product_by_id[product_id]
    displayed_price = Decimal(str(selected_product["price"]))
    displayed_total = displayed_price * int(quantity)

    st.markdown("#### Review your order")
    review_columns = st.columns(5)
    review_columns[0].metric("Customer", selected_customer["name"])
    review_columns[1].metric("Product", selected_product["product_name"])
    review_columns[2].metric("Quantity", int(quantity))
    review_columns[3].metric("Unit price", f"${displayed_price:.2f}")
    review_columns[4].metric("Total", f"${displayed_total:.2f}")
    if st.session_state.pop("price_changed_notice", False):
        st.info("The product price changed. Review the updated total and confirm again.")

    price_revision = st.session_state.get("price_revision", 0)
    confirmation_key = (
        f"confirm_{price_revision}_{customer_id}_{product_id}_"
        f"{quantity}_{displayed_price}"
    )
    with st.form("order_submission"):
        confirmed = st.checkbox(
            "I confirm this order and want to submit it.",
            key=confirmation_key,
        )
        submitted = st.form_submit_button("Submit order")

    if submitted:
        if not confirmed:
            st.warning("Check the confirmation box before submitting the order.")
        else:
            try:
                latest_product = (
                    client.table("products")
                    .select("price")
                    .eq("product_id", product_id)
                    .single()
                    .execute()
                    .data
                )
                latest_price = Decimal(str(latest_product["price"]))
            except SUPABASE_ERRORS as error:
                st.error(f"Could not check the current product price: {error}")
            else:
                if latest_price != displayed_price:
                    updated_products = [
                        {
                            **product,
                            "price": str(latest_price),
                        }
                        if int(product["product_id"]) == product_id
                        else product
                        for product in products
                    ]
                    st.session_state["app_data"]["products"] = updated_products
                    st.session_state["price_revision"] = price_revision + 1
                    st.session_state["price_changed_notice"] = True
                    st.rerun()
                else:
                    order_payload = {
                        "customer_id": customer_id,
                        "product_id": product_id,
                        "quantity": int(quantity),
                        "order_date": date.today().isoformat(),
                        "unit_price": str(latest_price),
                    }
                    try:
                        inserted = (
                            client.table("orders")
                            .insert(order_payload)
                            .select("order_id")
                            .single()
                            .execute()
                            .data
                        )
                    except SUPABASE_ERRORS as error:
                        st.error(f"Supabase could not save the order: {error}")
                    else:
                        order_id = inserted.get("order_id") if inserted else None
                        if order_id is None:
                            st.error(
                                "Supabase did not return the generated order ID. "
                                "The order may have been saved; do not submit it again "
                                "until you check the order history."
                            )
                        else:
                            st.session_state["price_revision"] = price_revision + 1
                            try:
                                st.session_state["app_data"]["orders"] = (
                                    fetch_order_history(client)
                                )
                            except SUPABASE_ERRORS as error:
                                st.warning(
                                    "The order was inserted, but order history could "
                                    f"not be refreshed: {error}"
                                )

                            try:
                                saved_order = (
                                    client.table("orders")
                                    .select(
                                        "order_id,quantity,order_date,unit_price,"
                                        "customers(name),products(product_name)"
                                    )
                                    .eq("order_id", order_id)
                                    .maybe_single()
                                    .execute()
                                    .data
                                )
                            except SUPABASE_ERRORS as error:
                                st.success(f"Order {order_id} was saved.")
                                st.warning(
                                    "The order was saved but could not be retrieved "
                                    f"for verification: {error}"
                                )
                            else:
                                if saved_order is None:
                                    st.success(f"Order {order_id} was saved.")
                                    st.warning(
                                        "The order was saved but no matching record "
                                        "could be retrieved for verification."
                                    )
                                else:
                                    st.session_state["last_saved_order"] = saved_order
                                    st.success(f"Order {order_id} was saved.")

    if "last_saved_order" in st.session_state:
        st.subheader("Saved order verification")
        st.dataframe(
            format_orders([st.session_state["last_saved_order"]]),
            hide_index=True,
            width="stretch",
        )

    st.subheader("Order History")
    if data["orders"]:
        st.dataframe(
            format_orders(data["orders"]),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("There are no orders to display yet.")


run_app()
