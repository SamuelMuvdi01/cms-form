import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st


# ======================================================
# FILE CONFIG
# ======================================================

USERS_CSV = "users.csv"
MASTER_CSV = "master_responses.csv"


# ======================================================
# FORM CONFIG
# ======================================================

YES_NO = ["Yes", "No"]
CORRECT_INCORRECT = ["Correct", "Incorrect"]

STATE_CODES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "AS", "GU", "MP", "PR", "VI"
]

MASTER_COLUMNS = [
    "caller_id",
    "campaign_id",
    "can_proceed_with_call",
    "form_start_time",
    "form_submission_time",
    "form_total_time_minutes",
    "attempt_date_1",
    "attempt_date_2",
    "attempt_date_3",
    "verification_complete",
    "caqh_id",
    "provider_currently_practicing_response",
    "provider_speciality_category_response",
    "phone_number_correct_response",
    "practice_location_name_response",
    "practice_location_address_response",
    "practice_location_suite_response",
    "practice_accepting_new_patients_response",
    "practice_accepting_new_medicare_patients_response",
    "enriched_provider_speciality_category_value",
    "enriched_phone_number_value",
    "enriched_practice_location_name_value",
    "enriched_practice_street_line_1_value",
    "enriched_practice_Street_line_2_suite_value",
    "enriched_practice_city_value",
    "enriched_practice_zip_value",
    "enriched_practice_state_value",
]

CALLER_REPORT_COLUMNS = [
    "caller_id",
    "campaign_id",
    "form_submission_time",
    "caqh_id",
    "can_proceed_with_call",
    "attempt_date_1",
    "attempt_date_2",
    "attempt_date_3",
    "verification_complete",
    "provider_currently_practicing_response",
    "provider_speciality_category_response",
    "phone_number_correct_response",
    "practice_location_name_response",
    "practice_location_address_response",
    "practice_location_suite_response",
    "practice_accepting_new_patients_response",
    "practice_accepting_new_medicare_patients_response",
    "enriched_provider_speciality_category_value",
    "enriched_phone_number_value",
    "enriched_practice_location_name_value",
    "enriched_practice_street_line_1_value",
    "enriched_practice_Street_line_2_suite_value",
    "enriched_practice_city_value",
    "enriched_practice_zip_value",
    "enriched_practice_state_value",
]

