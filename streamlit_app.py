import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st
from databricks import sql
from dotenv import load_dotenv

load_dotenv()


# ======================================================
# DB CONFIG
# ======================================================

CATALOG = "cat_dev_dq.master_responses"


@st.cache_resource
def get_db_connection():
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


# ======================================================
# FORM CONFIG
# ======================================================

YES_NO = ["Yes", "No"]

STATE_CODES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "AS", "GU", "MP", "PR", "VI"
]

STANDARD_COMMENTS = [
    "Automated message",
    "Automated message directs callers to email",
    "Call drops immediately",
    "Hung up or said not to contact",
    "No answer and left voicemail",
    "No answer and no voicemail",
    "Responder could not validate",
    "Number out of service",
    "Provider does not practice here",
    "Provider is deceased",
    "Provider is retired",
    "Responder could not validate said we have to email",
    "Responder not answering thinks this is spam",
    "Responder said she has no information about this provider",
    "Responder said the listed provider is only contracted through a different company",
    "Responder said we would have to call the business office in order to validate",
    "Responder unwilling to validate information",
    "Responder was unable to validate information",
    "Transfer to help desk",
    "Wrong number",
]

# Widget keys cleared on form start/cancel. p1 keys removed — page 1 is now read-only.
FORM_KEYS = [
    "p2_phone_correct", "p2_phone_enrichment",
    "p2_can_continue",
    "p2_name_correct", "p2_name_enrichment",
    "p3_currently_practicing",
    "p3_specialty_correct", "p3_specialty_enrichment",
    "p4_address_correct",
    "p4_addr_line1", "p4_city", "p4_state", "p4_zip",
    "p4_suite_correct", "p4_suite_enrichment",
    "p5_accepting_new", "p5_accepting_medicare",
    "p6_verification_complete",
    "p6_standard_comments", "p6_unique_comments",
]


# ======================================================
# PAGE SETUP
# ======================================================

st.set_page_config(
    page_title="Provider Survey App",
    page_icon="📝",
    layout="wide"
)


# ======================================================
# SESSION STATE
# ======================================================

def init_session_state():
    defaults = {
        "logged_in": False,
        "username": None,
        "caller_id": None,
        "role": None,
        "page": "home",
        "form_started": False,
        "form_start_time": None,
        "form_start_epoch": None,
        "form_page": 1,
        "form_prev_page": 5,
        "current_record": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# ======================================================
# HELPER FUNCTIONS
# ======================================================

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def to_bool(val):
    return {"Yes": True, "No": False}.get(val)


def check_login(username, password):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT username, caller_id, role FROM {CATALOG}.users WHERE username = %s AND password = %s",
            [username.strip(), password]
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return {"username": row[0], "caller_id": row[1], "role": row[2]}


def load_next_record():
    """
    Returns (record_dict, remaining_count) for this caller.
    Admin (caller_id=0) sees all unverified records across all callers.
    Attempt priority: attempt_date_1 IS NULL first, then 2, then 3.
    Records with all 3 attempt dates filled are excluded from the queue.
    Returns (None, 0) when the queue is empty.
    """
    conn = get_db_connection()
    caller_id = st.session_state.caller_id

    is_admin = (caller_id == 0)
    base_filter = """
        verification_complete = FALSE
        AND (attempt_date_1 IS NULL OR attempt_date_2 IS NULL OR attempt_date_3 IS NULL)
    """

    if is_admin:
        where = f"WHERE {base_filter}"
        params = []
    else:
        where = f"WHERE caller_id = %s AND {base_filter}"
        params = [caller_id]

    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) FROM {CATALOG}.record_queue {where}",
            params
        )
        count = cursor.fetchone()[0]

        if count == 0:
            return None, 0

        cursor.execute(
            f"""
            SELECT
                record_id, caller_id, campaign_id,
                db_caqhid, db_first_name, db_last_name,
                db_office_phone_number, db_practice_location_name,
                db_specialty_list, db_street, db_street_2,
                db_city, db_state, db_zip_code,
                verification_complete, attempt_date_1, attempt_date_2, attempt_date_3
            FROM {CATALOG}.record_queue
            {where}
            ORDER BY
                CASE
                    WHEN attempt_date_1 IS NULL THEN 0
                    WHEN attempt_date_2 IS NULL THEN 1
                    WHEN attempt_date_3 IS NULL THEN 2
                END ASC
            LIMIT 1
            """,
            params
        )
        row = cursor.fetchone()

    if row is None:
        return None, 0

    cols = [
        "record_id", "caller_id", "campaign_id",
        "db_caqhid", "db_first_name", "db_last_name",
        "db_office_phone_number", "db_practice_location_name",
        "db_specialty_list", "db_street", "db_street_2",
        "db_city", "db_state", "db_zip_code",
        "verification_complete", "attempt_date_1", "attempt_date_2", "attempt_date_3"
    ]
    return dict(zip(cols, row)), count


