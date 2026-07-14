# Next Session Briefing — CMS Provider Survey App

**How to use this file:**
At the start of the session, tell Claude:
> "Read `streamlit_app.py` and `NEXT_SESSION_BRIEFING.md` and `Azure_App_Service_Setup_Guide.md` in my project folder, then let's continue."

---

## What This Project Is

A Python/Streamlit web app replacing a CMS provider survey previously run on MS Forms.
External contracted callers use it to phone healthcare provider practices and verify whether
the data the organization holds on file is correct. Responses are written to Databricks.

- **Framework:** Streamlit (open-source, no license cost)
- **Hosting:** Moving from Streamlit Cloud → Azure App Service (Linux, Python 3.11, Basic B1)
- **Database:** Databricks Delta Lake
- **Catalog / schema:** `cat_dev_dq.master_responses`
- **Tables:** `users`, `record_queue`, `master_responses`
- **Repo:** GitHub (Samuel's account)
- **Local project path:** `C:\Users\SamuelMuvdi\Desktop\streamlit_app\cms-form\`

---

## Current State — What Is Already Done

- `streamlit_app.py` — fully built, 6-page multi-step verification form, **already converted from CSV to Databricks**. Reads `users` table for login, upserts into `master_responses` on submit via MERGE INTO. No CSV files used anymore.
- `requirements.txt` — updated (`streamlit`, `pandas`, `databricks-sql-connector`, `python-dotenv`)
- `.streamlit/config.toml` — configured for App Service (port 8000, headless)
- `.env` — placeholder file created (Samuel needs to fill in credentials)
- `.gitignore` — covers `.env` so credentials are never committed
- `Azure_App_Service_Setup_Guide.md` — complete setup document for the infrastructure person, includes all 3 DDL statements and seed INSERT

---

## What Is NOT Done Yet — Priority Order

### 1. Databricks tables (Samuel can do this independently)
The DDL has been written but the tables do not exist yet in Databricks.
Samuel needs to run the 3 `CREATE TABLE` statements and the seed `INSERT` from
`Azure_App_Service_Setup_Guide.md` (Section 4) in the Databricks SQL editor.
Order: `users` → `record_queue` → `master_responses`
Then seed: `INSERT INTO users ...`

### 2. Local testing (blocked until .env is filled in + tables exist)
- Samuel needs to get 3 Databricks credentials: server hostname, HTTP path, PAT token
- Fill them into the `.env` file
- Run `pip install -r requirements.txt` then `streamlit run streamlit_app.py`
- Test login, form submission, and admin page against Databricks

### 3. Azure App Service (waiting on infra team approval)
- Infra person has the full requirements in `Azure_App_Service_Setup_Guide.md`
- Once provisioned: set 3 env vars in Azure Portal, enable WebSockets, set startup command, connect GitHub for deployment
- Everything is documented in the guide — no code changes needed for this step

### 4. record_queue display in the app (NOT STARTED — future work)
This is the next major feature after the above 3 are complete.
When a caller opens a record, the app should display the DB reference values
from `record_queue` alongside each question so the caller knows what to verify.
Example: "Is the phone number correct? — DB value: **555-123-4567**"
This requires:
- The `record_queue` table to be populated (ETL pipeline, separate from the app)
- App logic to query `record_queue` by `caller_id` and surface those values on the form pages
- The ETL pipeline is being built separately by Samuel's team — the app side is not started

### 5. Queue system in the app (NOT STARTED — future work)
Currently callers manually type in Campaign ID and CAQHID on Page 1.
Eventually the app should auto-load the next record from `record_queue` filtered by `caller_id`,
pre-filling those fields and cycling through attempts automatically.
This is blocked until the ETL pipeline is loading data into `record_queue`.

---

## Key Design Decisions Already Made (Do Not Revisit)

- **Upsert key:** `campaign_id + caqh_id` (composite natural key on `master_responses`) — `UNIQUE` constraint enforces this
- **PK:** `response_id GENERATED ALWAYS AS IDENTITY` — app never passes this, Databricks generates it
- **Attempt dates:** stamped via `COALESCE` / `CASE` inside the MERGE SQL — atomic, no pre-read needed
- **Logical delete on queue:** `verification_status` flag, records are never physically deleted from `record_queue`
- **Same CAQHID across campaigns:** intentional — a provider can be called again in a future campaign
- **No Azure AD auth:** callers are external consultants from another company, username/password in `users` table
- **can_proceed_with_call on Page 2:** if "No", caller skips to Page 6 directly — pages 3, 4, 5 are bypassed and their fields are NULL in the DB

---

## DB Connection (How It Works in Code)

```python
# In streamlit_app.py, top of file
CATALOG = "cat_dev_dq.master_responses"

@st.cache_resource
def get_db_connection():
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )
```

Table references throughout the app use f-strings like:
`f"SELECT ... FROM {CATALOG}.users WHERE ..."`
which resolves to `cat_dev_dq.master_responses.users`

---

## Likely Questions / Things to Pick Up

- "The infra guy approved App Service — how do I deploy?" → Follow Section 3 of `Azure_App_Service_Setup_Guide.md`
- "The tables are created, how do I test locally?" → Fill `.env`, run `pip install -r requirements.txt`, then `streamlit run streamlit_app.py`
- "The ETL pipeline is ready, now I want to show DB values in the form" → Start with `record_queue` query in `survey_page_1()` after user enters Campaign ID + CAQHID, then pass values down to pages 2–5
- "I want to add a new caller account" → `INSERT INTO cat_dev_dq.master_responses.users (caller_id, password, role) VALUES ('newcaller', 'password', 'caller');`
