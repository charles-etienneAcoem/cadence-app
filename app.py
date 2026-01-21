import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Cadence Manuel & Graph", page_icon="📊", layout="wide")
st.title("📊 Cadence : Extraction & Comparaison Temporelle")

# --- INITIALISATION STATE ---
if 'df_1h' not in st.session_state: st.session_state['df_1h'] = None
if 'df_15m' not in st.session_state: st.session_state['df_15m'] = None

# --- SIDEBAR (PARAMÈTRES) ---
with st.sidebar:
    st.header("1. Authentification")
    api_key = st.text_input("Clé API", type="password")
    
    st.divider()
    
    st.header("2. Cibles (Manuel)")
    # Entrées manuelles comme demandé
    project_id = st.number_input("ID Projet", value=1931, step=1)
    mps_input = st.text_input("IDs Points de Mesure", value="3440, 3441", help="Séparez par une virgule ex: 3440, 3441")
    
    st.divider()
    
    st.header("3. Configuration")
    st.caption("Données à récupérer :")
    # On force un peu la main pour avoir une belle comparaison graphique
    use_1h = st.checkbox("Données 1h (LAeq + Max)", value=True)
    use_15m = st.checkbox("Données 15min (LAeq)", value=True)
    
    st.caption("Période :")
    d_start = st.date_input("Début", date(2025, 1, 21))
    d_end = st.date_input("Fin", date.today())
    
    st.divider()
    btn_run = st.button("🚀 Lancer l'analyse", type="primary")

# --- FONCTION CORE (RECUPERATION) ---
def get_cadence_data(api_key, proj_id, mp_ids, start, end, agg_time, suffix):
    """Récupère les données et gère le format spécifique [[val]]"""
    
    # 1. Construction Payload (Format Strict AppScript)
    indicators = []
    for mp in mp_ids:
        # LAeq (Base)
        indicators.append({
            "measurementPointId": mp, "primaryData": "LAeq", "aggregationMethod": "average",
            "timeFrequency": "global", "frequencyBand": None, "axis": None, "precision": 1
        })
        # Si c'est du 1h, on ajoute le Max pour avoir plus d'infos
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
            
            # Création DataFrame
            df = pd.DataFrame({'Date': pd.to_datetime(data['timeStamp'])})
            
            for item in data.get('indicators', []):
                # Récupération ID Point et Type donnée
                mp = item['measurementPointId']
                dtype = item['primaryData']
                col_name = f"MP {mp} | {dtype}"
                
                # Gestion de la valeur imbriquée [[val]] ou [val]
                raw_vals = item.get('data', {}).get('values')
                if raw_vals:
                    # Si c'est une liste de liste, on prend la 1ere, sinon la liste directe
                    final_vals = raw_vals[0] if (isinstance(raw_vals, list) and len(raw_vals)>0 and isinstance(raw_vals[0], list)) else raw_vals
                    
                    if len(final_vals) == len(df):
                        df[col_name] = final_vals
            
            df.set_index('Date', inplace=True)
            return df
        else:
            st.error(f"Erreur API ({suffix}): {r.status_code}")
            return None
    except Exception as e:
        st.error(f"Erreur Script ({suffix}): {e}")
        return None

# --- MAIN EXECUTION ---
if btn_run:
    if not api_key:
        st.error("Clé API requise.")
        st.stop()
        
    try:
        mp_ids_list = [int(x.strip()) for x in mps_input.split(",") if x.strip()]
    except:
        st.error("Erreur format IDs Points (utiliser: 3440, 3441)")
        st.stop()

    # Reset
    st.session_state['df_1h'] = None
    st.session_state['df_15m'] = None
    
    # 1. Récupération 1h
    if use_1h:
        with st.spinner("Récupération données 1h..."):
            df1 = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 3600, "1h")
            st.session_state['df_1h'] = df1

    # 2. Récupération 15min
    if use_15m:
        with st.spinner("Récupération données 15min..."):
            df2 = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 900, "15m")
            st.session_state['df_15m'] = df2

# --- VISUALISATION ---
if st.session_state['df_1h'] is not None or st.session_state['df_15m'] is not None:
    
    st.success("Données chargées !")
    
    # --- BLOC GRAPHIQUE SUPERPOSÉ ---
    st.markdown("### 📈 Superposition : 1h (Points) vs 15min (Ligne)")
    
    fig = go.Figure()
    
    # AJOUT DONNÉES 15 MIN (LIGNES FINES) - D'abord pour être en arrière plan
    if st.session_state['df_15m'] is not None:
        df = st.session_state['df_15m']
        # On ne prend que les colonnes LAeq pour le graph pour pas surcharger
        cols_laeq = [c for c in df.columns if "LAeq" in c]
        for col in cols_laeq:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col],
                mode='lines',
                name=f"{col} (15m)",
                line=dict(width=1),
                opacity=0.7
            ))

    # AJOUT DONNÉES 1H (LIGNES + MARQUEURS) - Au dessus
    if st.session_state['df_1h'] is not None:
        df = st.session_state['df_1h']
        cols_laeq = [c for c in df.columns if "LAeq" in c]
        for col in cols_laeq:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col],
                mode='lines+markers',
                name=f"{col} (1h)",
                line=dict(width=3),
                marker=dict(size=8, symbol="circle")
            ))

    fig.update_layout(
        title="Comparaison LAeq (1h vs 15min)",
        xaxis_title="Date / Heure",
        yaxis_title="dB",
        hovermode="x unified",
        height=600,
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()

    # --- BLOC TABLEAUX SÉPARÉS ---
    st.markdown("### 📋 Tableaux de Données")
    
    tab1, tab2 = st.tabs(["🕒 Tableau 1H", "⏱️ Tableau 15min"])
    
    with tab1:
        if st.session_state['df_1h'] is not None:
            st.dataframe(st.session_state['df_1h'], use_container_width=True)
            csv1 = st.session_state['df_1h'].to_csv().encode('utf-8')
            st.download_button("📥 Télécharger CSV (1h)", csv1, f"Data_1h_{project_id}.csv", "text/csv")
        else:
            st.info("Aucune donnée 1h.")
            
    with tab2:
        if st.session_state['df_15m'] is not None:
            st.dataframe(st.session_state['df_15m'], use_container_width=True)
            csv2 = st.session_state['df_15m'].to_csv().encode('utf-8')
            st.download_button("📥 Télécharger CSV (15m)", csv2, f"Data_15m_{project_id}.csv", "text/csv")
        else:
            st.info("Aucune donnée 15min.")