def attempt_number(record):
    if record["attempt_date_1"] is None:
        return 1
    if record["attempt_date_2"] is None:
        return 2
    return 3


def update_queue_record(record_id, verification_complete):
    """Stamps the next available attempt date and updates verification_complete."""
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE {CATALOG}.record_queue
            SET
                attempt_date_1 = CASE
                    WHEN attempt_date_1 IS NULL THEN CURRENT_DATE()
                    ELSE attempt_date_1
                END,
                attempt_date_2 = CASE
                    WHEN attempt_date_1 IS NOT NULL AND attempt_date_2 IS NULL THEN CURRENT_DATE()
                    ELSE attempt_date_2
                END,
                attempt_date_3 = CASE
                    WHEN attempt_date_2 IS NOT NULL AND attempt_date_3 IS NULL THEN CURRENT_DATE()
                    ELSE attempt_date_3
                END,
                verification_complete = %s
            WHERE record_id = %s
            """,
            [verification_complete, record_id]
        )


def upsert_response(row):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            MERGE INTO {CATALOG}.master_responses AS target
            USING (
                SELECT
                    %s                    AS record_queue_id,
                    %s                    AS caller_id,
                    %s                    AS campaign_id,
                    %s                    AS caqh_id,
                    %s                    AS can_proceed_with_call,
                    CAST(%s AS TIMESTAMP) AS form_start_time,
                    CAST(%s AS TIMESTAMP) AS form_submission_time,
                    %s                    AS form_total_time_minutes,
                    %s                    AS verification_complete,
                    %s                    AS provider_currently_practicing_response,
                    %s                    AS provider_speciality_category_response,
                    %s                    AS phone_number_correct_response,
                    %s                    AS practice_location_name_response,
                    %s                    AS practice_location_address_response,
                    %s                    AS practice_location_suite_response,
                    %s                    AS practice_accepting_new_patients_response,
                    %s                    AS practice_accepting_new_medicare_patients_response,
                    %s                    AS enriched_provider_speciality_category_value,
                    %s                    AS enriched_phone_number_value,
                    %s                    AS enriched_practice_location_name_value,
                    %s                    AS enriched_practice_street_line_1_value,
                    %s                    AS enriched_practice_street_line_2_suite_value,
                    %s                    AS enriched_practice_city_value,
                    %s                    AS enriched_practice_zip_value,
                    %s                    AS enriched_practice_state_value,
                    %s                    AS standard_comments,
                    %s                    AS unique_comments
            ) AS source
            ON target.campaign_id = source.campaign_id
            AND target.caqh_id    = source.caqh_id

            WHEN MATCHED THEN UPDATE SET
                target.record_queue_id                                   = source.record_queue_id,
                target.caller_id                                         = source.caller_id,
                target.can_proceed_with_call                             = source.can_proceed_with_call,
                target.form_start_time                                   = source.form_start_time,
                target.form_submission_time                              = source.form_submission_time,
                target.form_total_time_minutes                           = source.form_total_time_minutes,
                target.verification_complete                             = source.verification_complete,
                target.provider_currently_practicing_response            = source.provider_currently_practicing_response,
                target.provider_speciality_category_response             = source.provider_speciality_category_response,
                target.phone_number_correct_response                     = source.phone_number_correct_response,
                target.practice_location_name_response                   = source.practice_location_name_response,
                target.practice_location_address_response                = source.practice_location_address_response,
                target.practice_location_suite_response                  = source.practice_location_suite_response,
                target.practice_accepting_new_patients_response          = source.practice_accepting_new_patients_response,
                target.practice_accepting_new_medicare_patients_response = source.practice_accepting_new_medicare_patients_response,
                target.enriched_provider_speciality_category_value       = source.enriched_provider_speciality_category_value,
                target.enriched_phone_number_value                       = source.enriched_phone_number_value,
                target.enriched_practice_location_name_value             = source.enriched_practice_location_name_value,
                target.enriched_practice_street_line_1_value             = source.enriched_practice_street_line_1_value,
                target.enriched_practice_street_line_2_suite_value       = source.enriched_practice_street_line_2_suite_value,
                target.enriched_practice_city_value                      = source.enriched_practice_city_value,
                target.enriched_practice_zip_value                       = source.enriched_practice_zip_value,
                target.enriched_practice_state_value                     = source.enriched_practice_state_value,
                target.standard_comments                                 = source.standard_comments,
                target.unique_comments                                   = source.unique_comments,
                target.attempt_date_1 = COALESCE(target.attempt_date_1, CURRENT_DATE()),
                target.attempt_date_2 = CASE
                                            WHEN target.attempt_date_1 IS NOT NULL
                                             AND target.attempt_date_2 IS NULL
                                            THEN CURRENT_DATE()
                                            ELSE target.attempt_date_2
                                        END,
                target.attempt_date_3 = CASE
                                            WHEN target.attempt_date_2 IS NOT NULL
                                             AND target.attempt_date_3 IS NULL
                                            THEN CURRENT_DATE()
                                            ELSE target.attempt_date_3
                                        END

            WHEN NOT MATCHED THEN INSERT (
                record_queue_id, caller_id, campaign_id, caqh_id,
                can_proceed_with_call, form_start_time, form_submission_time,
                form_total_time_minutes, verification_complete,
                provider_currently_practicing_response, provider_speciality_category_response,
                phone_number_correct_response, practice_location_name_response,
                practice_location_address_response, practice_location_suite_response,
                practice_accepting_new_patients_response, practice_accepting_new_medicare_patients_response,
                enriched_provider_speciality_category_value, enriched_phone_number_value,
                enriched_practice_location_name_value, enriched_practice_street_line_1_value,
                enriched_practice_street_line_2_suite_value, enriched_practice_city_value,
                enriched_practice_zip_value, enriched_practice_state_value,
                standard_comments, unique_comments,
                attempt_date_1, attempt_date_2, attempt_date_3
            ) VALUES (
                source.record_queue_id, source.caller_id, source.campaign_id, source.caqh_id,
                source.can_proceed_with_call, source.form_start_time, source.form_submission_time,
                source.form_total_time_minutes, source.verification_complete,
                source.provider_currently_practicing_response, source.provider_speciality_category_response,
                source.phone_number_correct_response, source.practice_location_name_response,
                source.practice_location_address_response, source.practice_location_suite_response,
                source.practice_accepting_new_patients_response, source.practice_accepting_new_medicare_patients_response,
                source.enriched_provider_speciality_category_value, source.enriched_phone_number_value,
                source.enriched_practice_location_name_value, source.enriched_practice_street_line_1_value,
                source.enriched_practice_street_line_2_suite_value, source.enriched_practice_city_value,
                source.enriched_practice_zip_value, source.enriched_practice_state_value,
                source.standard_comments, source.unique_comments,
                CURRENT_DATE(), NULL, NULL
            )
            """,
            [
                row["record_queue_id"],
                row["caller_id"],
                row["campaign_id"],
                row["caqh_id"],
                row["can_proceed_with_call"],
                row["form_start_time"],
                row["form_submission_time"],
                row["form_total_time_minutes"],
                row["verification_complete"],
                row["provider_currently_practicing_response"],
                row["provider_speciality_category_response"],
                row["phone_number_correct_response"],
                row["practice_location_name_response"],
                row["practice_location_address_response"],
                row["practice_location_suite_response"],
                row["practice_accepting_new_patients_response"],
                row["practice_accepting_new_medicare_patients_response"],
                row["enriched_provider_speciality_category_value"],
                row["enriched_phone_number_value"],
                row["enriched_practice_location_name_value"],
                row["enriched_practice_street_line_1_value"],
                row["enriched_practice_street_line_2_suite_value"],
                row["enriched_practice_city_value"],
                row["enriched_practice_zip_value"],
                row["enriched_practice_state_value"],
                row["standard_comments"],
                row["unique_comments"],
            ]
        )


