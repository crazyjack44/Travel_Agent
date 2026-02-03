import streamlit as st
import time
import pandas as pd
from datetime import datetime, timedelta
import base64
from utils import generate_plan, checking_task_status, load_local_history, save_api_config

# Set page configuration
st.set_page_config(
    page_title="Intelligent Travel Agent",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    with open("web_app/styles.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Initialize session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Home"
if 'generated_plan' not in st.session_state:
    st.session_state.generated_plan = None
if 'task_id' not in st.session_state:
    st.session_state.task_id = None
if 'is_generating' not in st.session_state:
    st.session_state.is_generating = False

# Sidebar Navigation
with st.sidebar:
    st.title("✈️ Travel Agent")
    
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.current_page = "Home"
        st.rerun()
        
    if st.button("📜 History", use_container_width=True):
        st.session_state.current_page = "History"
        st.rerun()
        
    if st.button("⚙️ Settings", use_container_width=True):
        st.session_state.current_page = "Settings"
        st.rerun()
    
    st.divider()
    st.caption("Powered by Streamlit")

# --- Page: Home ---
def render_home():
    st.title("Plan Your Next Adventure")
    
    # Input Form
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            destination = st.text_input("Destination", placeholder="e.g., Tokyo, Japan")
            origin = st.text_input("Origin", placeholder="e.g., New York, USA")
            budget = st.selectbox("Budget Level", ["Budget", "Moderate", "Luxury"], index=1)
            
        with col2:
            start_date = st.date_input("Start Date", min_value=datetime.today())
            days = st.slider("Duration (Days)", min_value=1, max_value=14, value=3)
            preferences_str = st.text_input("Travel Style / Preferences", placeholder="e.g., Food, Culture, Nature")
    
    # Generate Button
    if st.button("Generate Itinerary 🚀"):
        if not destination or not origin:
            st.error("Please fill in both Destination and Origin.")
        else:
            st.session_state.is_generating = True
            st.session_state.generated_plan = None
            st.session_state.task_id = None
            
            # Prepare payload
            preferences = [p.strip() for p in preferences_str.split(',')] if preferences_str else []
            payload = {
                "destination": destination,
                "origin": origin,
                "days": days,
                "budget_level": budget,
                "preferences": preferences,
                "start_date": start_date.strftime("%Y-%m-%d")
            }
            
            # Call API
            with st.spinner("Submitting request..."):
                result = generate_plan(payload)
                if "task_id" in result:
                    st.session_state.task_id = result["task_id"]
                else:
                    st.error(f"Failed to submit task: {result.get('error')}")
                    st.session_state.is_generating = False
            
            st.rerun()

    # Polling & Display Results
    if st.session_state.is_generating and st.session_state.task_id:
        with st.empty():
            st.info("Generating your personalized itinerary... This may take a minute.")
            
            # Polling loop
            while True:
                status_data = checking_task_status(st.session_state.task_id)
                status = status_data.get("status")
                
                if status == "completed":
                    st.session_state.generated_plan = status_data
                    st.session_state.is_generating = False
                    st.success("Plan generated successfully!")
                    st.rerun()
                    break
                elif status == "failed":
                    st.session_state.is_generating = False
                    st.error(f"Generation failed: {status_data.get('error')}")
                    break
                
                time.sleep(2) # Poll every 2 seconds

    # Display Result
    if st.session_state.generated_plan:
        plan = st.session_state.generated_plan.get("result", {})
        posters = st.session_state.generated_plan.get("posters", [])
        
        st.divider()
        st.header(f"Trip to {destination}")
        
        # Summary
        if "summary" in plan:
            st.markdown(f"<div class='card'>{plan['summary']}</div>", unsafe_allow_html=True)
        
        # Daily Plans
        if "daily_plans" in plan:
            for day in plan["daily_plans"]:
                with st.expander(f"Day {day['day']}: {day.get('theme', '')}", expanded=True):
                    st.write(day.get('schedule', ''))
                    
        # Posters Carousel (simulated with scroll)
        if posters:
            st.subheader("Daily Posters")
            cols = st.columns(len(posters))
            for idx, poster in enumerate(posters):
                if idx < len(cols):
                    with cols[idx]:
                        # Handle base64 image
                        image_data = poster.get("image_base64")
                        if image_data:
                            st.image(base64.b64decode(image_data), caption=f"Day {poster.get('day')}", use_column_width=True)

# --- Page: History ---
def render_history():
    st.title("Checking your Travel History")
    
    # Refresh button
    if st.button("Refresh History"):
        st.rerun()
    
    # Load history
    history_items = load_local_history("backbond_python") # Accessing parent dir's file
    
    if not history_items:
        st.info("No history found.")
        return
        
    for item in history_items:
        data = item["data"]
        # Try to extract destination from result
        # The structure of result.json varies, we need to adapt
        # Typically: result -> destination info or derived from filename
        
        # Display logic needs to be robust
        with st.expander(f"Plan created at {datetime.fromtimestamp(item['created_at']).strftime('%Y-%m-%d %H:%M')}", expanded=False):
            if "summary" in data:
               st.write(data["summary"])
            elif "daily_plans" in data:
               st.write(f"Itinerary with {len(data['daily_plans'])} days.")
            else:
               st.json(data)
               
            # Option to load this as the "active" plan on home page could be added here
            
# --- Page: Settings ---
def render_settings():
    st.title("Settings")
    
    st.subheader("API Configuration")
    search_api_key = st.text_input("Bing Search API Key", type="password")
    llm_api_key = st.text_input("LLM API Key", type="password")
    llm_name = st.text_input("Model Name", type="text")
    if st.button("Save Configuration"):
        if save_api_config(search_api_key, llm_api_key, llm_name):
            st.success("Configuration saved!")

# Main Router
if st.session_state.current_page == "Home":
    render_home()
elif st.session_state.current_page == "History":
    render_history()
elif st.session_state.current_page == "Settings":
    render_settings()
