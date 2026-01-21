import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Cadence Ultimate", page_icon="🛠️", layout="wide")
st.title("🛠️ Cadence : Interface de Récupération")

# --- SESSION STATE ---
if 'proj_map' not in st.session_state: st.session_state['proj_map'] = {}
if 'points_map' not in st.session_state: st.session_state['points_map'] = {}
if 'data_df' not in st.session_state: st.session_state['data_df'] = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Connexion")
    api_key = st.text_input("Clé API", type="password", value="") # Tu peux mettre ta clé par défaut ici si tu veux
    
    st.divider()
    
    # --- BLOCK 1 : CHOIX DU PROJET ---
    st.header("2. Projet")
    
    # OPTION DE SECOURS : SAISIE MANUELLE
    use_manual = st.checkbox("Saisir l'ID Projet manuellement", value=False, help="Cochez si la liste automatique ne marche pas")
    
    selected_proj_id = None
    
    if use_manual:
        # MODE MANUEL (Pour contourner le bug)
        selected_proj_id = st.number_input("ID du Projet", value=1931, step=1)
        st.info(f"Projet forcé : {selected_proj_id}")
    else:
        # MODE AUTOMATIQUE (Appel API)
        if st.button("🔄 Charger la liste des projets"):
            if not api_key:
                st.error("Il faut la Clé API !")
            else:
                try:
                    url = "https://cadence.acoem.com/cloud-api/v1/projects"
                    # On tente sans paramètre de pagination pour voir, ou avec size large
                    params = {"size": 100, "page": 0} 
                    headers = {"accept": "application/json", "X-API-KEY": api_key}
                    
                    r = requests.get(url, headers=headers, params=params, timeout=10)
                    
                    if r.status_code == 200:
                        data = r.json()
                        
                        # --- INSPECTEUR DE JSON ---
                        # On cherche la liste partout
                        raw_list = []
                        if isinstance(data, list):
                            raw_list = data
                        elif isinstance(data, dict) and 'content' in data:
                            raw_list = data['content']
                        elif isinstance(data, dict) and 'items' in data:
                            raw_list = data['items']
                        
                        if raw_list:
                            mapping = {f"{p.get('name', 'N/A')} ({p.get('id')})": p.get('id') for p in raw_list}
                            st.session_state['proj_map'] = mapping
                            st.success(f"✅ {len(mapping)} projets trouvés")
                        else:
                            st.warning("Liste vide reçue.")
                            st.json(data) # Affiche le JSON pour comprendre le bug
                    else:
                        st.error(f"Erreur HTTP {r.status_code}")
                        st.text(r.text) # Affiche l'erreur textuelle
                except Exception as e:
                    st.error(f"Erreur technique : {e}")

        # Menu déroulant si on a trouvé des projets
        if st.session_state['proj_map']:
            p_choice = st.selectbox("Choisir le projet", list(st.session_state['proj_map'].keys()))
            selected_proj_id = st.session_state['proj_map'][p_choice]

    st.divider()

    # --- BLOCK 2 : POINTS DE MESURE ---
    st.header("3. Points de Mesure")
    
    # On ne charge les points que si on a un ID de projet
    if selected_proj_id:
        if st.button("📍 Charger les points"):
            url_p = f"https://cadence.acoem.com/cloud-api/v1/projects/{selected_proj_id}"
            headers = {"accept": "application/json", "X-API-KEY": api_key}
            try:
                r2 = requests.get(url_p, headers=headers)
                if r2.status_code == 200:
                    d2 = r2.json()
                    # Recherche des points dans 'measurementPoints'
                    if 'measurementPoints' in d2:
                        pmap = {f"{mp['name']} ({mp['id']})": mp['id'] for mp in d2['measurementPoints']}
                        st.session_state['points_map'] = pmap
                        st.success(f"{len(pmap)} points trouvés")
                    else:
                        st.warning("Pas de clé 'measurementPoints' trouvée.")
                        st.json(d2)
                else:
                    st.error(f"Erreur Points: {r2.status_code}")
            except Exception as e:
                st.error(str(e))

    # Multiselect pour les points
    selected_mp_ids = []
    if st.session_state['points_map']:
        sel_names = st.multiselect("Sélectionner :", list(st.session_state['points_map'].keys()), default=list(st.session_state['points_map'].keys()))
        selected_mp_ids = [st.session_state['points_map'][n] for n in sel_names]
    elif selected_proj_id:
        # Fallback manuel si l'API points échoue aussi
        st.caption("Si la liste est vide, entrez les IDs manuellement :")
        man_ids = st.text_input("IDs (séparés par virgule)", "3440, 3441")
        if man_ids:
            selected_mp_ids = [int(x.strip()) for x in man_ids.split(",") if x.strip()]

