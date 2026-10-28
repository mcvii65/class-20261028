"""Print rows from the Campus Store tables in Supabase."""

import sys

from database import get_supabase_client
from postgrest.exceptions import APIError
from tabulate import tabulate

TABLES = ("customers", "products", "orders")


def main() -> int:
    """Fetch and print all rows from each Campus Store table."""
    try:
        supabase = get_supabase_client()

        for table_name in TABLES:
            response = supabase.table(table_name).select("*").execute()
            rows = response.data
            print(f"\n{table_name} ({len(rows)} rows)")
            if rows:
                print(tabulate(rows, headers="keys", tablefmt="grid"))
            else:
                print("(no rows)")
    except APIError as error:
        print(f"Supabase request failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
