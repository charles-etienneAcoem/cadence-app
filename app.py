import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Cadence Expert Extractor", page_icon="📡", layout="wide")

st.title("📡 Cadence Expert Data")
st.markdown("### Projet #1931 - Dashboard #1783")

# --- FONCTION POUR RECUPERER LES NOMS DES POINTS ---
@st.cache_data(ttl=3600) # Cache pour ne pas requêter à chaque clic
def get_project_mps(api_key, proj_id):
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{proj_id}"
    headers = {"accept": "application/json", "X-API-KEY": api_key}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            proj_data = response.json()
            # On extrait les points de mesure (ID et Nom)
            mps = {}
            if 'measurementPoints' in proj_data:
                for mp in proj_data['measurementPoints']:
                    # On stocke {ID: "Nom (ID)"}
                    mps[mp['id']] = f"{mp['name']} ({mp['id']})"
            return mps
        return {}
    except:
        return {}

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("🔐 Authentification")
    api_key = st.text_input("Clé API (Cadence Key)", type="password", value="")
    
    st.header("⚙️ Projet")
    project_id = st.number_input("ID Projet", value=1931, step=1)
    
    # CHARGEMENT DES POINTS DE MESURE
    mp_options = {}
    selected_mps = []
    
    if api_key:
        with st.spinner("Chargement des points..."):
            mp_options = get_project_mps(api_key, project_id)
            
        if mp_options:
            st.success(f"{len(mp_options)} points trouvés")
            # Multiselect avec les vrais noms
            selected_mp_names = st.multiselect(
                "Choisir les points :", 
                options=list(mp_options.values()),
                default=list(mp_options.values()) # Tout sélectionner par défaut
            )
            # Retrouver les IDs à partir des noms sélectionnés
            selected_mps = [id for id, name in mp_options.items() if name in selected_mp_names]
        else:
            st.warning("Impossible de récupérer les noms (Vérifiez la clé/ID Projet)")
            # Fallback manuel si l'API info échoue
            manual_mps = st.text_input("IDs manuels (secours)", "3440, 3441")
            if manual_mps:
                selected_
