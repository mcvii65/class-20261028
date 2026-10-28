"""Supabase client setup for the Campus Store project."""

import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def get_supabase_client(
    url: str | None = None,
    secret_key: str | None = None,
) -> Client:
    """Create a privileged client for local scripts using environment credentials."""
    url = url or os.getenv("SUPABASE_URL")
    secret_key = secret_key or os.getenv("SUPABASE_SECRET_KEY")

    if not url or not secret_key:
        missing = [
            name
            for name, value in (
                ("SUPABASE_URL", url),
                ("SUPABASE_SECRET_KEY", secret_key),
            )
            if not value
        ]
        raise RuntimeError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "Set them in the private .env file. Use the project's secret key "
            "(or legacy service_role key) for these local scripts."
        )

    return create_client(url.rstrip("/"), secret_key)
