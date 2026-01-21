import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import json

# --- CONFIGURATION (Doit être la 1ère ligne) ---
st.set_page_config(page_title="Cadence Debugger", page_icon="🐞", layout="wide")
st.title("🐞 Cadence : Mode DEBUG")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Paramètres")
    # Case à cocher pour tout afficher
    debug_mode = st.checkbox("🛠️ ACTIVER LE MODE DEBUG", value=True)
    
    api_key = st.text_input("Clé API", type="password")
    
    st.divider()
    st.header("2. Cibles")
    project_id = st.number_input("ID Projet", value=1931, step=1)
    mps_input = st.text_input("IDs Points (séparés par virgule)", value="3440, 3441")
    
    st.divider()
    st.header("3. Dates")
    d_start = st.date_input("Début", date(2025, 1, 21))
    d_end = st.date_input("Fin", date.today())
    
    btn_run = st.button("🚀 LANCER LA REQUÊTE", type="primary")

# --- FONCTION PRINCIPALE ---
if btn_run:
    if not api_key:
        st.error("⚠️ Il manque la Clé API.")
        st.stop()
        
    # Nettoyage des IDs
    try:
        mp_ids = [int(x.strip()) for x in mps_input.split(",") if x.strip()]
    except:
        st.error("Erreur de format dans les IDs des points.")
        st.stop()

    # Configuration de base
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{project_id}/data"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-API-KEY": api_key
    }
    
    start_iso = f"{d_start}T00:00:00Z"
    end_iso = f"{d_end}T23:59:59Z"

    # --- CONSTRUCTION DU PAYLOAD (INDICATEURS) ---
    # On teste une requête simple pour commencer : LAeq 1h
    # C'est souvent là que ça bloque
    
    indicators_list = []
    for mp in mp_ids:
        indicators_list.append({
            "measurementPointId": mp,
            "primaryData": "LAeq",
            "timeFrequency": "global",
            "frequencyBand": None,      # On tente le None (null) explicite
            "aggregationMethod": "average",
            "axis": None,               # On tente le None (null) explicite
            "precision": 1
        })

    payload = {
        "start": start_iso,
        "end": end_iso,
        "aggregationTime": 3600, # 1 heure
        "indicators": indicators_list
    }

    # --- AFFICHAGE DEBUG AVANT ENVOI ---
    if debug_mode:
        st.markdown("### 📤 1. Ce qu'on envoie (Payload)")
        st.code(json.dumps(payload, indent=4), language='json')
        st.info(f"URL ciblée : {url}")

    # --- ENVOI DE LA REQUÊTE ---
    with st.spinner("Communication avec le serveur..."):
        try:
            r = requests.post(url, headers=headers, json=payload)
            
            # --- AFFICHAGE DEBUG APRÈS RÉCEPTION ---
            if debug_mode:
                st.markdown(f"### 📥 2. Ce que Cadence répond (Status {r.status_code})")
                st.text(f"Status Code : {r.status_code}")
                st.text("Corps de la réponse brute :")
                st.code(r.text) # Affiche le texte brut même si ce n'est pas du JSON valide
            
            # --- ANALYSE ---
            if r.status_code == 200:
                st.success("✅ SUCCÈS : Connexion établie !")
                data = r.json()
                
                # Vérification du contenu
                if data.get('timestamp'):
                    nb_points = len(data['timestamp'])
                    st.write(f"Nombre de points temporels reçus : {nb_points}")
                    
                    # Création DataFrame rapide
                    df
