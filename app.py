import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Cadence Custom Dashboard", page_icon="📈", layout="wide")

st.title("📈 Cadence Data Visualizer")
st.markdown("Interface de sélection fine et visualisation graphique interactive.")

# --- FONCTION DE RÉCUPÉRATION DES NOMS ---
@st.cache_data(ttl=3600)
def get_project_mps_names(api_key, proj_id):
    if len(api_key) < 5: return {}
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{proj_id}"
    headers = {"accept": "application/json", "X-API-KEY": api_key}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Retourne un dict {ID: "Nom (ID)"}
            return {mp['id']: f"{mp['name']} ({mp['id']})" for mp in data.get('measurementPoints', [])}
    except:
        pass
    return {}

# --- INITIALISATION VARIABLES ---
if 'data_cache' not in st.session_state:
    st.session_state['data_cache'] = None

# --- BARRE LATÉRALE (CONFIGURATION) ---
with st.sidebar:
    st.header("1. Connexion")
    api_key = st.text_input("Clé API", type="password", help="Ta clé EZfX...")
    project_id = st.number_input("ID Projet", value=1931, step=1)
    
    st.divider()
    
    st.header("2. Sélection des Points")
    # Chargement dynamique des noms
    mp_dict = {}
    if api_key:
        with st.spinner("Chargement des points..."):
            mp_dict = get_project_mps_names(api_key, project_id)
    
    # Si l'API échoue ou pas de clé, on met des défauts pour éviter le plantage
    if not mp_dict:
        mp_dict = {3440: "Point 3440 (Défaut)", 3441: "Point 3441 (Défaut)"}
        
    # Multiselect (Cocher les points)
    selected_mp_names = st.multiselect(
        "Points de mesure",
        options=list(mp_dict.values()),
        default=list(mp_dict.values()) # Tout coché par défaut
    )
    # Conversion Noms -> IDs
    selected_mp_ids = [id for id, name in mp_dict.items() if name in selected_mp_names]

    st.divider()

    st.header("3. Période (Journées entières)")
    # Dates fixes demandées
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        # Date de début par défaut au 21 Janvier comme demandé
        default_start = date(2025, 1, 21) 
        start_date = st.date_input("Du (00:00)", default_start)
    with col_d2:
        end_date = st.date_input("Au (23:59)", date.today())

    st.divider()

    st.header("4. Indicateurs à récupérer")
    st.caption("Cochez les données souhaitées :")
    
    # Cases à cocher individuelles
    check_h_laeq = st.checkbox("Hourly - LAeq", value=True)
    check_h_max = st.checkbox("Hourly - LAFMax", value=True)
    check_h_min = st.checkbox("Hourly - LAFMin", value=False)
    check_15_laeq = st.checkbox("15 min - LAeq", value=True)

    # Bouton de validation principal
    btn_validate = st.button("✅ VALIDER ET AFFICHER", type="primary")

