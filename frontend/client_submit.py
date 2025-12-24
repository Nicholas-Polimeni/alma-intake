import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Submit Your Resume", page_icon="📄")
st.title("Candidate Application")
st.write("Please fill out the form below and upload your resume.")

with st.form("lead_form"):
    first_name = st.text_input("First Name", max_chars=50)
    last_name = st.text_input("Last Name", max_chars=50)
    email = st.text_input("Email")
    resume = st.file_uploader(
        "Resume / CV",
        type=["pdf", "doc", "docx"]
    )

    submitted = st.form_submit_button("Submit")

if submitted:
    if not first_name or not last_name or not email or not resume:
        st.error("All fields are required.")
    else:
        with st.spinner("Submitting application..."):
            try:
                files = {
                    "resume": (resume.name, resume.getvalue(), resume.type)
                }
                data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email
                }
                
                response = requests.post(f"{API_URL}/leads", data=data, files=files)

                if response.status_code == 200:
                    st.success("Application submitted successfully! Check your email for confirmation.")
                    st.balloons()
                else:
                    st.error(f"Error submitting form: {response.text}")
            
            except Exception as e:
                st.error(f"Connection failed: {e}")