def clear_form_state():
    for key in FORM_KEYS:
        if key in st.session_state:
            del st.session_state[key]


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def start_form(record):
    st.session_state.form_started = True
    st.session_state.form_start_time = now_text()
    st.session_state.form_start_epoch = time.time()
    st.session_state.form_page = 1
    st.session_state.form_prev_page = 5
    st.session_state.current_record = record
    clear_form_state()
    st.rerun()


def cancel_form():
    st.session_state.form_started = False
    st.session_state.form_start_time = None
    st.session_state.form_start_epoch = None
    st.session_state.form_page = 1
    st.session_state.current_record = None
    clear_form_state()
    st.rerun()


def show_errors(errors):
    for e in errors:
        st.error(e)


# ======================================================
# LOGIN PAGE
# ======================================================

def login_page():
    st.title("Provider Survey Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", type="primary")

    if submitted:
        user = check_login(username, password)
        if user is None:
            st.error("Username or password is not correct. Please try again.")
        else:
            st.session_state.logged_in = True
            st.session_state.username = user["username"]
            st.session_state.caller_id = user["caller_id"]
            st.session_state.role = user["role"]
            st.session_state.page = "home"
            st.rerun()


# ======================================================
# HOME PAGE
# ======================================================

def home_page():
    st.title("Caller Dashboard")
    st.write(f"Signed in as: **{st.session_state.username}**")

    col_logout, col_admin = st.columns([1, 1])
    with col_logout:
        if st.button("Logout", use_container_width=True):
            logout()
    with col_admin:
        if st.session_state.role == "admin":
            if st.button("Admin Page", use_container_width=True):
                st.session_state.page = "admin"
                st.rerun()

    st.divider()

    record, count = load_next_record()

    if record is None:
        st.info(
            "There are no records available to call right now. "
            "All records in your queue have been completed or are waiting for more assignments. "
            "Please contact your supervisor."
        )
        return

    attempt = attempt_number(record)
    provider_name = f"{record['db_first_name'] or ''} {record['db_last_name'] or ''}".strip() or "—"

    st.subheader("Next Record to Call")

    col_info, col_action = st.columns([3, 1])

    with col_info:
        st.markdown(f"**Provider:** {provider_name}")
        st.markdown(f"**Phone:** {record['db_office_phone_number'] or '—'}")
        st.markdown(f"**Campaign ID:** {record['campaign_id'] or '—'}")
        st.markdown(f"**CAQH ID:** {record['db_caqhid'] or '—'}")
        st.markdown(f"**Attempt:** {attempt} of 3")
        st.caption(f"{count} record(s) remaining in your queue")

    with col_action:
        if st.button("Start This Record", type="primary", use_container_width=True):
            start_form(record)


