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
        indicators.append({
            "measurementPointId": mp, "primaryData": "LAeq", "aggregationMethod": "average",
            "timeFrequency": "global", "frequencyBand": None, "axis": None, "precision": 1
        })
        # Max (uniquement pour 1h pour alléger)
        if agg_time == 3600:
            indicators.append({
                "measurementPointId": mp, "primaryData": "LAFMax", "aggregationMethod": "max",
                "timeFrequency": "global", "frequencyBand": None, "axis": None, "precision": 1
            })

    payload = {
        "start": f"{start}T00:00:00Z", "end": f"{end}T23:59:59Z",
        "aggregationTime": agg_time, "indicators": indicators
    }
    
    headers = {"accept": "application/json", "Content-Type": "application/json", "X-API-KEY": api_key}
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{proj_id}/data"
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        
        if r.status_code == 200:
            data = r.json()
            if not data.get('timeStamp'): return None
            
            # DataFrame Base
            df = pd.DataFrame({'Date': pd.to_datetime(data['timeStamp'])})
            
            # --- BOUCLE DE PARSING CORRIGÉE ---
            for item in data.get('indicators', []):
                
                # 1. RECUPERATION ROBUSTE DE L'ID ET DU NOM
                # C'est ici que ça plantait. On vérifie la structure.
                mp_id = "Unknown"
                mp_name = "Unknown"
                
                # Cas A : Structure imbriquée (Ton JSON)
                if 'measurementPoint' in item:
                    mp_obj = item['measurementPoint']
                    mp_id = mp_obj.get('measurementPointId')
                    mp_name = mp_obj.get('measurementPointName', str(mp_id))
                
                # Cas B : Structure plate (Ancienne API ou autre endpoint)
                elif 'measurementPointId' in item:
                    mp_id = item['measurementPointId']
                    mp_name = str(mp_id)
                
                # 2. Type de donnée
                # Parfois c'est dans indicatorDescription, parfois à la racine
                dtype = "Val"
                if 'indicatorDescription' in item:
                    dtype = item['indicatorDescription'].get('primaryData', 'Val')
                elif 'primaryData' in item:
                    dtype = item['primaryData']

                col_name = f"{mp_name} | {dtype}"
                
                # 3. VALEURS (Gestion liste imbriquée [[v]])
                raw_vals = item.get('data', {}).get('values')
                if raw_vals:
                    # Si c'est une liste de liste, on aplatit
                    final_vals = raw_vals[0] if (isinstance(raw_vals, list) and len(raw_vals)>0 and isinstance(raw_vals[0], list)) else raw_vals
                    
                    # Sécurité taille
                    if len(final_vals) == len(df):
                        df[col_name] = final_vals
            
            df.set_index('Date', inplace=True)
            return df
            
        else:
            st.error(f"Erreur API ({suffix}): {r.status_code} - {r.text}")
            return None
            
    except Exception as e:
        st.error(f"Erreur Script ({suffix}): {e}")
        return None

# --- EXECUTION ---
if btn_run:
    if not api_key:
        st.error("Clé API requise")
        st.stop()
        
    try:
        mp_ids_list = [int(x.strip()) for x in mps_input.split(",") if x.strip()]
    except:
        st.error("Erreur format IDs")
        st.stop()

    st.session_state['df_1h'] = None
    st.session_state['df_15m'] = None
    
    # 1. 1H
    if use_1h:
        with st.spinner("Chargement 1h..."):
            st.session_state['df_1h'] = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 3600, "1h")

    # 2. 15min
    if use_15m:
        with st.spinner("Chargement 15min..."):
            st.session_state['df_15m'] = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 900, "15m")

# --- VISUALISATION ---
if st.session_state['df_1h'] is not None or st.session_state['df_15m'] is not None:
    
    st.success("Données récupérées !")
    
    # --- GRAPHIQUE SUPERPOSÉ ---
    st.markdown("### 📈 Analyse Temporelle")
    fig = go.Figure()
    
    # 15 min (Lignes fines en arrière plan)
    if st.session_state['df_15m'] is not None:
        df = st.session_state['df_15m']
        # On ne trace que les LAeq pour la clarté
        cols = [c for c in df.columns if "LAeq" in c]
        for c in cols:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[c], mode='lines', name=f"15m - {c}",
                line=dict(width=1), opacity=0.7
            ))
            
    # 1h (Lignes épaisses + Points au premier plan)
    if st.session_state['df_1h'] is not None:
        df = st.session_state['df_1h']
        cols = [c for c in df.columns if "LAeq" in c]
        for c in cols:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[c], mode='lines+markers', name=f"1H - {c}",
                line=dict(width=3), marker=dict(size=7)
            ))

    fig.update_layout(height=600, hovermode="x unified", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # --- TABLEAUX SÉPARÉS ---
    t1, t2 = st.tabs(["Tableau 1h", "Tableau 15min"])
    
    with t1:
        if st.session_state['df_1h'] is not None:
            st.dataframe(st.session_state['df_1h'], use_container_width=True)
            csv = st.session_state['df_1h'].to_csv().encode('utf-8')
            st.download_button("📥 CSV 1h", csv, f"Export_1h_{project_id}.csv", "text/csv")
            
    with t2:
        if st.session_state['df_15m'] is not None:
            st.dataframe(st.session_state['df_15m'], use_container_width=True)
            csv = st.session_state['df_15m'].to_csv().encode('utf-8')
            st.download_button("📥 CSV 15m", csv, f"Export_15m_{project_id}.csv", "text/csv")
