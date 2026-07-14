# CMS Provider Survey App — Azure App Service Setup Guide

---

## SECTION 1 — Next Steps (Samuel's Checklist)

These can be done independently, before or after App Service is provisioned.

### Can be done RIGHT NOW (no infra needed)
- [ ] Run the 3 DDL `CREATE TABLE` statements in Databricks (see Section 4)
- [ ] Seed the `users` table in Databricks with caller accounts (see Section 4)
- [ ] Fill in the `.env` file in the project folder with Databricks credentials for local testing
- [ ] Run the app locally to confirm Databricks connectivity: `streamlit run streamlit_app.py`

### Once App Service is provisioned by infra
- [ ] In Azure Portal → App Service → **Configuration → Application settings**, add the 3 environment variables (see Section 3)
- [ ] In Azure Portal → App Service → **Configuration → General Settings**, set **Web sockets** to **On**
- [ ] In Azure Portal → App Service → **Configuration → General Settings**, set the **Startup command**:
  ```
  python -m streamlit run streamlit_app.py --server.port 8000 --server.address 0.0.0.0
  ```
- [ ] Connect GitHub repo to App Service for deployment (Portal → Deployment Center → GitHub)
- [ ] Verify the app is reachable at `https://<app-name>.azurewebsites.net`

### Future (once ETL pipeline for record_queue is built)
- [ ] ETL job loads provider records into `cat_dev_dq.master_responses.record_queue` table
- [ ] App is updated to read from `record_queue` and display DB reference values to callers during verification

---

## SECTION 2 — What the App Is (For Infrastructure)

**App type:** Python web application (Streamlit framework)

**Purpose:**
This is an internal data verification tool used by external contracted callers.
Callers receive a queue of healthcare provider records and phone each provider's practice
to confirm whether the data the organization holds on file is accurate. The app captures
their responses (yes/no answers and corrected values) and writes the results to Databricks.

**Users:**
- ~5–15 concurrent external consultant callers
- 1–2 internal admin users for reporting

**Data flow:**
1. Caller logs in with username and password
2. App reads caller credentials from Databricks (`users` table)
3. Caller fills out a 6-page verification form per provider record
4. On submit, the app writes the response to Databricks (`master_responses` table) via an upsert
5. Admin users can view and download the full response table

**Tech stack:**
- Language: Python 3.11
- Framework: Streamlit (open-source, MIT license — no paid license required)
- Database: Databricks Delta Lake (existing org infrastructure)
- Databricks connection: `databricks-sql-connector` over HTTPS (port 443)

---

## SECTION 3 — Azure App Service Requirements (For Infrastructure)

### What to provision

| Setting | Value |
|---|---|
| Service type | Azure App Service (Web App) |
| OS | Linux |
| Runtime stack | Python 3.11 |
| Region | Match the Databricks workspace region (minimize latency) |
| SKU / Pricing tier | Basic B1 (sufficient for ~15 concurrent users; can scale to Standard S1 if needed) |
| App name | *(your choice — determines the default URL)* |

### Networking & Internet Exposure

| Requirement | Detail |
|---|---|
| **Public HTTPS access** | Required — callers are external consultants working remotely, not on the company network. The app must be reachable over the public internet. |
| **HTTP → HTTPS redirect** | Enable HTTPS Only in App Service (Portal → TLS/SSL settings → HTTPS Only: On) |
| **SSL certificate** | No action needed — App Service provides a free managed TLS cert for the `*.azurewebsites.net` default domain |
| **Custom domain** | Optional — can be added later if a branded URL is needed |
| **WebSockets** | Must be enabled — Streamlit requires WebSocket support for real-time UI updates |
| **Outbound connectivity** | App needs outbound HTTPS (port 443) to the Databricks workspace URL (e.g. `adb-xxxx.azuredatabricks.net`). If the App Service is placed inside a VNet or behind a firewall, this outbound route must be open. |
| **Inbound restrictions** | None required initially. If desired, access can be restricted to specific IP ranges (e.g. caller office IPs) via App Service Access Restrictions. |
| **Authentication** | The app manages its own username/password login against the Databricks `users` table. Azure AD / Entra ID authentication is NOT required — callers are from an external company and do not have org Azure AD accounts. |

### Environment Variables to Set in App Service

Navigate to: **App Service → Configuration → Application settings → + New application setting**

Add these three key/value pairs (values to be provided by Samuel once Databricks credentials are confirmed):

| Key | Value |
|---|---|
| `DATABRICKS_SERVER_HOSTNAME` | Databricks workspace hostname (e.g. `adb-xxxx.azuredatabricks.net`) |
| `DATABRICKS_HTTP_PATH` | SQL Warehouse HTTP path (e.g. `/sql/1.0/warehouses/xxxx`) |
| `DATABRICKS_TOKEN` | Databricks Personal Access Token |

### Startup Command

Navigate to: **App Service → Configuration → General Settings → Startup command**

```
python -m streamlit run streamlit_app.py --server.port 8000 --server.address 0.0.0.0
```

### Deployment

The app is hosted in a GitHub repository. App Service can deploy directly from GitHub:
- Navigate to: **App Service → Deployment Center → Source: GitHub**
- Select the repository and branch (e.g. `main`)
- App Service will automatically redeploy when new commits are pushed

