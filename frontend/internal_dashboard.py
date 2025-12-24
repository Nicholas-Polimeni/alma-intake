import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TOKEN = os.getenv("API_SECRET_TOKEN")

class Lead:
    def __init__(self, data):
        self.id = data.get("id")
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.email = data.get("email")
        self.state = data.get("state")
        self.resume_key = data.get("resume_s3_key")
        self.created_at = data.get("created_at")


def fetch_leads(state=None):
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    params = {}
    if state and state != "ALL":
        params["state"] = state
        
    try:
        resp = requests.get(f"{API_URL}/leads", headers=headers, params=params)
        if resp.status_code == 200:
            data = resp.json()
            return [Lead(item) for item in data.get("leads", [])]
        else:
            st.error(f"Failed to load leads: {resp.text}")
            return []
    except Exception as e:
        st.error(f"Connection error: {e}")
        return []

def update_lead_status(lead_id, new_state):
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    try:
        resp = requests.patch(
            f"{API_URL}/leads/{lead_id}/state", 
            headers=headers, 
            json={"state": new_state}
        )
        return resp.status_code == 200
    except:
        return False

st.set_page_config(page_title="Lead Submissions", page_icon="📋")

if not API_TOKEN:
    st.error("API_SECRET_TOKEN is missing from .env configuration.")
    st.stop()

st.title("Lead Submissions")
st.write("Internal view for reviewing and managing incoming leads.")

status_filter = st.selectbox(
    "Filter by status",
    options=["ALL", "PENDING", "REACHED_OUT"],
    index=0,
)

leads = fetch_leads(status_filter)

st.divider()

if not leads:
    st.info("No leads found matching criteria.")

for lead in leads:
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader(f"{lead.first_name} {lead.last_name}")
            st.write(f"📧 **Email:** {lead.email}")
            st.write(f"📄 **Resume Key:** `{lead.resume_key}`") # S3 Key
            st.write(f"📅 **Date:** {lead.created_at}")
            
            if lead.state == "PENDING":
                st.warning(f"Status: {lead.state}")
            else:
                st.success(f"Status: {lead.state}")

        with col2:
            if lead.state == "PENDING":
                # Use a callback to update state and rerun app immediately
                if st.button("Mark Reached Out", key=f"btn_{lead.id}"):
                    if update_lead_status(lead.id, "REACHED_OUT"):
                        st.success("Updated!")
                        st.rerun()
                    else:
                        st.error("Update failed")
            else:
                st.write("✅ Completed")