import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# --- CONFIGURATION ---
st.set_page_config(page_title="Cadence Viewer Final", page_icon="✅", layout="wide")
st.title("✅ Cadence : Visualiseur de Données")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔐 Authentification")
    api_key = st.text_input("Clé API", type="password")
    
    st.divider()
    st.header("🎯 Cibles")
    # J'ai mis par défaut les IDs trouvés dans ton JSON (Projet 689, Point 1797)
    project_id = st.number_input("ID Projet", value=689, step=1) 
    mps_input = st.text_input("IDs Points", value="1797", help="Pour plusieurs points : 1797, 1798")
    
    st.divider()
    st.header("📅 Période & Données")
    
    col1, col2 = st.columns(2)
    with col1:
        use_1h = st.checkbox("1h (Hourly)", True)
    with col2:
        use_15m = st.checkbox("15min", False)
        
    d_start = st.date_input("Début", date(2025, 1, 21)) # Date de ton JSON
    d_end = st.date_input("Fin", date.today())
    
    btn_run = st.button("🚀 AFFICHER LES DONNÉES", type="primary")

# --- FONCTION DE TRAITEMENT ---
def process_cadence_response(json_data, suffix):
    """Transforme le JSON complexe de Cadence en DataFrame simple"""
    try:
        if not json_data.get('timeStamp'):
            return None
        
        # 1. Les Dates
        df = pd.DataFrame({'Date': pd.to_datetime(json_data['timeStamp'])})
        
        # 2. Les Indicateurs
        if 'indicators' in json_data:
            for item in json_data['indicators']:
                # Nom du point
                mp_info = item.get('measurementPoint', {})
                mp_name = mp_info.get('measurementPointName', str(item.get('measurementPointId')))
                data_type = item.get('indicatorDescription', {}).get('primaryData', 'Value')
                
                # Nom de la colonne
                col_name = f"{mp_name} | {data_type} ({suffix})"
                
                # Extraction des valeurs (Gestion du [[...]] vs [...])
                raw_values = item.get('data', {}).get('values')
                
                if raw_values:
                    # Si c'est une liste de liste [[v1, v2]], on prend la première
                    if isinstance(raw_values, list) and len(raw_values) > 0 and isinstance(raw_values[0], list):
                        clean_values = raw_values[0]
                    else:
                        clean_values = raw_values
                    
                    # Vérification taille
                    if len(clean_values) == len(df):
                        df[col_name] = clean_values
                    else:
                        st.warning(f"Attention : Décalage de taille pour {col_name}")
        
        df.set_index('Date', inplace=True)
        return df
    except Exception as e:
        st.error(f"Erreur de lecture du JSON : {e}")
        return None

# --- MAIN ---
if btn_run:
    if not api_key:
        st.error("Il manque la clé API.")
        st.stop()
        
    # Nettoyage IDs
    try:
        mp_ids = [int(x.strip()) for x in mps_input.split(",") if x.strip()]
    except:
        st.error("Format des IDs incorrect.")
        st.stop()

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-API-KEY": api_key
    }
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{project_id}/data"
    
    start_iso = f"{d_start}T00:00:00Z"
    end_iso = f"{d_end}T23:59:59Z"
    
    dfs = []

    # --- REQUÊTE 1H ---
    if use_1h:
        indicators_1h = []
        for mp in mp_ids:
            # Construction stricte comme AppScript
            indicators_1h.append({
                "measurementPointId": mp,
                "primaryData": "LAeq",
                "timeFrequency": "global",
                "frequencyBand": None,
                "aggregationMethod": "average",
                "axis": None,
                "precision": 1
            })
            
        payload_1h = {
            "start": start_iso, "end": end_iso, "aggregationTime": 3600,
            "indicators": indicators_1h
        }
        
        with st.spinner("Chargement données 1h..."):
            try:
                r = requests.post(url, headers=headers, json=payload_1h)
                if r.status_code == 200:
                    df_1h = process_cadence_response(r.json(), "1h")
                    if df_1h is not None: dfs.append(df_1h)
                else:
                    st.error(f"Erreur 1h : {r.status_code}")
            except Exception as e:
                st.error(str(e))

    # --- REQUÊTE 15 MIN ---
    if use_15m:
        indicators_15 = []
        for mp in mp_ids:
            indicators_15.append({
                "measurementPointId": mp,
                "primaryData": "LAeq",
                "timeFrequency": "global",
                "frequencyBand": None,
                "aggregationMethod": "average",
                "axis": None,
                "precision": 1
            })
            
        payload_15 = {
            "start": start_iso, "end": end_iso, "aggregationTime": 900,
            "indicators": indicators_15
        }
        
        with st.spinner("Chargement données 15min..."):
            try:
                r2 = requests.post(url, headers=headers, json=payload_15)
                if r2.status_code == 200:
                    df_15 = process_cadence_response(r2.json(), "15m")
                    if df_15 is not None: dfs.append(df_15)
                else:
                    st.error(f"Erreur 15m : {r2.status_code}")
            except Exception as e:
                st.error(str(e))

    # --- AFFICHAGE FINAL ---
    if dfs:
        # Fusion
        final_df = dfs[0]
        for d in dfs[1:]:
            final_df = final_df.join(d, how='outer')
        
        final_df.reset_index(inplace=True)
        final_df.sort_values('Date', inplace=True)
        
        # Info Projet (Basé sur le JSON reçu)
        st.success(f"Données récupérées pour {len(final_df)} points temporels.")
        
        # 1. Graphique
        st.markdown("### 📈 Courbes de niveaux")
        fig = px.line(final_df, x='Date', y=final_df.columns[1:], height=600)
        # Amélioration visuelle
        fig.update_layout(
            hovermode="x unified", 
            legend=dict(orientation="h", y=1.1, title="Capteurs"),
            yaxis_title="Niveau (dB)"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 2. Tableau & Export
        st.divider()
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown("### 📋 Tableau de données")
            st.dataframe(final_df, use_container_width=True, height=400)
        with c2:
            st.markdown("### 📥 Télécharger")
            csv = final_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Télécharger CSV",
                data=csv,
                file_name=f"Cadence_Export_{project_id}.csv",
                mime="text/csv",
                type="primary"
            )
            
    else:
        st.warning("Aucune donnée n'a pu être affichée.")
