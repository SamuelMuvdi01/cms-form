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

STATE_CODES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "AS", "GU", "MP", "PR", "VI"
]

CORRECT_INCORRECT = ["Correct", "Incorrect"]


# Matches DDL column order (response_id is GENERATED ALWAYS AS IDENTITY — excluded).
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
    "enriched_provider_currently_practicing_value",
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
    "enriched_provider_currently_practicing_value",
    "enriched_provider_speciality_category_value",
    "enriched_phone_number_value",
    "enriched_practice_location_name_value",
    "enriched_practice_street_line_1_value",
    "enriched_practice_Street_line_2_suite_value",
    "enriched_practice_city_value",
    "enriched_practice_zip_value",
    "enriched_practice_state_value",
]

# NOT NULL user-input fields (auto-populated fields excluded).
REQUIRED_FIELDS = [
    "campaign_id",
    "can_proceed_with_call",
    "caqh_id",
    "provider_currently_practicing_response",
    "provider_speciality_category_response",
    "phone_number_correct_response",
    "practice_location_name_response",
    "practice_location_address_response",
    "practice_location_suite_response",
    "practice_accepting_new_patients_response",
    "practice_accepting_new_medicare_patients_response",
    "enriched_provider_currently_practicing_value",
    "enriched_provider_speciality_category_value",
]

FIELD_LABELS = {
    "campaign_id": "Campaign ID",
    "can_proceed_with_call": "Can we proceed with the call?",
    "caqh_id": "CAQH ID",
    "provider_currently_practicing_response": "Is the provider currently practicing information correct?",
    "provider_speciality_category_response": "Is the specialty category correct?",
    "phone_number_correct_response": "Is the phone number correct?",
    "practice_location_name_response": "Is the practice location name correct?",
    "practice_location_address_response": "Is the practice location address correct?",
    "practice_location_suite_response": "Is the practice location suite correct?",
    "practice_accepting_new_patients_response": "Is the accepting new patients information correct?",
    "practice_accepting_new_medicare_patients_response": "Is the accepting Medicare patients information correct?",
    "enriched_provider_currently_practicing_value": "Enriched provider currently practicing value",
    "enriched_provider_speciality_category_value": "Enriched specialty category value",
}


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
        "form_version": 0,
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


def date_to_text(value):
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d")


def correct_incorrect_to_bool(val):
    if val == "Correct":
        return True
    if val == "Incorrect":
        return False
    return None


def check_login(caller_id, password):
    users = pd.read_csv(USERS_CSV, dtype=str)

    match = users[
        (users["caller_id"] == caller_id.strip()) &
        (users["password"] == password)
    ]

    if match.empty:
        return None

    return match.iloc[0].to_dict()


def logout():
    st.session_state.logged_in = False
    st.session_state.caller_id = None
    st.session_state.role = None
    st.session_state.page = "home"
    st.session_state.form_started = False
    st.session_state.form_start_time = None
    st.session_state.form_start_epoch = None
    st.session_state.caller_report_csv = None
    st.session_state.form_version += 1
    st.rerun()


def start_form():
    st.session_state.form_started = True
    st.session_state.form_start_time = now_text()
    st.session_state.form_start_epoch = time.time()
    st.session_state.caller_report_csv = None
    st.session_state.form_version += 1
    st.rerun()


def cancel_form():
    st.session_state.form_started = False
    st.session_state.form_start_time = None
    st.session_state.form_start_epoch = None
    st.session_state.form_version += 1
    st.rerun()


def validate_required_fields(row):
    errors = []

    for field in REQUIRED_FIELDS:
        value = row.get(field)

        # Boolean fields fail only when None (not selected); True/False are valid.
        if value is None or str(value).strip() == "":
            label = FIELD_LABELS.get(field, field)
            errors.append(f"{label} is required.")

    return errors


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
# SURVEY PAGE
# ======================================================

