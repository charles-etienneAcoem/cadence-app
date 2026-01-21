import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go # Plus puissant que px pour la superposition
from datetime import datetime, date

# --- CONFIGURATION ---
st.set_page_config(page_title="Cadence Pro Dashboard", page_icon="🚀", layout="wide")
st.title("🚀 Cadence : Dashboard Expert")

# --- INITIALISATION SESSION STATE ---
if 'projects_map' not in st.session_state: st.session_state['projects_map'] = {}
if 'points_map' not in st.session_state: st.session_state['points_map'] = {}
if 'df_1h' not in st.session_state: st.session_state['df_1h'] = None
if 'df_15m' not in st.session_state: st.session_state['df_15m'] = None

# --- SIDEBAR : NAVIGATION ---
with st.sidebar:
    st.header("1. Connexion")
    api_key = st.text_input("Clé API", type="password")
    
    # --- ETAPE 1 : LISTER LES PROJETS ---
    if st.button("🔄 Visualiser mes projets", type="primary"):
        if not api_key:
            st.error("Clé API manquante")
        else:
            with st.spinner("Recherche des projets..."):
                try:
                    # On demande une grande page pour tout avoir d'un coup
                    url = "https://cadence.acoem.com/cloud-api/v1/projects?page=0&size=200&sort=name,asc"
                    headers = {"accept": "application/json", "X-API-KEY": api_key}
                    r = requests.get(url, headers=headers, timeout=10)
                    
                    if r.status_code == 200:
                        data = r.json()
                        raw_list = []
                        
                        # Gestion robuste du format (List vs Content)
                        if isinstance(data, list): raw_list = data
                        elif isinstance(data, dict) and 'content' in data: raw_list = data['content']
                        
                        if raw_list:
                            # Création du map { "Nom (ID)" : ID }
                            mapping = {f"{p.get('name', 'Sans Nom')} ({p.get('id')})": p.get('id') for p in raw_list}
                            st.session_state['projects_map'] = mapping
                            st.success(f"✅ {len(mapping)} projets chargés.")
                            # Reset des points si on change de projets
                            st.session_state['points_map'] = {} 
                        else:
                            st.warning("Aucun projet trouvé.")
                    else:
                        st.error(f"Erreur API Projets : {r.status_code}")
                except Exception as e:
                    st.error(f"Erreur connexion : {e}")

    # --- ETAPE 2 : CHOIX DU PROJET ---
    selected_proj_id = None
    if st.session_state['projects_map']:
        st.divider()
        st.header("2. Sélection Projet")
        
        proj_name = st.selectbox("Choisir le projet :", list(st.session_state['projects_map'].keys()))
        selected_proj_id = st.session_state['projects_map'][proj_name]
        
        # Dès qu'un projet est choisi, on cherche ses points (Automatique ou Bouton)