# ======================================================
# SURVEY — SHARED NAV HELPER
# ======================================================

def nav_buttons(back_page=None):
    col_back, col_next = st.columns([1, 5])
    with col_back:
        if back_page is not None:
            if st.button("← Back", use_container_width=True):
                st.session_state.form_page = back_page
                st.rerun()
    with col_next:
        return st.button("Next →", type="primary", use_container_width=True)


# ======================================================
# SURVEY — PAGE 1: Record Confirmation
# ======================================================

def survey_page_1():
    rec = st.session_state.current_record
    provider_name = f"{rec['db_first_name'] or ''} {rec['db_last_name'] or ''}".strip() or "—"
    attempt = attempt_number(rec)

    st.subheader("Record to Verify")
    st.markdown(f"**Provider:** {provider_name}")
    st.markdown(f"**CAQH ID:** {rec['db_caqhid'] or '—'}")
    st.markdown(f"**Campaign ID:** {rec['campaign_id'] or '—'}")
    st.markdown(f"**Phone Number:** {rec['db_office_phone_number'] or '—'}")
    st.markdown(f"**Attempt:** {attempt} of 3")

    st.info("Dial the number above. Click Next when the call connects.")

    if nav_buttons(back_page=None):
        st.session_state.form_page = 2
        st.rerun()


# ======================================================
# SURVEY — PAGE 2: Phone Number + Proceed Gate
# ======================================================

