import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Cadence Auto-Discovery", page_icon="📡", layout="wide")
st.title("📡 Cadence : Explorateur de Données")

# --- GESTION DE MÉMOIRE (Session State) ---
# On stocke les listes pour ne pas les perdre quand on clique ailleurs
if 'projects_list' not in st.session_state:
    st.session_state['projects_list'] = {} # {Nom: ID}
if 'points_list' not in st.session_state:
    st.session_state['points_list'] = {}   # {Nom: ID}
if 'data_cache' not in st.session_state:
    st.session_state['data_cache'] = None

# --- BARRE LATÉRALE : SÉQUENCE DE CONFIGURATION ---
with st.sidebar:
    st.header("1. Authentification")
    
    # ÉTAPE 1 : LA CLÉ API
    api_key = st.text_input("Clé API", type="password", help="Collez votre clé ici")
    
    # BOUTON 1 : CHERCHER LES PROJETS
    if st.button("🔍 Lister mes projets", type="primary"):
        if not api_key:
            st.error("⚠️ Clé API vide !")
        else:
            with st.spinner("Recherche des projets..."):
                try:
                    # Endpoint pour lister tous les projets
                    url = "https://cadence.acoem.com/cloud-api/v1/projects"
                    headers = {"accept": "application/json", "X-API-KEY": api_key}
                    r = requests.get(url, headers=headers, timeout=15)
                    
                    if r.status_code == 200:
                        projs = r.json()
                        # Création du dictionnaire {Nom (ID): ID}
                        # La structure de réponse est généralement une liste de projets
                        proj_dict = {}
                        if isinstance(projs, list):
                            for p in projs:
                                label = f"{p.get('name', 'Sans Nom')} ({p.get('id')})"
                                proj_dict[label] = p.get('id')
                        elif 'content' in projs: # Parfois c'est paginé dans 'content'
                             for p in projs['content']:
                                label = f"{p.get('name', 'Sans Nom')} ({p.get('id')})"
                                proj_dict[label] = p.get('id')
                        
                        st.session_state['projects_list'] = proj_dict
                        # On vide la sélection précédente de points
                        st.session_state['points_list'] = {} 
                        st.success(f"✅ {len(proj_dict)} projets trouvés")
                    else:
                        st.error(f"Erreur API ({r.status_code})")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    st.divider()

    # ÉTAPE 2 : CHOIX DU PROJET
    selected_project_id = None
    if st.session_state['projects_list']:
        st.header("2. Sélection du Projet")
        
        # Liste déroulante des projets
        proj_name_sel = st.selectbox(
            "Choisissez un projet :", 
            options=list(st.session_state['projects_list'].keys())
        )
        selected_project_id = st.session_state['projects_list'][proj_name_sel]
        
        # Dès qu'un projet est choisi, on cherche ses points AUTOMATIQUEMENT
        # On utilise le cache pour éviter de requêter à chaque milliseconde
        url_p = f"https://cadence.acoem.com/cloud-api/v1/projects/{selected_project_id}"
        headers = {"accept": "application/json", "X-API-KEY": api_key}
        
        try:
            r_p = requests.get(url_p, headers=headers)
            if r_p.status_code == 200:
                p_data = r_p.json()
                pts = {}
                if 'measurementPoints' in p_data:
                    for mp in p_data['measurementPoints']:
                        pts[f"{mp['name']} ({mp['id']})"] = mp['id']
                st.session_state['points_list'] = pts
        except:
            pass

    # ÉTAPE 3 : CHOIX DES POINTS & CONFIGURATION
    selected_mp_ids = []
    if st.session_state['points_list']:
        st.header("3. Configuration")
        
        # Multiselect Points
        mp_names_sel = st.multiselect(
            "Points de mesure :",
            options=list(st.session_state['points_list'].keys()),
            default=list(st.session_state['points_list'].keys())
        )
        # Récupération des IDs
        selected_mp_ids = [st.session_state['points_list'][name] for name in mp_names_sel]
        
        st.caption("Indicateurs :")
        c1, c2 = st.columns(2)
        with c1:
            check_1h_leq = st.checkbox("1h - LAeq", True)
            check_1h_max = st.checkbox("1h - LAFMax", True)
            check_1h_min = st.checkbox("1h - LAFMin", False)
        with c2:
            check_15m_leq = st.checkbox("15m - LAeq", True)
            
        st.caption("Période :")
        d_start = st.date_input("Début", date(2025, 1, 21))
        d_end = st.date_input("Fin", date.today())
        
        st.divider()
        btn_run = st.button("🚀 LANCER L'ANALYSE", type="primary")

# --- LOGIQUE PRINCIPALE (MAIN) ---

# Message d'accueil si rien n'est lancé
if not st.session_state['projects_list']:
    st.info("👋 Bienvenue. Entrez votre Clé API à gauche et cliquez sur **'Lister mes projets'** pour commencer.")

