import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, time, timedelta
import itertools
import re

# --- ASSETS ---
ACOEM_LOGO_NEW = "https://cdn.bfldr.com/Q3Z2TZY7/at/b4z3s28jpswp92h6z35h9f3/ACOEM-LOGO-WithoutBaseline-RGB-Bicolor.jpg?auto=webp&format=jpg"
ACOEM_COLORS = ['#ff6952', '#2c5078', '#96c8de', '#FFB000', '#50C878', '#808080', '#000000']

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Cadence Data", 
    page_icon=ACOEM_LOGO_NEW, 
    layout="wide"
)

# --- 2. CSS CUSTOMIZATION ---
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 1rem; }
        [data-testid="stSidebarUserContent"] { padding-top: 1rem; }
        
        .logo-container {
            background-color: white; padding: 12px; border-radius: 6px;
            display: flex; justify-content: center; align-items: center; margin-bottom: 20px;
        }
        
        .streamlit-expanderHeader {
            font-size: 1rem; font-weight: bold; color: #ff6952;
        }
        
        .project-detected {
            color: #50C878; font-size: 0.85rem; font-weight: bold; margin-top: -10px; margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'df_1h' not in st.session_state: st.session_state['df_1h'] = None
if 'df_15m' not in st.session_state: st.session_state['df_15m'] = None
if 'df_alerts' not in st.session_state: st.session_state['df_alerts'] = None

# --- HELPER: GET PROJECT NAME ---
@st.cache_data(ttl=3600)
def get_project_name(api_key, proj_id):
    if not api_key: return None
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{proj_id}"
    headers = {"accept": "application/json", "X-API-KEY": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=2)
        if r.status_code == 200:
            return r.json().get('name', None)
    except:
        pass
    return None

# --- SIDEBAR ---
with st.sidebar:
    # BRANDING ACOEM ONLY
    st.markdown(f"""
        <div class="logo-container">
            <img src="{ACOEM_LOGO_NEW}" style="width: 100%; max-width: 160px;">
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # --- 1. AUTH ---
    with st.expander("🔐 1. Authentication", expanded=True):
        api_key = st.text_input("API Key", type="password", help="Starts with EZfX...")

    # --- 2. TARGET ---
    with st.expander("🎯 2. Target", expanded=True):
        project_id = st.number_input("Project ID", value=689, step=1)
        dashboard_id = st.number_input("Dashboard ID (For Alerts)", value=1, step=1)
        
        # LOGIQUE NOM PROJET
        display_name = f"Project #{project_id}"
        if api_key:
            fetched_name = get_project_name(api_key, project_id)
            if fetched_name:
                display_name = fetched_name
                st.markdown(f"<div class='project-detected'>✅ {fetched_name}</div>", unsafe_allow_html=True)
        
        mps_input = st.text_input("Point IDs", value="1797, 1798", help="Ex: 1797, 1798")

    # --- 3. SETTINGS ---
    with st.expander("⚙️ 3. Settings", expanded=True):
        STD_INDICATORS = [
            {"label": "LAeq (Avg)", "code": "LAeq", "method": "average"},
            {"label": "LAFMax (Max)", "code": "LAFMax", "method": "max"},
            {"label": "LAFMin (Min)", "code": "LA
