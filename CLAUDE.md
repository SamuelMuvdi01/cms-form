# CMS Provider Survey App — Session Context

## What This Project Is

A Python/Streamlit web app replacing a CMS provider survey previously on MS Forms.
External contracted callers phone healthcare provider practices to verify data the org holds on file.
Responses are written to Databricks.

- **Framework:** Streamlit
- **Hosting:** Moving from Streamlit Cloud → Azure App Service (Linux, Python 3.11, Basic B1)
- **Database:** Databricks Delta Lake
- **Catalog/schema:** `cat_dev_dq.master_responses`
- **Tables:** `users`, `record_queue`, `master_responses`
- **Main file:** `streamlit_app.py` — 6-page multi-step verification form
- **Local path:** `C:\Users\SamuelMuvdi\Desktop\streamlit_app\cms-form\`

## What Is Done

- `streamlit_app.py` — fully built, Databricks-connected (no CSV). Login via `users` table, upsert via MERGE INTO on submit.
- `requirements.txt` — `streamlit`, `pandas`, `databricks-sql-connector`, `python-dotenv`
- `.streamlit/config.toml` — port 8000, headless (App Service ready)
- `.env` — placeholder (Samuel must fill in credentials)
- `.gitignore` — covers `.env`
- `Azure_App_Service_Setup_Guide.md` — full infra setup doc with 3 DDL statements and seed INSERT

## What Is NOT Done (Priority Order)

1. **Databricks tables** — DDL written but tables don't exist yet. Run 3 `CREATE TABLE` + seed `INSERT` from `Azure_App_Service_Setup_Guide.md` Section 4. Order: `users` → `record_queue` → `master_responses`.
2. **Local testing** — blocked until `.env` is filled (3 Databricks creds: hostname, HTTP path, PAT token) + tables exist.
3. **Azure App Service** — waiting on infra team. Guide covers everything; no code changes needed.
4. **`record_queue` display in form** (future) — show DB reference values next to each question so callers know what to verify. Requires ETL pipeline to populate `record_queue` first.
5. **Queue system** (future) — auto-load next record from `record_queue` by `caller_id`, pre-filling Campaign ID + CAQHID on Page 1.

## Key Design Decisions (Do Not Revisit)

- **Upsert key:** `campaign_id + caqh_id` composite — `UNIQUE` constraint on `master_responses`
- **PK:** `response_id GENERATED ALWAYS AS IDENTITY` — app never passes this
- **Attempt dates:** stamped atomically inside MERGE SQL via `COALESCE`/`CASE` — no pre-read
- **Logical delete on queue:** `verification_status` flag, records never physically deleted
- **Same CAQHID across campaigns:** intentional — provider can appear in multiple campaigns
- **No Azure AD auth:** callers are external consultants, credentials stored in `users` table
- **`can_proceed_with_call` gate on Page 2:** if "No", skips Pages 3–4–5, goes straight to Page 6; those fields are NULL in DB

## DB Connection Pattern

```python
CATALOG = "cat_dev_dq.master_responses"

@st.cache_resource
def get_db_connection():
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )
```

Table refs use f-strings: `f"SELECT ... FROM {CATALOG}.users"` → `cat_dev_dq.master_responses.users`

## Common Next Steps

- "How do I deploy to App Service?" → `Azure_App_Service_Setup_Guide.md` Section 3
- "Tables are created, how do I test locally?" → Fill `.env`, `pip install -r requirements.txt`, `streamlit run streamlit_app.py`
- "ETL is ready, show DB values in form" → Query `record_queue` in `survey_page_1()` after Campaign ID + CAQHID entered, pass values to pages 2–5
- "Add a new caller" → `INSERT INTO cat_dev_dq.master_responses.users (caller_id, password, role) VALUES ('id', 'pass', 'caller');`
