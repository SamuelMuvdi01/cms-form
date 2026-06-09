import streamlit as st

st.set_page_config(page_title="Survey Form", page_icon="📝", layout="centered")


# ----------------------------
# SESSION STATE INIT
# ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_id" not in st.session_state:
    st.session_state.user_id = None

# simple in-memory user store (temporary)
if "users" not in st.session_state:
    st.session_state.users = {
        "admin": "admin123"   # demo user
    }


# ----------------------------
# LOGOUT FUNCTION
# ----------------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.rerun()


# ----------------------------
# LOGIN PAGE
# ----------------------------
def login_page():
    st.title("🔐 Login")

    st.write("Enter your credentials to access the survey")

    user_id = st.text_input("User ID")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login"):
            if user_id in st.session_state.users and st.session_state.users[user_id] == password:
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.rerun()
            else:
                st.error("Invalid username or password")

    with col2:
        st.info("Demo user: admin / admin123")


# ----------------------------
# SURVEY PAGE (your form)
# ----------------------------
def survey_page():

    st.title("📝 Questionnaire / Survey Form")
    st.write(f"Logged in as: **{st.session_state.user_id}**")

    if st.button("Logout"):
        logout()

    with st.form(key="survey_form"):
        st.header("Section 1: Basic responses")

        q1 = st.radio(
            "1. Do you agree with the service quality?",
            options=["Yes", "No", "N/A"],
            index=2,
        )
        q2 = st.radio(
            "2. Was the information easy to understand?",
            options=["Yes", "No", "N/A"],
            index=2,
        )

        st.header("Section 2: Choice selections")

        q3 = st.selectbox(
            "3. Which of these best describes your experience?",
            options=[
                "Select an option...",
                "Excellent",
                "Good",
                "Fair",
                "Poor",
            ],
        )

        q4 = st.selectbox(
            "4. What is your preferred contact method?",
            options=[
                "Select an option...",
                "Email",
                "Phone",
                "Text message",
                "No preference",
            ],
        )

        st.header("Section 3: Free-form feedback")

        q5 = st.text_input("5. Please share any additional comments:")
        q6 = st.text_area("6. If you have suggestions for improvement, write them here:")

        submit_button = st.form_submit_button(label="Submit survey")

    if submit_button:
        st.success("Thank you for submitting the survey!")
        st.markdown("**Your responses:**")
        st.write({
            "User": st.session_state.user_id,
            "Service quality agreement": q1,
            "Information clarity": q2,
            "Experience rating": q3,
            "Preferred contact method": q4,
            "Additional comments": q5,
            "Improvement suggestions": q6,
        })


# ----------------------------
# ROUTER (HOME vs SURVEY)
# ----------------------------
if not st.session_state.logged_in:
    login_page()
else:
    survey_page()