def survey_page():
    st.title("📝 Provider Survey Form")

    if st.button("Cancel Form"):
        cancel_form()

    form_key = f"provider_survey_form_{st.session_state.form_version}"

    with st.form(form_key, clear_on_submit=False):

        # --------------------------------------------------
        # Call Metadata
        # --------------------------------------------------
        st.subheader("Call Metadata")

        campaign_id = st.text_input("Campaign ID *")

        caqh_id = st.text_input("CAQH ID *")

        can_proceed_with_call = st.radio(
            "Can we proceed with the call? *",
            YES_NO,
            index=None
        )

        verification_complete = st.checkbox("Verification complete")

        # --------------------------------------------------
        # Provider Status Verification
        # --------------------------------------------------
        st.divider()
        st.subheader("Provider Status Verification")

        provider_currently_practicing_response = st.radio(
            "Is the provider currently practicing information correct? *",
            CORRECT_INCORRECT,
            index=None,
            horizontal=True
        )

        provider_speciality_category_response = st.radio(
            "Is the specialty category correct? *",
            CORRECT_INCORRECT,
            index=None,
            horizontal=True
        )

        # --------------------------------------------------
        # Practice Location Verification
        # --------------------------------------------------
        st.divider()
        st.subheader("Practice Location Verification")

        phone_number_correct_response = st.radio(
            "Is the phone number correct? *",
            CORRECT_INCORRECT,
            index=None,
            horizontal=True
        )

        practice_location_name_response = st.radio(
            "Is the practice location name correct? *",
            CORRECT_INCORRECT,
            index=None,
            horizontal=True
        )

        practice_location_address_response = st.radio(
            "Is the practice location address correct? *",
            CORRECT_INCORRECT,
            index=None,
            horizontal=True
        )

        practice_location_suite_response = st.radio(
            "Is the practice location suite correct? *",
            CORRECT_INCORRECT,
            index=None,
            horizontal=True
        )

        # --------------------------------------------------
        # Patient Access Verification
        # --------------------------------------------------
        st.divider()
        st.subheader("Patient Access Verification")

        practice_accepting_new_patients_response = st.radio(
            "Is the accepting new patients information correct? *",
            CORRECT_INCORRECT,
            index=None,
            horizontal=True
        )

        practice_accepting_new_medicare_patients_response = st.radio(
            "Is the accepting Medicare patients information correct? *",
            CORRECT_INCORRECT,
            index=None,
            horizontal=True
        )

        # --------------------------------------------------
        # Enrichment / Corrections
        # --------------------------------------------------
        st.divider()
        st.subheader("Enrichment / Corrections")

        st.caption("Required fields capture confirmed or corrected values. Optional fields are for corrections only.")

        enriched_provider_currently_practicing_value = st.text_input(
            "Provider currently practicing value *"
        )

        enriched_provider_speciality_category_value = st.text_input(
            "Specialty category value *"
        )

        enriched_phone_number_value = st.text_input("Corrected phone number")

        enriched_practice_location_name_value = st.text_input("Corrected practice location name")

        enriched_practice_street_line_1_value = st.text_input("Corrected street line 1")

        enriched_practice_Street_line_2_suite_value = st.text_input("Corrected street line 2 / suite")

        enriched_practice_city_value = st.text_input("Corrected city")

        enriched_practice_zip_value = st.text_input("Corrected ZIP code")

        enriched_practice_state_value = st.selectbox(
            "Corrected state",
            STATE_CODES,
            index=None,
            placeholder="Select state..."
        )

        submitted = st.form_submit_button("Submit Survey", type="primary")

    if submitted:
        submission_time = now_text()
        total_minutes = round((time.time() - st.session_state.form_start_epoch) / 60)

        if is_already_verified(campaign_id.strip(), caqh_id.strip()):
            st.error("This record has already been verified and cannot be resubmitted.")
            return

        row = {
            "caller_id":                                    st.session_state.caller_id,
            "campaign_id":                                  campaign_id.strip(),
            "can_proceed_with_call":                        can_proceed_with_call or "",
            "form_start_time":                              st.session_state.form_start_time,
            "form_submission_time":                         submission_time,
            "form_total_time_minutes":                      total_minutes,
            "attempt_date_1":                               "",
            "attempt_date_2":                               "",
            "attempt_date_3":                               "",
            "verification_complete":                        verification_complete,
            "caqh_id":                                      caqh_id.strip(),
            "provider_currently_practicing_response":       correct_incorrect_to_bool(provider_currently_practicing_response),
            "provider_speciality_category_response":        correct_incorrect_to_bool(provider_speciality_category_response),
            "phone_number_correct_response":                correct_incorrect_to_bool(phone_number_correct_response),
            "practice_location_name_response":              correct_incorrect_to_bool(practice_location_name_response),
            "practice_location_address_response":           correct_incorrect_to_bool(practice_location_address_response),
            "practice_location_suite_response":             correct_incorrect_to_bool(practice_location_suite_response),
            "practice_accepting_new_patients_response":     correct_incorrect_to_bool(practice_accepting_new_patients_response),
            "practice_accepting_new_medicare_patients_response": correct_incorrect_to_bool(practice_accepting_new_medicare_patients_response),
            "enriched_provider_currently_practicing_value": enriched_provider_currently_practicing_value.strip(),
            "enriched_provider_speciality_category_value":  enriched_provider_speciality_category_value.strip(),
            "enriched_phone_number_value":                  enriched_phone_number_value.strip(),
            "enriched_practice_location_name_value":        enriched_practice_location_name_value.strip(),
            "enriched_practice_street_line_1_value":        enriched_practice_street_line_1_value.strip(),
            "enriched_practice_Street_line_2_suite_value":  enriched_practice_Street_line_2_suite_value.strip(),
            "enriched_practice_city_value":                 enriched_practice_city_value.strip(),
            "enriched_practice_zip_value":                  enriched_practice_zip_value.strip(),
            "enriched_practice_state_value":                enriched_practice_state_value or "",
        }

        errors = validate_required_fields(row)

        if errors:
            st.error("Please fix the following before submitting:")
            for error in errors:
                st.write(f"- {error}")
            return

        row = upsert_response(row)

        st.session_state.caller_report_csv = make_caller_report(row)

        st.session_state.form_started = False
        st.session_state.form_start_time = None
        st.session_state.form_start_epoch = None
        st.session_state.form_version += 1

        st.rerun()


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