# --- CORPS PRINCIPAL ---
if selected_mp_ids:
    st.markdown(f"### 🎯 Configuration : Projet {selected_proj_id}")
    st.write(f"Points ciblés : `{selected_mp_ids}`")
    
    with st.expander("🛠️ Paramètres d'extraction", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**1h (Hourly)**")
            h_leq = st.checkbox("LAeq", True, key="h1")
            h_max = st.checkbox("LAFMax", True, key="h2")
            h_min = st.checkbox("LAFMin", False, key="h3")
        with c2:
            st.markdown("**15min (Short)**")
            s_leq = st.checkbox("LAeq", True, key="s1")
            s_max = st.checkbox("LAFMax", False, key="s2")
        with c3:
            st.markdown("**Dates**")
            d1 = st.date_input("Début", date(2025, 1, 21))
            d2 = st.date_input("Fin", date.today())

    if st.button("🚀 LANCER L'EXTRACTION", type="primary", use_container_width=True):
        # ... CODE D'EXTRACTION (IDENTIQUE AVANT, MAIS ROBUSTE) ...
        dfs = []
        headers = {"accept": "application/json", "Content-Type": "application/json", "X-API-KEY": api_key}
        url_data = f"https://cadence.acoem.com/cloud-api/v1/projects/{selected_proj_id}/data"
        
        # Fonction interne pour éviter la répétition
        def call_api(agg, inds, suffix):
            payload_inds = []
            for mp in selected_mp_ids:
                for i, m in inds:
                    payload_inds.append({"measurementPointId": mp, "primaryData": i, "aggregationMethod": m, "timeFrequency": "global", "precision": 1})
            
            body = {
                "start": f"{d1}T00:00:00Z", "end": f"{d2}T23:59:59Z",
                "aggregationTime": agg, "indicators": payload_inds
            }
            
            try:
                res = requests.post(url_data, headers=headers, json=body)
                if res.status_code == 200:
                    jd = res.json()
                    if jd.get('timestamp'):
                        dft = pd.DataFrame({'Date': pd.to_datetime(jd['timestamp'])})
                        for item in jd['indicators']:
                            # Nommage propre (gestion fallback ID)
                            mp_n = str(item['measurementPointId'])
                            # Essai de trouver le nom
                            for k,v in st.session_state['points_map'].items():
                                if v == item['measurementPointId']: mp_n = k.split('(')[0].strip()
                            
                            col = f"{mp_n} | {item['primaryData']} ({suffix})"
                            if item.get('data') and item['data'].get('values'):
                                dft[col] = item['data']['values']
                        dft.set_index('Date', inplace=True)
                        return dft
            except Exception as e:
                st.error(e)
            return None

        with st.spinner("Travail en cours..."):
            # 1h
            li_1h = []
            if h_leq: li_1h.append(("LAeq", "average"))
            if h_max: li_1h.append(("LAFMax", "max"))
            if h_min: li_1h.append(("LAFMin", "min"))
            if li_1h:
                r1 = call_api(3600, li_1h, "1h")
                if r1 is not None: dfs.append(r1)
            
            # 15m
            li_15 = []
            if s_leq: li_15.append(("LAeq", "average"))
            if s_max: li_15.append(("LAFMax", "max"))
            if li_15:
                r2 = call_api(900, li_15, "15m")
                if r2 is not None: dfs.append(r2)
            
            if dfs:
                final = dfs[0]
                for d in dfs[1:]: final = final.join(d, how='outer')
                final.reset_index(inplace=True)
                final.sort_values('Date', inplace=True)
                st.session_state['data_df'] = final
                st.success("Terminé !")
            else:
                st.error("Aucune donnée reçue.")

# --- VISUALISATION ---
if st.session_state['data_df'] is not None:
    df = st.session_state['data_df']
    
    st.divider()
    # Graphique
    fig = px.line(df, x='Date', y=df.columns[1:], height=600, title="Visualisation Interactive")
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    
    # Export
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Télécharger CSV", csv, "export_cadence.csv", "text/csv", type="primary")

else:
    st.info("👈 Configurez votre extraction dans le menu de gauche.")