# --- LOGIQUE PRINCIPALE ---
if btn_validate:
    if not api_key:
        st.error("⚠️ Merci de renseigner la Clé API.")
    elif not selected_mp_ids:
        st.error("⚠️ Veuillez cocher au moins un point de mesure.")
    elif not (check_h_laeq or check_h_max or check_h_min or check_15_laeq):
        st.error("⚠️ Veuillez cocher au moins un indicateur.")
    else:
        # Préparation des requêtes
        headers = {"accept": "application/json", "Content-Type": "application/json", "X-API-KEY": api_key}
        url_data = f"https://cadence.acoem.com/cloud-api/v1/projects/{project_id}/data"
        
        # Dates format ISO complet pour journées entières
        start_iso = f"{start_date}T00:00:00Z"
        end_iso = f"{end_date}T23:59:59Z"

        # Liste pour stocker les DataFrames partiels
        dfs_to_merge = []

        # --- REQUÊTE 1 : INDICATEURS HORAIRES (3600s) ---
        indicators_1h = []
        if check_h_laeq: indicators_1h.append(("LAeq", "average"))
        if check_h_max:  indicators_1h.append(("LAFMax", "max"))
        if check_h_min:  indicators_1h.append(("LAFMin", "min"))

        if indicators_1h:
            payload_inds = []
            for mp in selected_mp_ids:
                for ind_name, agg_method in indicators_1h:
                    payload_inds.append({
                        "measurementPointId": mp,
                        "primaryData": ind_name,
                        "timeFrequency": "global",
                        "aggregationMethod": agg_method,
                        "precision": 1
                    })
            
            payload_1h = {
                "start": start_iso, "end": end_iso, "aggregationTime": 3600,
                "indicators": payload_inds
            }
            
            with st.spinner("Récupération des données horaires..."):
                try:
                    r = requests.post(url_data, headers=headers, json=payload_1h)
                    if r.status_code == 200:
                        d = r.json()
                        if d.get('timestamp'):
                            df_temp = pd.DataFrame({'Date': pd.to_datetime(d['timestamp'])})
                            for item in d['indicators']:
                                mp_label = mp_dict.get(item['measurementPointId'], str(item['measurementPointId']))
                                col_name = f"{mp_label} | 1h {item['primaryData']}"
                                if item.get('data') and item['data'].get('values'):
                                    df_temp[col_name] = item['data']['values']
                            # Set Index pour le merge futur
                            df_temp.set_index('Date', inplace=True)
                            dfs_to_merge.append(df_temp)
                except Exception as e:
                    st.error(f"Erreur 1h: {e}")

        # --- REQUÊTE 2 : INDICATEURS 15 MIN (900s) ---
        if check_15_laeq:
            payload_inds_15 = []
            for mp in selected_mp_ids:
                payload_inds_15.append({
                    "measurementPointId": mp,
                    "primaryData": "LAeq",
                    "timeFrequency": "global",
                    "aggregationMethod": "average",
                    "precision": 1
                })
            
            payload_15m = {
                "start": start_iso, "end": end_iso, "aggregationTime": 900,
                "indicators": payload_inds_15
            }
            
            with st.spinner("Récupération des données 15 minutes..."):
                try:
                    r = requests.post(url_data, headers=headers, json=payload_15m)
                    if r.status_code == 200:
                        d = r.json()
                        if d.get('timestamp'):
                            df_temp = pd.DataFrame({'Date': pd.to_datetime(d['timestamp'])})
                            for item in d['indicators']:
                                mp_label = mp_dict.get(item['measurementPointId'], str(item['measurementPointId']))
                                col_name = f"{mp_label} | 15m LAeq"
                                if item.get('data') and item['data'].get('values'):
                                    df_temp[col_name] = item['data']['values']
                            df_temp.set_index('Date', inplace=True)
                            dfs_to_merge.append(df_temp)
                except Exception as e:
                    st.error(f"Erreur 15m: {e}")

        # --- FUSION ET AFFICHAGE ---
        if dfs_to_merge:
            # Fusionner tous les DF sur l'index de date (outer join pour garder toutes les lignes)
            final_df = dfs_to_merge[0]
            for df in dfs_to_merge[1:]:
                final_df = final_df.join(df, how='outer')
            
            # Reset index pour avoir la date en colonne
            final_df.reset_index(inplace=True)
            final_df.sort_values('Date', inplace=True)
            
            # Stockage en session state
            st.session_state['data_cache'] = final_df
            st.success("Données récupérées !")
        else:
            st.warning("Aucune donnée retournée par l'API.")

# --- AFFICHAGE DES RÉSULTATS (SI DONNÉES EN CACHE) ---
if st.session_state['data_cache'] is not None:
    df = st.session_state['data_cache']
    
    # 1. GRAPHIQUE INTERACTIF (PLOTLY)
    st.subheader("📊 Visualisation Graphique")
    st.caption("Cliquez sur les légendes ci-dessous pour masquer/afficher des courbes. Double-cliquez pour isoler une courbe.")
    
    # Création du graph
    fig = px.line(
        df, 
        x='Date', 
        y=df.columns[1:], # Toutes les colonnes sauf Date
        title=f"Évolution des Niveaux Sonores (Projet {project_id})",
        labels={"value": "Niveau (dB)", "variable": "Indicateur"},
        height=600
    )
    # Personnalisation (Tooltips, axes)
    fig.update_traces(mode="lines", hovertemplate='%{y:.1f} dB<br>%{x}')
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1))
    
    st.plotly_chart(fig, use_container_width=True)

    # 2. TABLEAU DE DONNÉES
    st.divider()
    st.subheader("📋 Tableau de Données")
    st.dataframe(df, use_container_width=True)
    
    # BOUTON DOWNLOAD
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Télécharger toutes les données (CSV)",
        csv,
        f"Export_Cadence_{date.today()}.csv",
        "text/csv",
        type="primary"
    )