# All widget keys used across the 6 pages — cleared when starting or cancelling a form.
FORM_KEYS = [
    "p1_batch_id", "p1_caqh_id",
    "p2_phone_correct", "p2_phone_enrichment",
    "p2_name_correct", "p2_name_enrichment",
    "p2_can_continue",
    "p3_currently_practicing",
    "p3_specialty_correct", "p3_specialty_enrichment",
    "p4_address_correct",
    "p4_addr_line1", "p4_addr_line2", "p4_city", "p4_state", "p4_zip",
    "p4_suite_correct", "p4_suite_enrichment",
    "p5_accepting_new", "p5_accepting_medicare",
    "p6_verification_complete",
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
# CREATE STARTER CSV FILES
# ======================================================

def setup_csv_files():
    if not os.path.exists(USERS_CSV):
        users = pd.DataFrame([
            {"caller_id": "admin",     "password": "admin123",  "role": "admin"},
            {"caller_id": "caller001", "password": "caller123", "role": "caller"},
            {"caller_id": "caller002", "password": "caller456", "role": "caller"},
        ])
        users.to_csv(USERS_CSV, index=False)

    if not os.path.exists(MASTER_CSV):
        pd.DataFrame(columns=MASTER_COLUMNS).to_csv(MASTER_CSV, index=False)


setup_csv_files()


# ======================================================
# SESSION STATE
# ======================================================

def init_session_state():
    defaults = {
        "logged_in": False,
        "caller_id": None,
        "role": None,
        "page": "home",
        "form_started": False,
        "form_start_time": None,
        "form_start_epoch": None,
        "caller_report_csv": None,
        "form_page": 1,
        "form_prev_page": 5,
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
    """Converts Yes/Correct → True, No/Incorrect → False, anything else → None."""
    return {"Yes": True, "No": False, "Correct": True, "Incorrect": False}.get(val)


def check_login(caller_id, password):
    users = pd.read_csv(USERS_CSV, dtype=str)
    match = users[
        (users["caller_id"] == caller_id.strip()) &
        (users["password"] == password)
    ]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def clear_form_state():
    for key in FORM_KEYS:
        if key in st.session_state:
            del st.session_state[key]


def logout():
    st.session_state.logged_in = False
    st.session_state.caller_id = None
    st.session_state.role = None
    st.session_state.page = "home"
    st.session_state.form_started = False
    st.session_state.form_start_time = None
    st.session_state.form_start_epoch = None
    st.session_state.caller_report_csv = None
    st.session_state.form_page = 1
    clear_form_state()
    st.rerun()


def start_form():
    st.session_state.form_started = True
    st.session_state.form_start_time = now_text()
    st.session_state.form_start_epoch = time.time()
    st.session_state.caller_report_csv = None
    st.session_state.form_page = 1
    st.session_state.form_prev_page = 5
    clear_form_state()
    st.rerun()


def cancel_form():
    st.session_state.form_started = False
    st.session_state.form_start_time = None
    st.session_state.form_start_epoch = None
    st.session_state.form_page = 1
    clear_form_state()
    st.rerun()


def is_already_verified(campaign_id, caqh_id):
    df = pd.read_csv(MASTER_CSV, dtype=str)
    mask = (df["campaign_id"] == campaign_id) & (df["caqh_id"] == caqh_id)
    existing = df[mask]
    if existing.empty:
        return False
    return str(existing.iloc[0]["verification_complete"]).strip().lower() == "true"


def upsert_response(row):
    today = datetime.now().strftime("%Y-%m-%d")
    df = pd.read_csv(MASTER_CSV, dtype=str)

    mask = (df["campaign_id"] == row["campaign_id"]) & (df["caqh_id"] == row["caqh_id"])
    existing_idx = df.index[mask].tolist()

    if not existing_idx:
        row["attempt_date_1"] = today
        row["attempt_date_2"] = ""
        row["attempt_date_3"] = ""
        df = pd.concat([df, pd.DataFrame([row], columns=MASTER_COLUMNS)], ignore_index=True)
    else:
        idx = existing_idx[0]
        d1 = str(df.at[idx, "attempt_date_1"]).strip()
        d2 = str(df.at[idx, "attempt_date_2"]).strip()
        d3 = str(df.at[idx, "attempt_date_3"]).strip()

        for col in MASTER_COLUMNS:
            if col not in ("attempt_date_1", "attempt_date_2", "attempt_date_3") and col in row:
                df.at[idx, col] = row[col]

        if not d1 or d1 == "nan":
            df.at[idx, "attempt_date_1"] = today
            df.at[idx, "attempt_date_2"] = ""
            df.at[idx, "attempt_date_3"] = ""
        elif not d2 or d2 == "nan":
            df.at[idx, "attempt_date_2"] = today
        elif not d3 or d3 == "nan":
            df.at[idx, "attempt_date_3"] = today

        row["attempt_date_1"] = str(df.at[idx, "attempt_date_1"])
        row["attempt_date_2"] = str(df.at[idx, "attempt_date_2"])
        row["attempt_date_3"] = str(df.at[idx, "attempt_date_3"])

    df.to_csv(MASTER_CSV, index=False)
    return row


def make_caller_report(row):
    report_row = {col: row[col] for col in CALLER_REPORT_COLUMNS}
    return pd.DataFrame([report_row]).to_csv(index=False)


def show_errors(errors):
    for e in errors:
        st.error(e)


# ======================================================
# LOGIN PAGE
# ======================================================

def login_page():
    st.title("🔐 Provider Survey Login")

    st.write("Demo users:")
    st.code("admin / admin123\ncaller001 / caller123\ncaller002 / caller456")

    with st.form("login_form"):
        caller_id = st.text_input("Caller ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", type="primary")

    if submitted:
        user = check_login(caller_id, password)
        if user is None:
            st.error("Invalid caller ID or password.")
        else:
            st.session_state.logged_in = True
            st.session_state.caller_id = user["caller_id"]
            st.session_state.role = user["role"]
            st.session_state.page = "home"
            st.rerun()


# ======================================================
# HOME PAGE
# ======================================================

def home_page():
    st.title("Caller Dashboard")
    st.write(f"Signed in as: **{st.session_state.caller_id}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Start Form", type="primary", use_container_width=True):
            start_form()
    with col2:
        if st.button("Logout", use_container_width=True):
            logout()
    with col3:
        if st.session_state.role == "admin":
            if st.button("Admin Page", use_container_width=True):
                st.session_state.page = "admin"
                st.rerun()

    if st.session_state.caller_report_csv:
        st.divider()
        st.success("Form submitted successfully.")
        st.write("Would you like to save a copy of these results to your PC?")
        st.download_button(
            label="Yes, save results to my PC",
            data=st.session_state.caller_report_csv,
            file_name="caller_provider_survey_report.csv",
            mime="text/csv",
            type="primary"
        )


# ======================================================
# SURVEY — SHARED NAV HELPER
# ======================================================

def nav_buttons(back_page=None):
    """Renders Back / Next →. Returns True when Next is clicked."""
    col_back, col_next = st.columns([1, 5])
    with col_back:
        if back_page is not None:
            if st.button("← Back", use_container_width=True):
                st.session_state.form_page = back_page
                st.rerun()
    with col_next:
        return st.button("Next →", type="primary", use_container_width=True)


# ======================================================
# SURVEY — PAGE 1: Call Metadata
# ======================================================

def survey_page_1():
    st.title("Call Metadata")

    st.info(f"Caller ID: **{st.session_state.caller_id}**")
    st.text_input("Batch ID *", key="p1_batch_id")
    st.text_input("CAQH ID *", key="p1_caqh_id")

    if nav_buttons(back_page=None):
        errors = []
        if not st.session_state.get("p1_batch_id", "").strip():
            errors.append("Batch ID is required.")
        if not st.session_state.get("p1_caqh_id", "").strip():
            errors.append("CAQH ID is required.")

        if not errors and is_already_verified(
            st.session_state.get("p1_batch_id", "").strip(),
            st.session_state.get("p1_caqh_id", "").strip()
        ):
            errors.append("This record is already verified — no further action needed.")

        if errors:
            show_errors(errors)
        else:
            st.session_state.form_page = 2
            st.rerun()


# ======================================================
# SURVEY — PAGE 2: Practice Location Name & Number
# ======================================================

def survey_page_2():
    st.title("Practice Location Name and Number Validation")

    # Q4 — Phone number
    st.subheader("Phone Number")
    st.radio(
        "Is the phone number correct? *",
        CORRECT_INCORRECT,
        key="p2_phone_correct",
        index=None,
        horizontal=True
    )
    if st.session_state.get("p2_phone_correct") == "Incorrect":
        st.text_input("What is the correct phone number? *", key="p2_phone_enrichment")

    st.divider()

    # Q5 — Practice name
    st.subheader("Practice Name")
    st.radio(
        "Is the practice name correct? *",
        CORRECT_INCORRECT,
        key="p2_name_correct",
        index=None,
        horizontal=True
    )
    if st.session_state.get("p2_name_correct") == "Incorrect":
        st.text_input("What is the correct practice name? *", key="p2_name_enrichment")

    st.divider()

    # Continuation gate
    st.subheader("Continuation Check")
    st.radio(
        "Can you continue with verification? *",
        YES_NO,
        key="p2_can_continue",
        index=None,
        horizontal=True
    )

    if nav_buttons(back_page=1):
        errors = []
        if not st.session_state.get("p2_phone_correct"):
            errors.append("Phone number verification is required.")
        if st.session_state.get("p2_phone_correct") == "Incorrect" and \
                not st.session_state.get("p2_phone_enrichment", "").strip():
            errors.append("Correct phone number is required.")
        if not st.session_state.get("p2_name_correct"):
            errors.append("Practice name verification is required.")
        if st.session_state.get("p2_name_correct") == "Incorrect" and \
                not st.session_state.get("p2_name_enrichment", "").strip():
            errors.append("Correct practice name is required.")
        if not st.session_state.get("p2_can_continue"):
            errors.append('"Can you continue with verification?" is required.')

        if errors:
            show_errors(errors)
        else:
            if st.session_state.p2_can_continue == "No":
                # Skip to completion — pages 3-5 unanswered
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
    st.title("Provider Identity & Practicing Status")

    # Q6 — Currently practicing (Yes/No only, no enrichment)
    st.subheader("Practicing Status")
    st.radio(
        "Is this provider currently practicing at this location? *",
        YES_NO,
        key="p3_currently_practicing",
        index=None,
        horizontal=True
    )

    st.divider()

    # Q7 — Specialty
    st.subheader("Specialty")
    st.radio(
        "Is the specialty correct? *",
        CORRECT_INCORRECT,
        key="p3_specialty_correct",
        index=None,
        horizontal=True
    )
    if st.session_state.get("p3_specialty_correct") == "Incorrect":
        st.text_input("What is the correct specialty? *", key="p3_specialty_enrichment")

    if nav_buttons(back_page=2):
        errors = []
        if not st.session_state.get("p3_currently_practicing"):
            errors.append("Practicing status is required.")
        if not st.session_state.get("p3_specialty_correct"):
            errors.append("Specialty verification is required.")
        if st.session_state.get("p3_specialty_correct") == "Incorrect" and \
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
    st.title("Practice Location Validation")

    # Q8 — Address
    st.subheader("Address")
    st.radio(
        "Is the address correct? *",
        CORRECT_INCORRECT,
        key="p4_address_correct",
        index=None,
        horizontal=True
    )
    if st.session_state.get("p4_address_correct") == "Incorrect":
        st.text_input("Correct address line 1 *", key="p4_addr_line1")
        st.text_input("Correct address line 2", key="p4_addr_line2")
        col_city, col_state, col_zip = st.columns([3, 1, 1])
        with col_city:
            st.text_input("Correct city *", key="p4_city")
        with col_state:
            st.selectbox("State *", STATE_CODES, key="p4_state", index=None, placeholder="State...")
        with col_zip:
            st.text_input("ZIP *", key="p4_zip")

    st.divider()

    # Q9 — Suite
    st.subheader("Suite")
    st.radio(
        "Is the suite correct? *",
        CORRECT_INCORRECT,
        key="p4_suite_correct",
        index=None,
        horizontal=True
    )
    if st.session_state.get("p4_suite_correct") == "Incorrect":
        st.text_input("What is the correct suite number? *", key="p4_suite_enrichment")

    if nav_buttons(back_page=3):
        errors = []
        if not st.session_state.get("p4_address_correct"):
            errors.append("Address verification is required.")
        if st.session_state.get("p4_address_correct") == "Incorrect":
            if not st.session_state.get("p4_addr_line1", "").strip():
                errors.append("Correct address line 1 is required.")
            if not st.session_state.get("p4_city", "").strip():
                errors.append("Correct city is required.")
            if not st.session_state.get("p4_state"):
                errors.append("Correct state is required.")
            if not st.session_state.get("p4_zip", "").strip():
                errors.append("Correct ZIP code is required.")
        if not st.session_state.get("p4_suite_correct"):
            errors.append("Suite verification is required.")
        if st.session_state.get("p4_suite_correct") == "Incorrect" and \
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

    # Q10 — Accepting new patients (Yes/No only, no enrichment)
    st.subheader("New Patients")
    st.radio(
        "Is the practice accepting new patients? *",
        YES_NO,
        key="p5_accepting_new",
        index=None,
        horizontal=True
    )

    st.divider()

    # Q11 — Accepting Medicare patients (Yes/No only, no enrichment)
    st.subheader("Medicare Patients")
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
            "The caller could not continue with verification. "
            "This submission will be logged as an attempt."
        )

    st.checkbox("Verification complete", key="p6_verification_complete")

    col_back, col_submit = st.columns([1, 5])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.form_page = st.session_state.form_prev_page
            st.rerun()
    with col_submit:
        submit = st.button("Submit", type="primary", use_container_width=True)

    if submit:
        submission_time = now_text()
        total_minutes = round((time.time() - st.session_state.form_start_epoch) / 60)

        addr_incorrect    = st.session_state.get("p4_address_correct") == "Incorrect"
        suite_incorrect   = st.session_state.get("p4_suite_correct")   == "Incorrect"
        specialty_incorrect = st.session_state.get("p3_specialty_correct") == "Incorrect"

        # Suite enrichment takes priority over address line 2 for the shared column.
        if suite_incorrect:
            line2_suite = st.session_state.get("p4_suite_enrichment", "").strip()
        elif addr_incorrect:
            line2_suite = st.session_state.get("p4_addr_line2", "").strip()
        else:
            line2_suite = ""

        row = {
            "caller_id":                                         st.session_state.caller_id,
            "campaign_id":                                       st.session_state.get("p1_batch_id", "").strip(),
            "can_proceed_with_call":                             st.session_state.get("p2_can_continue", ""),
            "form_start_time":                                   st.session_state.form_start_time,
            "form_submission_time":                              submission_time,
            "form_total_time_minutes":                           total_minutes,
            "attempt_date_1":                                    "",
            "attempt_date_2":                                    "",
            "attempt_date_3":                                    "",
            "verification_complete":                             st.session_state.get("p6_verification_complete", False),
            "caqh_id":                                           st.session_state.get("p1_caqh_id", "").strip(),
            "provider_currently_practicing_response":            to_bool(st.session_state.get("p3_currently_practicing")),
            "provider_speciality_category_response":             to_bool(st.session_state.get("p3_specialty_correct")),
            "phone_number_correct_response":                     to_bool(st.session_state.get("p2_phone_correct")),
            "practice_location_name_response":                   to_bool(st.session_state.get("p2_name_correct")),
            "practice_location_address_response":                to_bool(st.session_state.get("p4_address_correct")),
            "practice_location_suite_response":                  to_bool(st.session_state.get("p4_suite_correct")),
            "practice_accepting_new_patients_response":          to_bool(st.session_state.get("p5_accepting_new")),
            "practice_accepting_new_medicare_patients_response": to_bool(st.session_state.get("p5_accepting_medicare")),
            "enriched_provider_speciality_category_value":       st.session_state.get("p3_specialty_enrichment", "").strip() if specialty_incorrect else "",
            "enriched_phone_number_value":                       st.session_state.get("p2_phone_enrichment", "").strip() if st.session_state.get("p2_phone_correct") == "Incorrect" else "",
            "enriched_practice_location_name_value":             st.session_state.get("p2_name_enrichment", "").strip() if st.session_state.get("p2_name_correct") == "Incorrect" else "",
            "enriched_practice_street_line_1_value":             st.session_state.get("p4_addr_line1", "").strip() if addr_incorrect else "",
            "enriched_practice_Street_line_2_suite_value":       line2_suite,
            "enriched_practice_city_value":                      st.session_state.get("p4_city", "").strip() if addr_incorrect else "",
            "enriched_practice_zip_value":                       st.session_state.get("p4_zip", "").strip() if addr_incorrect else "",
            "enriched_practice_state_value":                     st.session_state.get("p4_state", "") if addr_incorrect else "",
        }

        row = upsert_response(row)
        st.session_state.caller_report_csv = make_caller_report(row)
        st.session_state.form_started = False
        st.session_state.form_start_time = None
        st.session_state.form_start_epoch = None
        st.session_state.form_page = 1
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
    st.title("📊 Admin Page")

    if st.session_state.role != "admin":
        st.error("You do not have access to this page.")
        return

    if st.button("Back to Dashboard"):
        st.session_state.page = "home"
        st.rerun()

    st.divider()

    df = pd.read_csv(MASTER_CSV, dtype=str)
    st.write(f"Total records: **{len(df)}**")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        label="Download master CSV",
        data=df.to_csv(index=False),
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
