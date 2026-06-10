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

YES_NO_NA = ["Yes", "No", "N/A"]

STATE_CODES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "AS", "GU", "MP", "PR", "VI"
]

EXPIRY_BUCKET_OPTIONS = [
    "0-6 months",
    "6 months to 1 year",
    "1 - 2 years",
    "2+ years"
]


# These are the final columns saved to the master CSV.
MASTER_COLUMNS = [
    "caller_id",
    "form_start_time",
    "form_submission_time",
    "form_total_time_seconds",

    "provider_currently_practicing_y_n",
    "provider_speciality_category",
    "office_phone_number",
    "practice_location_name",
    "practice_street_line_1",
    "practice_street_line_2_suite",
    "practice_state",
    "practice_accepting_new_patients",
    "practice_accepting_new_medicare_patients",
    "provider_npi",
    "provider_type",
    "poid",
    "po_name",
    "specialty_details",
    "last_confirmed_date",
    "confirmation_type",
    "last_attest_date",
    "expiry_bucket",
    "months_since_expiry",
    "practice_location_affiliation_status",
    "office_type",
    "appointment_bookable_with_provider",
    "list_accepted_plans",
]


# These are the columns downloaded by the caller.
# The hidden timing fields are excluded.
CALLER_REPORT_COLUMNS = [
    "caller_id",
    "form_submission_time",

    "provider_currently_practicing_y_n",
    "provider_speciality_category",
    "office_phone_number",
    "practice_location_name",
    "practice_street_line_1",
    "practice_street_line_2_suite",
    "practice_state",
    "practice_accepting_new_patients",
    "practice_accepting_new_medicare_patients",
    "provider_npi",
    "provider_type",
    "poid",
    "po_name",
    "specialty_details",
    "last_confirmed_date",
    "confirmation_type",
    "last_attest_date",
    "expiry_bucket",
    "months_since_expiry",
    "practice_location_affiliation_status",
    "office_type",
    "appointment_bookable_with_provider",
    "list_accepted_plans",
]


# Control required fields here.
# Remove a column from this list if you want that field to be optional.
REQUIRED_FIELDS = [
    "provider_currently_practicing_y_n",
    "provider_speciality_category",
    "office_phone_number",
    "practice_location_name",
    "practice_street_line_1",
    "practice_state",
    "practice_accepting_new_patients",
    "practice_accepting_new_medicare_patients",
    "provider_npi",
    "provider_type",
    "poid",
    "po_name",
    "last_confirmed_date",
    "confirmation_type",
    "last_attest_date",
    "expiry_bucket",
    "months_since_expiry",
    "practice_location_affiliation_status",
    "office_type",
    "appointment_bookable_with_provider",
    "list_accepted_plans",
]


