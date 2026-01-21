import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Cadence Corrected", page_icon="✅", layout="wide")
st.title("✅ Cadence : Extraction & Comparaison (Code Corrigé)")

# --- STATE ---
if 'df_1h' not in st.session_state: st.session_state['df_1h'] = None
if 'df_15m' not in st.session_state: st.session_state['df_15m'] = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Authentification")
    api_key = st.text_input("Clé API", type="password")
    
    st.divider()
    
    st.header("2. Mode Manuel")
    # On reprend les valeurs de ton JSON pour tester direct
    project_id = st.number_input("ID Projet", value=689, step=1)
    mps_input = st.text_input("IDs Points", value="1797", help="Ex: 1797, 1798")
    
    st.divider()
    
    st.header("3. Configuration")
    use_1h = st.checkbox("1h (LAeq + Max)", value=True)
    use_15m = st.checkbox("15min (LAeq)", value=True)
    
    d_start = st.date_input("Début", date(2025, 1, 21))
    d_end = st.date_input("Fin", date.today())
    
    st.divider()
    btn_run = st.button("🚀 Lancer l'analyse", type="primary")

# --- FONCTION DE TRAITEMENT ROBUSTE ---
def get_cadence_data(api_key, proj_id, mp_ids, start, end, agg_time, suffix):
    
    # 1. Payload AppScript Strict
    indicators = []
    for mp in mp_ids:
        # LAeq
