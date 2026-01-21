import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Cadence Explorer V2", page_icon="🛰️", layout="wide")
st.title("🛰️ Cadence Explorer : Connecteur Cloud API")

# --- INITIALISATION SESSION STATE ---
if 'projects_map' not in st.session_state: st.session_state['projects_map'] = {}
if 'points_map' not in st.session_state: st.session_state['points_map'] = {}
if 'data_result' not in st.session_state: st.session_state['data_result'] = None

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("1. Authentification")
    api_key = st.text_input("Clé API (X-API-KEY)", type="password", help="Votre clé commençant par EZfX...")
    
    # BOUTON 1 : LISTER LES PROJETS
    if st.button("🔄 1. Lister les Projets", type="primary"):
        if not api_key:
            st.error("⚠️ Clé API manquante")
        else:
            # On force la pagination pour être sûr d'avoir une liste
            url = "https://cadence.acoem.com/cloud-api/v1/projects"
            params = {"page": 0, "size": 100, "sort": "name,asc"}
            headers = {"accept": "application/json", "X-API-KEY": api_key}
            
            with st.spinner("Connexion au Cloud Cadence..."):
                try:
                    r = requests.get(url, headers=headers, params=params, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        
                        # --- DÉTECTION INTELLIGENTE DU FORMAT JSON ---
                        # Cas 1 : La liste est dans 'content' (Standard Spring Boot/Cadence)
                        if isinstance(data, dict) and 'content' in data:
                            proj_list = data['content']
                        # Cas 2 : La liste est directe
                        elif isinstance(data, list):
                            proj_list = data
                        else:
                            proj_list = []
                        
                        # Mapping ID -> Nom
                        pmap = {}
                        for p in proj_list:
                            p_id = p.get('id')
                            p_name = p.get('name', f"Projet {p_id}")
                            pmap[f"{p_name} ({p_id})"] = p_id
                        
                        st.session_state['projects_map'] = pmap
                        
                        if pmap:
                            st.success(f"✅ {len(pmap)} projets trouvés")
                        else:
                            st.warning("Aucun projet trouvé. Vérifiez les droits de la clé.")
                            with st.expander("Voir réponse brute API"):
                                st.json(data)
                    else:
                        st.error(f"Erreur {r.status_code}")
                        st.write(r.text)
                except Exception as e:
                    st.error(f"Erreur de connexion : {e}")

    # SÉLECTION DU PROJET (Seulement si la liste existe)
    selected_proj_id = None
    if st.session_state['projects_map']:
        st.divider()
        st.header("2. Choix du Projet")
        proj_label = st.selectbox("Sélectionnez un projet :", options=list(st.session_state['projects_map'].keys()))
        selected_proj_id = st.session_state['projects_map'][proj_label]
        
        # BOUTON 2 : CHERCHER LES POINTS (DEMANDÉ SPÉCIFIQUEMENT)
        if st.button("📍 3. Sélection des points de mesure"):
            url_p = f"https://cadence.acoem.com/cloud-api/v1/projects/{selected_proj_id}"
            headers = {"accept": "application/json", "X-API-KEY": api_key}
            
            with st.spinner(f"Analyse du projet {selected_proj_id}..."):
                try:
                    r_p = requests.get(url_p, headers=headers)
                    if r_p.status_code == 200:
                        p_data = r_p.json()
                        points_found = {}
                        
                        # Essai 1 : Chercher la clé 'measurementPoints' dans les détails du projet
                        if 'measurementPoints' in p_data and isinstance(p_data['measurementPoints'], list):
                            for mp in p_data['measurementPoints']:
                                points_found[f"{mp['name']} ({mp['id']})"] = mp['id']
                        
                        # Si vide, on pourrait essayer un autre endpoint, mais généralement c'est ici.
                        st.session_state['points_map'] = points_found
                        
                        if points_found:
                            st.success(f"✅ {len(points_found)} points récupérés !")
                        else:
                            st.warning("Aucun point trouvé dans ce projet.")
                            with st.expander("Voir réponse brute API (Debug)"):
                                st.json(p_data)
                    else:
                        st.error(f"Erreur API Points : {r_p.status_code}")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # CONFIGURATION FINALE
    selected_mp_ids = []
    if st.session_state['points_map']:
        st.divider()
        st.header("4. Configuration Extraction")
        
        # Multiselect Points
        sel_points = st.multiselect("Points à analyser :", options=list(st.session_state['points_map'].keys()), default=list(st.session_state['points_map'].keys()))
        selected_mp_ids = [st.session_state['points_map'][k] for k in sel_points]
        
        st.caption("Indicateurs :")
        c1, c2 = st.columns(2)
        with c1:
            i_h_leq = st.checkbox("1h - LAeq", True)
            i_h_max = st.checkbox("1h - LAFMax", True)
            i_h_min = st.checkbox("1h - LAFMin", False)
        with c2:
            i_15_leq = st.checkbox("15m - LAeq", True)
            i_15_max = st.checkbox("15m - LAFMax", False)
            
        st.caption("Période :")
        d_start = st.date_input("Début", date(2025, 1, 21))
        d_end = st.date_input("Fin", date.today())
        
        st.divider()
        btn_launch = st.button("🚀 LANCER L'EXTRACTION", type="primary")

# --- LOGIQUE D'EXTRACTION (MAIN) ---
if 'btn_launch' in locals() and btn_launch:
    if not selected_mp_ids:
        st.error("❌ Sélectionnez au moins un point de mesure.")
    else:
        # Configuration
        url_data = f"https://cadence.acoem.com/cloud-api/v1/projects/{selected_proj_id}/data"
        headers = {"accept": "application/json", "Content-Type": "application/json", "X-API-KEY": api_key}
        start_iso = f"{d_start}T00:00:00Z"
        end_iso = f"{d_end}T23:59:59Z"
        
        dfs = []
        progress_text = "Opération en cours..."
        my_bar = st.progress(0, text=progress_text)

        # FONCTION REQUETE GENERIQUE
        def get_cadence_data(agg_time, indicators_list, label_suffix):
            if not indicators_list: return None
            
            payload_inds = []
            for mp_id in selected_mp_ids:
                for ind_name, agg_method in indicators_list:
                    payload_inds.append({
                        "measurementPointId": mp_id, "primaryData": ind_name,
                        "timeFrequency": "global", "aggregationMethod": agg_method, "precision": 1
                    })
            
            payload = {
                "start": start_iso, "end": end_iso,
                "aggregationTime": agg_time, "indicators": payload_inds
            }
            
            try:
                # Debug payload si besoin
                # st.write(payload) 
                resp = requests.post(url_data, headers=headers, json=payload)
                if resp.status_code == 200:
                    d = resp.json()
                    if d.get('timestamp'):
                        df = pd.DataFrame({'Date': pd.to_datetime(d['timestamp'])})
                        for item in d['indicators']:
                            # Trouver nom
                            mp_label = "Inconnu"
                            for k, v in st.session_state['points_map'].items():
                                if v == item['measurementPointId']:
                                    mp_label = k.split('(')[0].strip()
                                    break
                            
                            col_name = f"{mp_label} | {item['primaryData']} ({label_suffix})"
                            if item.get('data') and item['data'].get('values'):
                                df[col_name] = item['data']['values']
                        df.set_index('Date', inplace=True)
                        return df
            except Exception as e:
                st.error(f"Erreur requête {label_suffix}: {e}")
            return None

        # 1. REQUETE 1H
        inds_1h = []
        if i_h_leq: inds_1h.append(("LAeq", "average"))
        if i_h_max: inds_1h.append(("LAFMax", "max"))
        if i_h_min: inds_1h.append(("LAFMin", "min"))
        
        if inds_1h:
            my_bar.progress(30, text="Téléchargement données 1h...")
            df1 = get_cadence_data(3600, inds_1h, "1h")
            if df1 is not None: dfs.append(df1)

        # 2. REQUETE 15M
        inds_15 = []
        if i_15_leq: inds_15.append(("LAeq", "average"))
        if i_15_max: inds_15.append(("LAFMax", "max"))
        
        if inds_15:
            my_bar.progress(60, text="Téléchargement données 15min...")
            df2 = get_cadence_data(900, inds_15, "15m")
            if df2 is not None: dfs.append(df2)

        # FUSION
        my_bar.progress(90, text="Fusion et affichage...")
        if dfs:
            final = dfs[0]
            for d in dfs[1:]:
                final = final.join(d, how='outer')
            
            final.reset_index(inplace=True)
            final.sort_values('Date', inplace=True)
            st.session_state['data_result'] = final
            my_bar.empty()
            st.success("Données récupérées avec succès !")
        else:
            my_bar.empty()
            st.warning("Aucune donnée reçue. Vérifiez que les capteurs étaient actifs sur cette période.")

# --- AFFICHAGE RESULTATS ---
if st.session_state['data_result'] is not None:
    df = st.session_state['data_result']
    
    st.markdown("### 📊 Visualisation")
    fig = px.line(df, x='Date', y=df.columns[1:], height=600)
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)
    
    col_t, col_d = st.columns([3, 1])
    with col_t:
        st.dataframe(df, use_container_width=True, height=300)
    with col_dl:
        st.write("### Export")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger CSV", csv, "export_cadence.csv", "text/csv", type="primary")

# MESSAGE D'ACCUEIL
if not st.session_state['projects_map']:
    st.info("👋 Bienvenue. Entrez votre clé API à gauche pour commencer.")
