import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import json

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Cadence Manual Extractor", page_icon="⚡", layout="wide")
st.title("⚡ Cadence : Extraction Rapide (Mode Manuel)")
st.markdown("Saisie directe des IDs pour contourner les erreurs de listing.")

# --- BARRE LATÉRALE : PARAMÈTRES ---
with st.sidebar:
    st.header("1. Authentification")
    api_key = st.text_input("Clé API", type="password", help="Votre clé commençant par EZfX...")
    
    st.divider()
    
    st.header("2. Cibles (Manuel)")
    # Saisie manuelle directe comme demandé
    project_id = st.number_input("ID du Projet", value=1931, step=1, help="Ex: 1931")
    
    mps_input = st.text_input("IDs des Points de mesure", value="3440, 3441", help="Séparez les IDs par une virgule")
    
    st.divider()
    
    st.header("3. Configuration")
    
    st.caption("Données horaires (1h) :")
    c1, c2, c3 = st.columns(3)
    with c1: use_1h_leq = st.checkbox("LAeq", True, key="h1")
    with c2: use_1h_max = st.checkbox("Max", True, key="h2")
    with c3: use_1h_min = st.checkbox("Min", False, key="h3")
    
    st.caption("Données courtes (15min) :")
    use_15m_leq = st.checkbox("LAeq (15m)", True, key="m1")
    
    st.caption("Période :")
    d_start = st.date_input("Début", date(2025, 1, 21))
    d_end = st.date_input("Fin", date.today())
    
    st.divider()
    
    btn_run = st.button("🚀 RÉCUPÉRER LES DONNÉES", type="primary")

# --- LOGIQUE PRINCIPALE ---
if btn_run:
    # 1. Validation des entrées
    if not api_key:
        st.error("⚠️ Clé API manquante.")
        st.stop()
    
    # Parsing des IDs de points (ex: "3440, 3441" -> [3440, 3441])
    try:
        mp_ids = [int(x.strip()) for x in mps_input.split(",") if x.strip()]
    except:
        st.error("⚠️ Erreur de format dans les IDs des points. Utilisez uniquement des chiffres et des virgules.")
        st.stop()

    if not mp_ids:
        st.error("⚠️ Aucun ID de point renseigné.")
        st.stop()

    # 2. Préparation
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-API-KEY": api_key
    }
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{project_id}/data"
    
    # Dates ISO 8601
    start_iso = f"{d_start}T00:00:00Z"
    end_iso = f"{d_end}T23:59:59Z"
    
    dfs_result = []
    
    # --- FONCTION DE CONSTRUCTION INDICATEUR (STYLE APPSCRIPT) ---
    def make_indicator(mp_id, primary_data, agg_method):
        # C'est ici qu'on respecte strictement ton format AppScript
        return {
            "measurementPointId": mp_id,
            "primaryData": primary_data,
            "timeFrequency": "global",
            "frequencyBand": None,      # Essentiel (null en JSON)
            "aggregationMethod": agg_method,
            "axis": None,               # Essentiel (null en JSON)
            "precision": 1
        }

    # --- REQUÊTE 1 : DONNÉES HORAIRES (3600s) ---
    inds_1h = []
    if use_1h_leq: 
        for mp in mp_ids: inds_1h.append(make_indicator(mp, "LAeq", "average"))
    if use_1h_max: 
        for mp in mp_ids: inds_1h.append(make_indicator(mp, "LAFMax", "max"))
    if use_1h_min: 
        for mp in mp_ids: inds_1h.append(make_indicator(mp, "LAFMin", "min"))
        
    if inds_1h:
        payload_1h = {
            "start": start_iso, "end": end_iso,
            "aggregationTime": 3600,
            "indicators": inds_1h
        }
        
        with st.spinner("Téléchargement des données 1h..."):
            try:
                r = requests.post(url, headers=headers, json=payload_1h)
                if r.status_code == 200:
                    d = r.json()
                    if d.get('timestamp'):
                        df = pd.DataFrame({'Date': pd.to_datetime(d['timestamp'])})
                        for item in d['indicators']:
                            # Nommage simplifié : ID Point | Type Donnée
                            col = f"MP {item['measurementPointId']} | {item['primaryData']} (1h)"
                            if item.get('data') and item['data'].get('values'):
                                df[col] = item['data']['values']
                        df.set_index('Date', inplace=True)
                        dfs_result.append(df)
                else:
                    st.error(f"Erreur 1h ({r.status_code})")
                    # Affichage Debug si erreur
                    with st.expander("Voir le payload envoyé (Debug)"):
                        st.json(payload_1h)
                    with st.expander("Voir la réponse API"):
                        st.write(r.text)
            except Exception as e:
                st.error(f"Erreur technique 1h : {e}")

    # --- REQUÊTE 2 : DONNÉES 15 MINUTES (900s) ---
    if use_15m_leq:
        inds_15 = []
        for mp in mp_ids:
            inds_15.append(make_indicator(mp, "LAeq", "average"))
            
        payload_15 = {
            "start": start_iso, "end": end_iso,
            "aggregationTime": 900,
            "indicators": inds_15
        }
        
        with st.spinner("Téléchargement des données 15min..."):
            try:
                r = requests.post(url, headers=headers, json=payload_15)
                if r.status_code == 200:
                    d = r.json()
                    if d.get('timestamp'):
                        df = pd.DataFrame({'Date': pd.to_datetime(d['timestamp'])})
                        for item in d['indicators']:
                            col = f"MP {item['measurementPointId']} | {item['primaryData']} (15m)"
                            if item.get('data') and item['data'].get('values'):
                                df[col] = item['data']['values']
                        df.set_index('Date', inplace=True)
                        dfs_result.append(df)
                else:
                    st.error(f"Erreur 15m ({r.status_code})")
            except Exception as e:
                st.error(f"Erreur technique 15m : {e}")

    # --- FUSION ET RÉSULTAT ---
    if dfs_result:
        # Merge de tous les dataframes récupérés
        final_df = dfs_result[0]
        for df_part in dfs_result[1:]:
            final_df = final_df.join(df_part, how='outer')
        
        final_df.reset_index(inplace=True)
        final_df.sort_values('Date', inplace=True)
        
        st.success(f"✅ Terminé ! {len(final_df)} lignes récupérées.")
        
        # 1. Graphique Plotly
        st.markdown("### 📈 Visualisation")
        fig = px.line(final_df, x='Date', y=final_df.columns[1:], height=600)
        fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)
        
        # 2. Tableau et Export
        c1, c2 = st.columns([3, 1])
        with c1:
            st.dataframe(final_df, use_container_width=True, height=300)
        with c2:
            st.markdown("### 📥 Export")
            csv_data = final_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Télécharger en CSV",
                data=csv_data,
                file_name=f"Cadence_Export_{project_id}.csv",
                mime="text/csv",
                type="primary"
            )
    else:
        st.warning("Aucune donnée n'a été récupérée. Vérifiez les dates et les IDs.")