---

## SECTION 4 — Databricks Setup (Samuel to run)

Run these in order in the Databricks SQL editor.

### Step 1 — Create the `users` table

```sql
CREATE TABLE IF NOT EXISTS cat_dev_dq.master_responses.users (
    user_id     BIGINT  NOT NULL GENERATED ALWAYS AS IDENTITY,
    caller_id   STRING  NOT NULL,
    password    STRING  NOT NULL,
    role        STRING  NOT NULL,

    CONSTRAINT pk_users           PRIMARY KEY (user_id),
    CONSTRAINT uq_users_caller_id UNIQUE (caller_id)
)
USING DELTA
COMMENT 'Caller accounts. caller_id is the natural key referenced by downstream tables.';
```

### Step 2 — Create the `record_queue` table

```sql
CREATE TABLE IF NOT EXISTS cat_dev_dq.master_responses.record_queue (
    record_id                   BIGINT  NOT NULL GENERATED ALWAYS AS IDENTITY,

    caller_id                   STRING,
    campaign_id                 STRING,

    db_caqhid                   STRING,
    db_first_name               STRING,
    db_last_name                STRING,
    db_office_phone_number      STRING,
    db_practice_location_name   STRING,
    db_specialty_list           STRING,
    db_street                   STRING,
    db_street_2                 STRING,
    db_city                     STRING,
    db_state                    STRING,
    db_zip_code                 STRING,

    verification_status         STRING,

    attempt_date_1              DATE,
    attempt_date_2              DATE,
    attempt_date_3              DATE,

    CONSTRAINT pk_record_queue      PRIMARY KEY (record_id),
    CONSTRAINT fk_record_queue_user FOREIGN KEY (caller_id)
        REFERENCES cat_dev_dq.master_responses.users (caller_id)
)
USING DELTA
COMMENT 'One row per provider assigned per campaign. Logically hidden via verification_status rather than deleted. Same CAQHID may appear across multiple campaigns.';
```

### Step 3 — Create the `master_responses` table

```sql
CREATE TABLE IF NOT EXISTS cat_dev_dq.master_responses.master_responses (
    response_id                                         BIGINT  NOT NULL GENERATED ALWAYS AS IDENTITY,
    record_queue_id                                     BIGINT,
    caller_id                                           STRING,
    campaign_id                                         STRING,
    caqh_id                                             STRING,
    can_proceed_with_call                               BOOLEAN,
    form_start_time                                     TIMESTAMP,
    form_submission_time                                TIMESTAMP,
    form_total_time_minutes                             INTEGER,
    attempt_date_1                                      DATE,
    attempt_date_2                                      DATE,
    attempt_date_3                                      DATE,
    verification_complete                               BOOLEAN,
    provider_currently_practicing_response              BOOLEAN,
    provider_speciality_category_response               BOOLEAN,
    phone_number_correct_response                       BOOLEAN,
    practice_location_name_response                     BOOLEAN,
    practice_location_address_response                  BOOLEAN,
    practice_location_suite_response                    BOOLEAN,
    practice_accepting_new_patients_response            BOOLEAN,
    practice_accepting_new_medicare_patients_response   BOOLEAN,
    enriched_provider_speciality_category_value         STRING,
    enriched_phone_number_value                         STRING,
    enriched_practice_location_name_value               STRING,
    enriched_practice_street_line_1_value               STRING,
    enriched_practice_street_line_2_suite_value         STRING,
    enriched_practice_city_value                        STRING,
    enriched_practice_zip_value                         STRING,
    enriched_practice_state_value                       STRING,
    standard_comments                                   STRING,
    unique_comments                                     STRING,

    CONSTRAINT pk_master_responses       PRIMARY KEY (response_id),
    CONSTRAINT uq_master_campaign_caqh   UNIQUE (campaign_id, caqh_id),
    CONSTRAINT fk_master_responses_queue FOREIGN KEY (record_queue_id)
        REFERENCES cat_dev_dq.master_responses.record_queue (record_id),
    CONSTRAINT fk_master_responses_user  FOREIGN KEY (caller_id)
        REFERENCES cat_dev_dq.master_responses.users (caller_id)
)
USING DELTA
COMMENT 'One row per provider per campaign. Upserted on each call attempt; attempt_date_1/2/3 stamped progressively. response_id is generated by Databricks — never passed by the app.';
```

### Step 4 — Seed the `users` table

```sql
INSERT INTO cat_dev_dq.master_responses.users (caller_id, password, role) VALUES
('admin',     'admin123',  'admin'),
('caller001', 'caller123', 'caller'),
('caller002', 'caller456', 'caller');
-- Add additional consultant caller accounts here as needed
```

---

## SECTION 5 — Repository Structure (For Reference)

```
cms-form/
├── streamlit_app.py          # Main application
├── requirements.txt          # Python dependencies
├── .env                      # Local credentials (never committed to GitHub)
├── .gitignore                # Excludes .env and cache files
└── .streamlit/
    └── config.toml           # Streamlit server config (port 8000, headless mode)
```

**Python dependencies (`requirements.txt`):**
```
streamlit
pandas
databricks-sql-connector
python-dotenv
```

---

*Document prepared: 2026-07-14*