def survey_page_2():
    rec = st.session_state.current_record
    st.title("Practice Location Name and Number Validation")

    st.caption(f"On file — Phone number: {rec['db_office_phone_number'] or '—'}")
    st.radio(
        "Is the phone number correct? *",
        YES_NO,
        key="p2_phone_correct",
        index=None,
        horizontal=True
    )
    if st.session_state.get("p2_phone_correct") == "No":
        st.text_input("If no, what is the correct phone number? *", key="p2_phone_enrichment")

    st.divider()

    st.radio(
        "Can you proceed with verification? *",
        YES_NO,
        key="p2_can_continue",
        index=None,
        horizontal=True
    )

    if st.session_state.get("p2_can_continue") == "Yes":
        st.divider()
        st.caption(f"On file — Practice name: {rec['db_practice_location_name'] or '—'}")
        st.radio(
            "Is the practice name correct? *",
            YES_NO,
            key="p2_name_correct",
            index=None,
            horizontal=True
        )
        if st.session_state.get("p2_name_correct") == "No":
            st.text_input(
                "If no, what is the correct practice location name? *",
                key="p2_name_enrichment"
            )

    if nav_buttons(back_page=1):
        errors = []
        if not st.session_state.get("p2_phone_correct"):
            errors.append("Phone number verification is required.")
        if st.session_state.get("p2_phone_correct") == "No" and \
                not st.session_state.get("p2_phone_enrichment", "").strip():
            errors.append("Correct phone number is required.")
        if not st.session_state.get("p2_can_continue"):
            errors.append('"Can you proceed with verification?" is required.')
        if st.session_state.get("p2_can_continue") == "Yes":
            if not st.session_state.get("p2_name_correct"):
                errors.append("Practice name verification is required.")
            if st.session_state.get("p2_name_correct") == "No" and \
                    not st.session_state.get("p2_name_enrichment", "").strip():
                errors.append("Correct practice location name is required.")

        if errors:
            show_errors(errors)
        else:
            if st.session_state.p2_can_continue == "No":
                st.session_state.form_prev_page = 2
                st.session_state.form_page = 6
            else:
                st.session_state.form_prev_page = 5
                st.session_state.form_page = 3
            st.rerun()


# ======================================================
# SURVEY — PAGE 3: Provider Identity & Practicing Status
# ======================================================

def survey_page_3():
    rec = st.session_state.current_record
    st.title("Provider Identity & Practicing Status")

    st.radio(
        "Is this provider currently practicing at this location? *",
        YES_NO,
        key="p3_currently_practicing",
        index=None,
        horizontal=True
    )

    st.divider()

    st.caption(f"On file — Specialty: {rec['db_specialty_list'] or '—'}")
    st.radio(
        "Is the specialty correct? *",
        YES_NO,
        key="p3_specialty_correct",
        index=None,
        horizontal=True
    )
    if st.session_state.get("p3_specialty_correct") == "No":
        st.text_input("If no, what is the correct specialty? *", key="p3_specialty_enrichment")

    if nav_buttons(back_page=2):
        errors = []
        if not st.session_state.get("p3_currently_practicing"):
            errors.append("Practicing status is required.")
        if not st.session_state.get("p3_specialty_correct"):
            errors.append("Specialty verification is required.")
        if st.session_state.get("p3_specialty_correct") == "No" and \
                not st.session_state.get("p3_specialty_enrichment", "").strip():
            errors.append("Correct specialty is required.")

        if errors:
            show_errors(errors)
        else:
            st.session_state.form_page = 4
            st.rerun()


# ======================================================
# SURVEY — PAGE 4: Practice Location Validation
# ======================================================

def survey_page_4():
    rec = st.session_state.current_record

    addr_parts = [
        rec.get("db_street"),
        rec.get("db_street_2"),
        rec.get("db_city"),
        rec.get("db_state"),
        rec.get("db_zip_code"),
    ]
    addr_on_file = " · ".join(p for p in addr_parts if p) or "—"

    st.title("Practice Location Validation")

    st.caption(f"On file — Address: {addr_on_file}")
    st.radio(
        "Is the address correct? *",
        YES_NO,
        key="p4_address_correct",
        index=None,
        horizontal=True
    )
    if st.session_state.get("p4_address_correct") == "No":
        st.caption("Example: 123 Main St · City · State · 12345  —  commas are restricted")
        st.text_input("Address line 1 *", key="p4_addr_line1")
        col_city, col_state, col_zip = st.columns([3, 1, 1])
        with col_city:
            st.text_input("City *", key="p4_city")
        with col_state:
            st.selectbox("State *", STATE_CODES, key="p4_state", index=None, placeholder="State...")
        with col_zip:
            st.text_input("ZIP *", key="p4_zip")

    st.divider()

    st.caption(f"On file — Suite: {rec.get('db_street_2') or '—'}")
    st.radio(
        "Is the suite number correct? *",
        YES_NO,
        key="p4_suite_correct",
        index=None,
        horizontal=True
    )
    if st.session_state.get("p4_suite_correct") == "No":
        st.text_input("If no, what is the correct suite number? *", key="p4_suite_enrichment")

    if nav_buttons(back_page=3):
        errors = []
        if not st.session_state.get("p4_address_correct"):
            errors.append("Address verification is required.")
        if st.session_state.get("p4_address_correct") == "No":
            if not st.session_state.get("p4_addr_line1", "").strip():
                errors.append("Address line 1 is required.")
            if not st.session_state.get("p4_city", "").strip():
                errors.append("City is required.")
            if not st.session_state.get("p4_state"):
                errors.append("State is required.")
            if not st.session_state.get("p4_zip", "").strip():
                errors.append("ZIP code is required.")
        if not st.session_state.get("p4_suite_correct"):
            errors.append("Suite number verification is required.")
        if st.session_state.get("p4_suite_correct") == "No" and \
                not st.session_state.get("p4_suite_enrichment", "").strip():
            errors.append("Correct suite number is required.")

        if errors:
            show_errors(errors)
        else:
            st.session_state.form_page = 5
            st.rerun()


