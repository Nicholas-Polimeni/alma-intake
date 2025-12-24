import streamlit as st
import requests
import os
from dotenv import load_dotenv

# Load environment variables for the API URL
load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

# 1. Initialize authentication state
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "api_token" not in st.session_state:
    st.session_state["api_token"] = None

def login_screen():
    """Renders a simple login form."""
    st.title("🔒 Admin Access")
    # Use type="password" to hide the token characters
    token_input = st.text_input("Enter API Secret Token", type="password")
    
    if st.button("Login"):
        if token_input:
            # Store the token in session state to use for API headers
            st.session_state["api_token"] = token_input
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Token is required.")

# 2. Check Authentication
if not st.session_state["authenticated"]:
    login_screen()
    st.stop()  # Stop execution here so the dashboard doesn't render

# --- Main Dashboard UI (Only visible after login) ---

st.set_page_config(page_title="Lead Submissions", page_icon="📋")

# Add a logout option in the sidebar
if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.session_state["api_token"] = None
    st.rerun()

st.title("Lead Submissions")
st.write("Internal view for reviewing and managing incoming leads.")

# 3. Helper to fetch leads using the session token
def fetch_leads(state_filter):
    headers = {"Authorization": f"Bearer {st.session_state['api_token']}"}
    params = {"state": state_filter} if state_filter != "ALL" else {}
    
    try:
        resp = requests.get(f"{API_URL}/leads", headers=headers, params=params)
        if resp.status_code == 200:
            return resp.json().get("leads", [])
        elif resp.status_code == 401:
            st.error("Invalid Token. Please logout and try again.")
            return []
        else:
            st.error(f"Error {resp.status_code}: {resp.text}")
            return []
    except Exception as e:
        st.error(f"Connection error: {e}")
        return []

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
            # Note: Lead fields match the 'Lead' pydantic model
            st.subheader(f"{lead['first_name']} {lead['last_name']}")
            st.write(f"📧 **Email:** {lead['email']}")
            resume_link = f"🔗 [View/Download Resume]({lead['resume_url']})"
            st.write(f"📄 **Resume:** {resume_link}")
            st.write(f"🔖 **Status:** `{lead['state']}`")

        with col2:
            if lead['state'] == "PENDING":
                if st.button("Mark Reached Out", key=f"btn_{lead['id']}", type="primary"):
                    # Call the patch endpoint with the token
                    headers = {"Authorization": f"Bearer {st.session_state['api_token']}"}
                    patch_resp = requests.patch(
                        f"{API_URL}/leads/{lead['id']}/state",
                        headers=headers,
                        json={"state": "REACHED_OUT"}
                    )
                    if patch_resp.status_code == 200:
                        st.success("Updated!")
                        st.rerun()
                    else:
                        st.error("Update failed.")
            else:
                st.write("✅ Completed")
