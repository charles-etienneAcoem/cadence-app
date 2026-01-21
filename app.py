import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="Cadence Data V3", page_icon="🎯", layout="wide")
st.title("🎯 Cadence : Interface de Récupération (Logique AppScript)")

# --- STATE MANAGEMENT ---
if 'proj_map' not in st.session_state: st.session_state['proj_map'] = {}
if 'points_map' not in st.session_state: st.session_state['points_map'] = {}
if 'data_df' not in st.session_state: st.session_state['data_df'] = None

# --- SIDEBAR : CONNEXION & PROJET ---
with st.sidebar:
    st.header("1. Authentification")
    api_key = st.text_input("Clé API", type="password")
    
    st.header("2. Sélection Projet")
    
    # Bouton pour lister les projets
    if st.button("🔄 Charger mes projets"):
        if not api_key:
            st.error("Clé manquante")
        else:
            try:
                # On force la pagination pour tout récupérer
                url = "https://cadence.acoem.com/cloud-api/v1/projects?page=0&size=100&sort=name,asc"
                headers = {"accept": "application/json", "X-API-KEY": api_key}
                r = requests.get(url, headers=headers, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    raw_list = []
                    # Gestion des différents formats de réponse possibles
                    if isinstance(data, list): raw_list = data
                    elif isinstance(data, dict) and 'content' in data: raw_list = data['content']
                    
                    if raw_list:
                        mapping = {f"{p.get('name')} ({p.get('id')})": p.get('id') for p in raw_list}
                        st.session_state['proj_map'] = mapping
                        st.success(f"✅ {len(mapping)} projets")
                    else:
                        st.warning("Aucun projet trouvé.")
                else:
                    st.error(f"Erreur API: {r.status_code}")
            except Exception as e:
                st.error(f"Erreur: {e}")

    # Sélecteur de projet ou saisie manuelle (Secours)
    selected_proj_id = None
    if st.session_state['proj_map']:
        p_name = st.selectbox("Choisir :", list(st.session_state['proj_map'].keys()))
        selected_proj_id = st.session_state['proj_map'][p_name]
    else:
        st.info("Si la liste échoue, entrez l'ID ci-dessous :")
        manual_id = st.number_input("ID Manuel", value=1931, step=1)
        selected_proj_id = manual_id

    st.header("3. Points de Mesure")
    # Chargement des points
    if st.button("📍 Charger les points"):
        url_p = f"https://cadence.acoem.com/cloud-api/v1/projects/{selected_proj_id}"
        headers = {"accept": "application/json", "X-API-KEY": api_key}
        try:
            r = requests.get(url_p, headers=headers)
            if r.status_code == 200:
                data = r.json()
                if 'measurementPoints' in data:
                    pmap = {f"{mp['name']} ({mp['id']})": mp['id'] for mp in data['measurementPoints']}
                    st.session_state['points_map'] = pmap
                    st.success(f"{len(pmap)} points")
                else:
                    st.warning("Pas de points dans ce projet")
        except Exception as e:
            st.error(str(e))

    # Sélection multiple des points
    selected_mp_ids = []
    if st.session_state['points_map']:
        sel_names = st.multiselect("Sélectionner :", list(st.session_state['points_map'].keys()), default=list(st.session_state['points_map'].keys()))
        selected_mp_ids = [st.session_state['points_map'][n] for n in sel_names]
    # Fallback manuel pour les points
    elif selected_proj_id: 
        st.caption("Ou IDs manuels :")
        txt_ids = st.text_input("IDs (ex: 3440, 3441)", "3440, 3441")
        if txt_ids:
            selected_mp_ids = [int(x.strip()) for x in txt_ids.split(",") if x.strip()]


# --- CONFIGURATION INDICATEURS (Inspiré du AppScript) ---
if selected_mp_ids:
    st.divider()
    st.markdown(f"### ⚙️ Configuration Extraction (Projet {selected_proj_id})")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Indicateurs**")
        # On définit les indicateurs exactement comme dans ton AppScript (Primary, Global, Band, Agg, Axis)
        use_leq = st.checkbox("LAeq (Average)", True)
        use_max = st.checkbox("LAFMax (Max)", True)
        use_min = st.checkbox("LAFMin (Min)", False)
        
    with col2:
        st.markdown("**Périodicité**")
        # On peut mixer les deux requêtes
        do_1h = st.checkbox("Horaires (1h)", True)
        do_15m = st.checkbox("15 Minutes", True)
        
    with col3:
        st.markdown("**Dates**")
        d_start = st.date_input("Du", date(2025, 1, 21))
        d_end = st.date_input("Au", date.today())

    # --- LE COEUR DU CODE : CONSTRUCTION DU PAYLOAD ---
    if st.button("🚀 VALIDER ET RÉCUPÉRER", type="primary", use_container_width=True):
        
        headers = {
            "accept": "application/json", 
            "Content-Type": "application/json", 
            "X-API-KEY": api_key
        }
        url_data = f"https://cadence.acoem.com/cloud-api/v1/projects/{selected_proj_id}/data"
        
        # Dates ISO 8601
        start_iso = f"{d_start}T00:00:00Z"
        end_iso = f"{d_end}T23:59:59Z"
        
        dfs_result = []

        # FONCTION INTERNE : Création de l'objet Indicator façon AppScript
        def make_indicator_obj(mp_id, primary, agg_method):
            # C'est ICI que ça se joue. On met 'None' pour obtenir 'null' dans le JSON
            return {
                "measurementPointId": mp_id,
                "primaryData": primary,
                "timeFrequency": "global",
                "frequencyBand": None,      # IMPORTANT : Correspond au row[2] null de ton script
                "aggregationMethod": agg_method,
                "axis": None,               # IMPORTANT : Correspond au row[6] null
                "precision": 1
            }

        # 1. TRAITEMENT 1 HEURE
        if do_1h:
            indicators_list = []
            for mp in selected_mp_ids:
                if use_leq: indicators_list.append(make_indicator_obj(mp, "LAeq", "average"))
                if use_max: indicators_list.append(make_indicator_obj(mp, "LAFMax", "max"))
                if use_min: indicators_list.append(make_indicator_obj(mp, "LAFMin", "min"))
            
            if indicators_list:
                payload_1h = {
                    "start": start_iso,
                    "end": end_iso,
                    "aggregationTime": 3600, # 1h
                    "indicators": indicators_list
                }
                
                with st.spinner("Requête 1h en cours..."):
                    try:
                        r = requests.post(url_data, headers=headers, json=payload_1h)
                        if r.status_code == 200:
                            d = r.json()
                            if d.get('timestamp'):
                                df = pd.DataFrame({'Date': pd.to_datetime(d['timestamp'])})
                                for item in d['indicators']:
                                    # Nommage propre colonnes
                                    mp_n = str(item['measurementPointId'])
                                    for k,v in st.session_state['points_map'].items():
                                        if v == item['measurementPointId']: mp_n = k.split('(')[0].strip()
                                    col = f"{mp_n} | {item['primaryData']} (1h)"
                                    if item.get('data') and item['data'].get('values'):
                                        df[col] = item['data']['values']
                                df.set_index('Date', inplace=True)
                                dfs_result.append(df)
                        else:
                            st.error(f"Erreur 1h ({r.status_code})")
                            with st.expander("🔍 Voir le JSON envoyé (Debug)"):
                                st.json(payload_1h)
                            with st.expander("🔍 Voir la réponse erreur"):
                                st.write(r.text)
                    except Exception as e:
                        st.error(e)

        # 2. TRAITEMENT 15 MINUTES
        if do_15m:
            indicators_list_15 = []
            for mp in selected_mp_ids:
                # Souvent en 15min on ne veut que le Leq, mais on peut ajouter max
                if use_leq: indicators_list_15.append(make_indicator_obj(mp, "LAeq", "average"))
            
            if indicators_list_15:
                payload_15 = {
                    "start": start_iso,
                    "end": end_iso,
                    "aggregationTime": 900, # 15 min
                    "indicators": indicators_list_15
                }
                
                with st.spinner("Requête 15m en cours..."):
                    try:
                        r = requests.post(url_data, headers=headers, json=payload_15)
                        if r.status_code == 200:
                            d = r.json()
                            if d.get('timestamp'):
                                df = pd.DataFrame({'Date': pd.to_datetime(d['timestamp'])})
                                for item in d['indicators']:
                                    mp_n = str(item['measurementPointId'])
                                    for k,v in st.session_state['points_map'].items():
                                        if v == item['measurementPointId']: mp_n = k.split('(')[0].strip()
                                    col = f"{mp_n} | {item['primaryData']} (15m)"
                                    if item.get('data') and item['data'].get('values'):
                                        df[col] = item['data']['values']
                                df.set_index('Date', inplace=True)
                                dfs_result.append(df)
                        else:
                            st.error(f"Erreur 15m ({r.status_code})")
                            with st.expander("🔍 Voir le JSON envoyé (Debug)"):
                                st.json(payload_15)
                    except Exception as e:
                        st.error(e)

        # FUSION ET AFFICHAGE
        if dfs_result:
            final_df = dfs_result[0]
            for d in dfs_result[1:]:
                final_df = final_df.join(d, how='outer')
            
            final_df.reset_index(inplace=True)
            final_df.sort_values('Date', inplace=True)
            st.session_state['data_df'] = final_df
            st.success("Données récupérées !")
        else:
            st.warning("Aucune donnée disponible.")

# --- AFFICHAGE RESULTATS ---
if st.session_state['data_df'] is not None:
    df = st.session_state['data_df']
    st.divider()
    
    # Graphique Plotly
    fig = px.line(df, x='Date', y=df.columns[1:], title="Visualisation des Niveaux", height=600)
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)
    
    # Tableau & Export
    col_t, col_e = st.columns([3, 1])
    with col_t:
        st.dataframe(df, use_container_width=True, height=300)
    with col_e:
        st.write("### Export")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 CSV", csv, "export_cadence.csv", "text/csv", type="primary")