# Si on lance l'analyse
if st.session_state['points_list'] and 'btn_run' in locals() and btn_run:
    if not selected_mp_ids:
        st.error("⚠️ Aucun point sélectionné.")
    else:
        # Préparation
        dfs = []
        headers = {"accept": "application/json", "Content-Type": "application/json", "X-API-KEY": api_key}
        url_data = f"https://cadence.acoem.com/cloud-api/v1/projects/{selected_project_id}/data"
        
        # Dates ISO
        start_iso = f"{d_start}T00:00:00Z"
        end_iso = f"{d_end}T23:59:59Z"

        progress_bar = st.progress(0, text="Démarrage...")
        
        # --- REQUETE 1H ---
        inds_1h = []
        if check_1h_leq: inds_1h.append(("LAeq", "average"))
        if check_1h_max: inds_1h.append(("LAFMax", "max"))
        if check_1h_min: inds_1h.append(("LAFMin", "min"))
        
        if inds_1h:
            progress_bar.progress(25, text="Récupération données 1 heure...")
            payload_inds = []
            for mp_id in selected_mp_ids:
                for ind, agg in inds_1h:
                    payload_inds.append({
                        "measurementPointId": mp_id, "primaryData": ind, 
                        "timeFrequency": "global", "aggregationMethod": agg, "precision": 1
                    })
            try:
                r1 = requests.post(url_data, headers=headers, json={
                    "start": start_iso, "end": end_iso, "aggregationTime": 3600, "indicators": payload_inds
                })
                if r1.status_code == 200:
                    d1 = r1.json()
                    if d1.get('timestamp'):
                        tmp_df = pd.DataFrame({'Date': pd.to_datetime(d1['timestamp'])})
                        for item in d1['indicators']:
                            # Trouver le nom du point via son ID
                            # On inverse le dico points_list pour trouver le nom via l'ID
                            inv_map = {v: k for k, v in st.session_state['points_list'].items()}
                            p_name = inv_map.get(item['measurementPointId'], str(item['measurementPointId']))
                            # Nettoyage nom
                            p_clean = p_name.split('(')[0].strip()
                            col = f"{p_clean} | 1h {item['primaryData']}"
                            if item.get('data') and item['data'].get('values'):
                                tmp_df[col] = item['data']['values']
                        tmp_df.set_index('Date', inplace=True)
                        dfs.append(tmp_df)
            except Exception as e:
                st.error(f"Erreur 1h : {e}")

        # --- REQUETE 15M ---
        if check_15m_leq:
            progress_bar.progress(60, text="Récupération données 15 minutes...")
            payload_inds_15 = []
            for mp_id in selected_mp_ids:
                payload_inds_15.append({
                    "measurementPointId": mp_id, "primaryData": "LAeq", 
                    "timeFrequency": "global", "aggregationMethod": "average", "precision": 1
                })
            try:
                r2 = requests.post(url_data, headers=headers, json={
                    "start": start_iso, "end": end_iso, "aggregationTime": 900, "indicators": payload_inds_15
                })
                if r2.status_code == 200:
                    d2 = r2.json()
                    if d2.get('timestamp'):
                        tmp_df = pd.DataFrame({'Date': pd.to_datetime(d2['timestamp'])})
                        for item in d2['indicators']:
                            inv_map = {v: k for k, v in st.session_state['points_list'].items()}
                            p_name = inv_map.get(item['measurementPointId'], str(item['measurementPointId']))
                            p_clean = p_name.split('(')[0].strip()
                            col = f"{p_clean} | 15m LAeq"
                            if item.get('data') and item['data'].get('values'):
                                tmp_df[col] = item['data']['values']
                        tmp_df.set_index('Date', inplace=True)
                        dfs.append(tmp_df)
            except Exception as e:
                st.error(f"Erreur 15m : {e}")

        progress_bar.progress(90, text="Fusion des données...")

        # --- FUSION ---
        if dfs:
            final_df = dfs[0]
            for d in dfs[1:]:
                final_df = final_df.join(d, how='outer')
            
            final_df.reset_index(inplace=True)
            final_df.sort_values('Date', inplace=True)
            st.session_state['data_cache'] = final_df
            progress_bar.empty()
            st.success("Extraction terminée !")
        else:
            progress_bar.empty()
            st.warning("Aucune donnée reçue (Capteurs éteints ou période vide).")

# --- AFFICHAGE RESULTATS ---
if st.session_state['data_cache'] is not None:
    df = st.session_state['data_cache']
    
    st.markdown("### 📊 Analyse Graphique")
    
    # Graphique Plotly
    fig = px.line(df, x='Date', y=df.columns[1:], height=650)
    fig.update_layout(
        xaxis_title="Temps", yaxis_title="Niveau (dB)",
        legend_title="Indicateurs (Cliquer pour masquer)",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    c_tab, c_dl = st.columns([3, 1])
    with c_tab:
        st.markdown("### 📋 Données Brutes")
        st.dataframe(df, use_container_width=True, height=300)
    with c_dl:
        st.write("")
        st.write("")
        st.write("### 📥 Export")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Télécharger en CSV",
            data=csv,
            file_name=f"Cadence_Export.csv",
            mime="text/csv",
            type="primary"
        )