# ======================================================
# SURVEY — PAGE 5: New Patients Admission Status
# ======================================================

def survey_page_5():
    st.title("New Patients Admission Status Validation")

    st.radio(
        "Is the practice accepting new patients? *",
        YES_NO,
        key="p5_accepting_new",
        index=None,
        horizontal=True
    )

    st.divider()

    st.radio(
        "Is the practice accepting new Medicare patients? *",
        YES_NO,
        key="p5_accepting_medicare",
        index=None,
        horizontal=True
    )

    if nav_buttons(back_page=4):
        errors = []
        if not st.session_state.get("p5_accepting_new"):
            errors.append("Accepting new patients status is required.")
        if not st.session_state.get("p5_accepting_medicare"):
            errors.append("Accepting Medicare patients status is required.")

        if errors:
            show_errors(errors)
        else:
            st.session_state.form_page = 6
            st.rerun()


# ======================================================
# SURVEY — PAGE 6: Completion Status
# ======================================================

def survey_page_6():
    st.title("Completion Status")

    if st.session_state.get("p2_can_continue") == "No":
        st.warning(
            "You could not proceed with the verification. "
            "This call will be saved as an attempt."
        )

    st.radio(
        "Verification complete? *",
        YES_NO,
        key="p6_verification_complete",
        index=None,
        horizontal=True
    )

    st.divider()

    st.subheader("Standard Comments")
    st.radio(
        "Select a standard comment",
        STANDARD_COMMENTS,
        key="p6_standard_comments",
        index=None
    )

    st.divider()

    st.subheader("Unique or Nonstandard Comments")
    st.text_area(
        "Enter any unique or nonstandard comments",
        key="p6_unique_comments"
    )

    col_back, col_submit = st.columns([1, 5])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.form_page = st.session_state.form_prev_page
            st.rerun()
    with col_submit:
        submit = st.button("Submit", type="primary", use_container_width=True)

    if submit:
        if not st.session_state.get("p6_verification_complete"):
            st.error("Verification complete is required.")
            st.stop()

        rec = st.session_state.current_record
        submission_time = now_text()
        total_minutes = round((time.time() - st.session_state.form_start_epoch) / 60)

        addr_no      = st.session_state.get("p4_address_correct")  == "No"
        suite_no     = st.session_state.get("p4_suite_correct")    == "No"
        specialty_no = st.session_state.get("p3_specialty_correct") == "No"
        phone_no     = st.session_state.get("p2_phone_correct")    == "No"
        name_no      = st.session_state.get("p2_name_correct")     == "No"
        verified     = to_bool(st.session_state.get("p6_verification_complete"))

        row = {
            "record_queue_id":                                   rec["record_id"],
            "caller_id":                                         st.session_state.caller_id,
            "campaign_id":                                       rec["campaign_id"],
            "caqh_id":                                           rec["db_caqhid"],
            "can_proceed_with_call":                             to_bool(st.session_state.get("p2_can_continue")),
            "form_start_time":                                   st.session_state.form_start_time,
            "form_submission_time":                              submission_time,
            "form_total_time_minutes":                           total_minutes,
            "verification_complete":                             verified,
            "provider_currently_practicing_response":            to_bool(st.session_state.get("p3_currently_practicing")),
            "provider_speciality_category_response":             to_bool(st.session_state.get("p3_specialty_correct")),
            "phone_number_correct_response":                     to_bool(st.session_state.get("p2_phone_correct")),
            "practice_location_name_response":                   to_bool(st.session_state.get("p2_name_correct")),
            "practice_location_address_response":                to_bool(st.session_state.get("p4_address_correct")),
            "practice_location_suite_response":                  to_bool(st.session_state.get("p4_suite_correct")),
            "practice_accepting_new_patients_response":          to_bool(st.session_state.get("p5_accepting_new")),
            "practice_accepting_new_medicare_patients_response": to_bool(st.session_state.get("p5_accepting_medicare")),
            "enriched_provider_speciality_category_value":       st.session_state.get("p3_specialty_enrichment", "").strip() if specialty_no else "",
            "enriched_phone_number_value":                       st.session_state.get("p2_phone_enrichment", "").strip() if phone_no else "",
            "enriched_practice_location_name_value":             st.session_state.get("p2_name_enrichment", "").strip() if name_no else "",
            "enriched_practice_street_line_1_value":             st.session_state.get("p4_addr_line1", "").strip() if addr_no else "",
            "enriched_practice_street_line_2_suite_value":       st.session_state.get("p4_suite_enrichment", "").strip() if suite_no else "",
            "enriched_practice_city_value":                      st.session_state.get("p4_city", "").strip() if addr_no else "",
            "enriched_practice_zip_value":                       st.session_state.get("p4_zip", "").strip() if addr_no else "",
            "enriched_practice_state_value":                     st.session_state.get("p4_state", "") if addr_no else "",
            "standard_comments":                                 st.session_state.get("p6_standard_comments", "") or "",
            "unique_comments":                                   st.session_state.get("p6_unique_comments", "").strip(),
        }

        upsert_response(row)
        update_queue_record(rec["record_id"], verified)

        st.session_state.form_started = False
        st.session_state.form_start_time = None
        st.session_state.form_start_epoch = None
        st.session_state.form_page = 1
        st.session_state.current_record = None
        clear_form_state()
        st.rerun()


