import streamlit as st

st.set_page_config(page_title="Survey Form", page_icon="📝", layout="centered")

st.title("📝 Questionnaire / Survey Form")
st.write(
    "Fill out the questions below. Use the radio buttons for yes/no/null responses, dropdowns for predefined choices, and free-form text fields where indicated."
)

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
        "Service quality agreement": q1,
        "Information clarity": q2,
        "Experience rating": q3,
        "Preferred contact method": q4,
        "Additional comments": q5,
        "Improvement suggestions": q6,
    })