# Friendly field names for validation messages.
FIELD_LABELS = {
    "provider_currently_practicing_y_n": "Is this provider currently practicing at this location?",
    "provider_speciality_category": "Provider specialty category",
    "office_phone_number": "Office phone number",
    "practice_location_name": "Practice location name",
    "practice_street_line_1": "Street line 1",
    "practice_street_line_2_suite": "Street line 2 or Suite",
    "practice_state": "State",
    "practice_accepting_new_patients": "Practice accepting new patients",
    "practice_accepting_new_medicare_patients": "Practice accepting Medicare patients",
    "provider_npi": "Provider NPI",
    "provider_type": "Provider type",
    "poid": "POID",
    "po_name": "PO Name",
    "specialty_details": "Specialty details",
    "last_confirmed_date": "Last confirmed date",
    "confirmation_type": "Confirmation type",
    "last_attest_date": "Last attest date",
    "expiry_bucket": "Expiry bucket",
    "months_since_expiry": "Months since expiry",
    "practice_location_affiliation_status": "Practice location affiliation status",
    "office_type": "Office type",
    "appointment_bookable_with_provider": "Can a patient schedule an appointment with this provider at this location?",
    "list_accepted_plans": "List all accepted plans",
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
            {"caller_id": "admin", "password": "admin123", "role": "admin"},
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

    # New form key = blank form.
    st.session_state.form_version += 1

    st.rerun()


def cancel_form():
    st.session_state.form_started = False
    st.session_state.form_start_time = None
    st.session_state.form_start_epoch = None

    # Clears old unsaved form values.
    st.session_state.form_version += 1

    st.rerun()


def validate_required_fields(row):
    errors = []

    for field in REQUIRED_FIELDS:
        value = row.get(field, "")

        if value is None or str(value).strip() == "":
            label = FIELD_LABELS.get(field, field)
            errors.append(f"{label} is required.")

    return errors


def save_to_master_csv(row):
    new_row = pd.DataFrame([row], columns=MASTER_COLUMNS)

    new_row.to_csv(
        MASTER_CSV,
        mode="a",
        header=False,
        index=False
    )


def make_caller_report(row):
    report_row = {
        column: row[column]
        for column in CALLER_REPORT_COLUMNS
    }

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
        st.subheader("Provider Status")

        provider_currently_practicing_y_n = st.radio(
            "Is this provider currently practicing at this location? *",
            YES_NO_NA,
            index=None
        )

        provider_speciality_category = st.text_input(
            "What is this provider's specialty category? *"
        )

        provider_npi = st.text_input("Provider NPI *")

        provider_type = st.text_input("Provider type *")

        poid = st.text_input("POID *")

        po_name = st.text_input("PO Name *")

        specialty_details = st.text_area("Any specialty details?")

        st.divider()
        st.subheader("Practice Location")

        office_phone_number = st.text_input("What is the office phone number? *")

        practice_location_name = st.text_input("What is the practice location name? *")

        practice_street_line_1 = st.text_input("Street line 1 *")

        practice_street_line_2_suite = st.text_input("Street line 2 or Suite")

        practice_state = st.selectbox(
            "State *",
            STATE_CODES,
            index=None,
            placeholder="Start typing a state code..."
        )

        practice_location_affiliation_status = st.text_input(
            "What is the affiliation status of the practice? *"
        )

        office_type = st.text_input("What is the office type? *")

        st.divider()
        st.subheader("Patient Access")

        practice_accepting_new_patients = st.radio(
            "Is the practice accepting new patients? *",
            YES_NO_NA,
            index=None
        )

        practice_accepting_new_medicare_patients = st.radio(
            "Is the practice accepting Medicare patients? *",
            YES_NO_NA,
            index=None
        )

        appointment_bookable_with_provider = st.radio(
            "Can a patient schedule an appointment with this provider at this location? *",
            YES_NO_NA,
            index=None
        )

        list_accepted_plans = st.text_area("List all accepted plans *")

        st.divider()
        st.subheader("Confirmation / Attestation")

        last_confirmed_date = st.date_input(
            "Last confirmed date? *",
            value=None,
            format="YYYY-MM-DD"
        )

        confirmation_type = st.text_input("Confirmation type? *")

        last_attest_date = st.date_input(
            "Last attest date? *",
            value=None,
            format="YYYY-MM-DD"
        )

        expiry_bucket = st.selectbox(
            "What is the expiry bucket? *",
            EXPIRY_BUCKET_OPTIONS,
            index=None,
            placeholder="Select expiry bucket..."
        )

        months_since_expiry = st.text_input("Months since expiry? *")

        submitted = st.form_submit_button("Submit Survey", type="primary")

    if submitted:
        submission_time = now_text()
        total_seconds = round(time.time() - st.session_state.form_start_epoch, 2)

        row = {
            "caller_id": st.session_state.caller_id,
            "form_start_time": st.session_state.form_start_time,
            "form_submission_time": submission_time,
            "form_total_time_seconds": total_seconds,

            "provider_currently_practicing_y_n": provider_currently_practicing_y_n or "",
            "provider_speciality_category": provider_speciality_category.strip(),
            "office_phone_number": office_phone_number.strip(),
            "practice_location_name": practice_location_name.strip(),
            "practice_street_line_1": practice_street_line_1.strip(),
            "practice_street_line_2_suite": practice_street_line_2_suite.strip(),
            "practice_state": practice_state or "",
            "practice_accepting_new_patients": practice_accepting_new_patients or "",
            "practice_accepting_new_medicare_patients": practice_accepting_new_medicare_patients or "",
            "provider_npi": provider_npi.strip(),
            "provider_type": provider_type.strip(),
            "poid": poid.strip(),
            "po_name": po_name.strip(),
            "specialty_details": specialty_details.strip(),
            "last_confirmed_date": date_to_text(last_confirmed_date),
            "confirmation_type": confirmation_type.strip(),
            "last_attest_date": date_to_text(last_attest_date),
            "expiry_bucket": expiry_bucket or "",
            "months_since_expiry": months_since_expiry.strip(),
            "practice_location_affiliation_status": practice_location_affiliation_status.strip(),
            "office_type": office_type.strip(),
            "appointment_bookable_with_provider": appointment_bookable_with_provider or "",
            "list_accepted_plans": list_accepted_plans.strip(),
        }

        errors = validate_required_fields(row)

        if errors:
            st.error("Please fix the following before submitting:")
            for error in errors:
                st.write(f"- {error}")
            return

        save_to_master_csv(row)

        st.session_state.caller_report_csv = make_caller_report(row)

        st.session_state.form_started = False
        st.session_state.form_start_time = None
        st.session_state.form_start_epoch = None

        # Forces the next form to open blank after successful submission.
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