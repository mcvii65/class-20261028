# Campus Store Supabase project

Python starter project for connecting to the Campus Store Supabase database.

## Set up

1. Activate the virtual environment:
   - macOS/Linux: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`
2. Install dependencies: `python -m pip install -r requirements.txt`
3. If `.env` does not exist yet, copy `.env.example` to `.env`.
4. In `.env`, set `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, and `APP_PASSWORD`.
   The URL must be the project URL without `/rest/v1`.
5. In Supabase, make sure the Campus Store SQL setup has been run. It grants
   table access to `service_role` only. The Streamlit app uses the secret key
   on the server and requires the shared classroom app password before making
   database requests.

Keep `.env` private. This key bypasses Row Level Security and grants elevated
database access. Never put it in source code, a public repository, a browser
app, or share it in chat. The `.env` file is excluded from Git.

## Use the client

```python
from database import get_supabase_client

supabase = get_supabase_client()
```

`get_supabase_client()` reads credentials from `.env` (or the process
environment) and raises a clear error if either value is missing. It creates a
client but does not make a database request.

## Run the Streamlit app locally

Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example` if you
prefer local Streamlit secrets, or set the same values in `.env`. Never commit
the filled-in secrets file.

```bash
streamlit run app.py
```

The app password gate runs before any Supabase access. It is a classroom
access control, not a production authentication system.

## Publish on Streamlit Community Cloud

1. Push this repository to GitHub. Include `app.py`, `database.py`,
   `requirements.txt`, `.gitignore`, and this README.
2. At <https://share.streamlit.io/>, create an app using this repository,
   branch, and `app.py` as the entry point.
3. In the app's **Settings → Secrets**, add:

   ```toml
   SUPABASE_URL = "https://your-project-id.supabase.co"
   SUPABASE_SECRET_KEY = "your-secret-key"
   APP_PASSWORD = "your-private-classroom-password"
   ```

4. Deploy and test the hosted URL using the checklist below. Give the
   instructor the app password privately.
5. Capture screenshots of the loaded order-entry interface and a successfully
   verified order. Save them under `screenshots/` and ensure they contain no
   credentials before adding them to the repository.

The secret key bypasses Row Level Security and grants elevated database
access. It is used only server-side after the password gate. Never put it in
source code, a public repository, browser code, or a screenshot.

## Assignment: terminal order entry

The separate terminal assignment can be run with:

```bash
python order_entry.py
```

The program retrieves customers and products from Supabase, displays them in
readable tables, validates the selected customer, product, and positive
quantity, inserts one order using the product's current database price, then
retrieves and prints the saved order to verify it. It runs in the VS Code
terminal; it is not a web application.

To print every table for troubleshooting, run `python print_tables.py`.

## Deployment and testing status

The app code is prepared, but it has not been published or tested at a hosted
URL. App URL: pending. GitHub repository URL:
<https://github.com/mcvii65/class-20261028>. After deploying, record the
working app URL here and document the results for: authorized app access,
customer/product data, invalid quantity, unconfirmed submission, confirmed
insertion, verification query, rerun without duplicate insertion, and refreshed
order history. Include the two credential-free screenshots described above.