# ======================================================
# SURVEY — ROUTER
# ======================================================

def survey_page():
    st.progress(st.session_state.form_page / 6, text=f"Step {st.session_state.form_page} of 6")

    col_cancel, _ = st.columns([1, 5])
    with col_cancel:
        if st.button("✕ Cancel", use_container_width=True):
            cancel_form()

    st.divider()

    pages = {
        1: survey_page_1,
        2: survey_page_2,
        3: survey_page_3,
        4: survey_page_4,
        5: survey_page_5,
        6: survey_page_6,
    }
    pages[st.session_state.form_page]()


# ======================================================
# ADMIN PAGE
# ======================================================

def admin_page():
    st.title("Admin Dashboard")

    if st.session_state.role != "admin":
        st.error("You do not have permission to view this page.")
        return

    if st.button("← Back to Dashboard"):
        st.session_state.page = "home"
        st.rerun()

    st.divider()

    conn = get_db_connection()

    st.subheader("Record Queue")
    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT * FROM {CATALOG}.record_queue ORDER BY record_id ASC"
        )
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
    df_queue = pd.DataFrame(rows, columns=columns)
    st.write(f"Total records in queue: **{len(df_queue)}**")
    st.dataframe(df_queue, use_container_width=True, hide_index=True)
    st.download_button(
        label="Download queue CSV",
        data=df_queue.to_csv(index=False),
        file_name="record_queue.csv",
        mime="text/csv"
    )

    st.divider()

    st.subheader("Master Responses")
    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT * FROM {CATALOG}.master_responses ORDER BY form_submission_time DESC"
        )
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
    df_responses = pd.DataFrame(rows, columns=columns)
    st.write(f"Total responses submitted: **{len(df_responses)}**")
    st.dataframe(df_responses, use_container_width=True, hide_index=True)
    st.download_button(
        label="Download responses CSV",
        data=df_responses.to_csv(index=False),
        file_name="master_responses.csv",
        mime="text/csv"
    )


# ======================================================
# ROUTER
# ======================================================

if not st.session_state.logged_in:
    login_page()
else:
    if st.session_state.form_started:
        survey_page()
    elif st.session_state.page == "admin":
        admin_page()
    else:
        home_page()
