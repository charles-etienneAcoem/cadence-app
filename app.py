import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, time, timedelta
import itertools
import re

# --- ASSETS ---
ACOEM_LOGO_NEW = "https://cdn.bfldr.com/Q3Z2TZY7/at/b4z3s28jpswp92h6z35h9f3/ACOEM-LOGO-WithoutBaseline-RGB-Bicolor.jpg?auto=webp&format=jpg"
ACOEM_COLORS = ['#ff6952', '#2c5078', '#96c8de', '#FFB000', '#50C878', '#808080', '#000000']

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Cadence Data", page_icon=ACOEM_LOGO_NEW, layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 1rem; }
        .logo-container { background-color: white; padding: 12px; border-radius: 6px; display: flex; justify-content: center; align-items: center; margin-bottom: 20px; }
        .streamlit-expanderHeader { font-size: 1rem; font-weight: bold; color: #ff6952; }
        .project-detected { color: #50C878; font-size: 0.85rem; font-weight: bold; margin-top: -10px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'df_1h' not in st.session_state: st.session_state['df_1h'] = None
if 'df_15m' not in st.session_state: st.session_state['df_15m'] = None
if 'df_alerts' not in st.session_state: st.session_state['df_alerts'] = None
if 'has_run' not in st.session_state: st.session_state['has_run'] = False
if 'messages' not in st.session_state: st.session_state['messages'] = []

# --- TRANSLATIONS ---
translations = {
    "Français": {
        "auth_title": "🔐 1. Authentification", "api_key": "Clé API", "api_help": "Commence par EZfX...",
        "target_title": "🎯 2. Cible", "proj_id": "ID du Projet", "dash_id": "ID du Dashboard (Alertes)",
        "points": "IDs des Points", "points_help": "Ex: 1797, 1798",
        "settings_title": "⚙️ 3. Paramètres", "metrics": "Sélection des Métriques :",
        "hourly": "Par Heure (1h)", "short": "Court (15min)", "time_range": "Période :",
        "limit_db": "Ligne de limite (dB) (0 = désactivé):",
        "start": "Début", "end": "Fin", "btn_load": "🚀 CHARGER LES DONNÉES", "dashboard_title": "Tableau de Bord",
        "tab_1h": "⏱️ Données (1h)", "tab_15m": "⚡ Données (15min)", "tab_alerts": "🚨 Alertes",
        "no_data": "Aucune donnée trouvée pour ces filtres.", "data_table": "Tableau de Données",
        "rows": "lignes", "export": "📥 Exporter en CSV", "missing_key": "⚠️ Clé API manquante",
        "invalid_points": "⚠️ Format des IDs de points invalide", "analyzing": "🔍 Analyse de {} points...",
        "fetching": "Récupération des données...", "no_alerts": "Aucune alerte trouvée pour cette période (Vérifiez le Dashboard ID).",
        "unknown": "Inconnu", "status_summary": "### 📊 Résumé des statuts", "total_alerts": "Total des alertes",
        "val_alerts": "✅ Validées", "unval_alerts": "⏳ Non Validées", "open_alerts": "🚨 Ouvertes (à traiter)",
        "chart_title_1": "#### Nombre d'alertes par Point et Type", "chart_title_2": "#### Sources Identifiées (IA)",
        "no_ident": "Aucune alerte identifiée.", "no_source_info": "Aucune information de source.",
        "raw_data": "### 📋 Données Brutes", "api_empty": "L'API n'a renvoyé aucune donnée. Vérifiez les dates ou les IDs.",
        "tab_ai": "🤖 Assistant IA", "chat_placeholder": "Demandez-moi quelque chose sur vos appareils...",
        "ai_welcome": "Bonjour ! Je suis l'assistant IA de Cadence. Posez-moi des questions sur le projet ou demandez-moi d'analyser les alertes."
    },
    "Español": {
        "auth_title": "🔐 1. Autenticación", "api_key": "Clave API", "api_help": "Empieza con EZfX...",
        "target_title": "🎯 2. Objetivo", "proj_id": "ID del Proyecto", "dash_id": "ID del Dashboard (Alertas)",
        "points": "IDs de los Puntos", "points_help": "Ej: 1797, 1798",
        "settings_title": "⚙️ 3. Configuración", "metrics": "Selección de Métricas:",
        "hourly": "Por Hora (1h)", "short": "Corto (15min)", "time_range": "Rango de Tiempo:",
        "limit_db": "Línea de límite (dB) (0 = desactivado):",
        "start": "Inicio", "end": "Fin", "btn_load": "🚀 CARGAR DATOS", "dashboard_title": "Dashboard de Datos",
        "tab_1h": "⏱️ Datos (1h)", "tab_15m": "⚡ Datos (15min)", "tab_alerts": "🚨 Alertas",
        "no_data": "No se encontraron datos para los filtros seleccionados.", "data_table": "Tabla de Datos",
        "rows": "filas", "export": "📥 Exportar CSV", "missing_key": "⚠️ Falta la Clave API",
        "invalid_points": "⚠️ Formato de IDs de Puntos inválido", "analyzing": "🔍 Analizando {} puntos...",
        "fetching": "Obteniendo datos de la API...", "no_alerts": "No se encontraron alertas (Compruebe el Dashboard ID).",
        "unknown": "Desconocido", "status_summary": "### 📊 Resumen de estados", "total_alerts": "Total de alertas",
        "val_alerts": "✅ Validadas", "unval_alerts": "⏳ No Validadas", "open_alerts": "🚨 Abiertas (a tratar)",
        "chart_title_1": "#### Número de alertas por Punto y Tipo", "chart_title_2": "#### Fuentes Identificadas (IA)",
        "no_ident": "Ninguna alerta identificada.", "no_source_info": "Sin información de fuente.",
        "raw_data": "### 📋 Datos Brutos", "api_empty": "La API no devolvió datos. Comprueba las fechas o los IDs.",
        "tab_ai": "🤖 Asistente IA", "chat_placeholder": "Pregúntame algo sobre tus dispositivos...",
        "ai_welcome": "¡Hola! Soy tu asistente Cadence. Puedo analizar tus alertas o extraer datos específicos. ¿Qué quieres saber?"
    },
    "Català": {
        "auth_title": "🔐 1. Autenticació", "api_key": "Clau API", "api_help": "Comença amb EZfX...",
        "target_title": "🎯 2. Objectiu", "proj_id": "ID del Projecte", "dash_id": "ID del Dashboard (Alertes)",
        "points": "IDs dels Punts", "points_help": "Ex: 1797, 1798",
        "settings_title": "⚙️ 3. Configuració", "metrics": "Selecció de Mètriques:",
        "hourly": "Per Hora (1h)", "short": "Curt (15min)", "time_range": "Rang de Temps:",
        "limit_db": "Línia de límit (dB) (0 = desactivat):",
        "start": "Inici", "end": "Fi", "btn_load": "🚀 CARREGAR DADES", "dashboard_title": "Dashboard de Dades",
        "tab_1h": "⏱️ Dades (1h)", "tab_15m": "⚡ Dades (15min)", "tab_alerts": "🚨 Alertes",
        "no_data": "No s'han trobat dades per als filtres seleccionats.", "data_table": "Taula de Dades",
        "rows": "files", "export": "📥 Exportar CSV", "missing_key": "⚠️ Falta la Clau API",
        "invalid_points": "⚠️ Format d'IDs de Punts invàlid", "analyzing": "🔍 Analitzant {} punts...",
        "fetching": "Obtenint dades de l'API...", "no_alerts": "No s'han trobat alertes (Comproveu el Dashboard ID).",
        "unknown": "Desconegut", "status_summary": "### 📊 Resum d'estats", "total_alerts": "Total d'alertes",
        "val_alerts": "✅ Validades", "unval_alerts": "⏳ No Validades", "open_alerts": "🚨 Obertes (a tractar)",
        "chart_title_1": "#### Nombre d'alertes per Punt i Tipus", "chart_title_2": "#### Fonts Identificades (IA)",
        "no_ident": "Cap alerta identificada.", "no_source_info": "Sense informació de font.",
        "raw_data": "### 📋 Dades Brutes", "api_empty": "L'API no ha retornat dades. Comprova les dates o els IDs.",
        "tab_ai": "🤖 Assistent IA", "chat_placeholder": "Pregunta'm alguna cosa sobre els teus dispositius...",
        "ai_welcome": "Hola! Soc el teu assistent Cadence. Puc analitzar les teves alertes o extreure dades. Què vols saber?"
    }
}

# --- HELPER FUNCTIONS ---
@st.cache_data(ttl=3600)
def get_project_name(api_key, proj_id):
    if not api_key: return None
    try:
        r = requests.get(f"https://cadence.acoem.com/cloud-api/v1/projects/{proj_id}", headers={"accept": "application/json", "X-API-KEY": api_key}, timeout=3)
        if r.status_code == 200: return r.json().get('name', None)
    except: pass
    return None

def get_cadence_data(api_key, proj_id, mp_ids, start_date, end_date, agg_time, selected_labels, ref_indicators):
    dt_start = datetime.combine(start_date, time.min)
    dt_end = datetime.combine(end_date + timedelta(days=1), time.min)
    indicators_payload = [{"measurementPointId": mp, "primaryData": ind["code"], "aggregationMethod": ind["method"], "timeFrequency": "global", "frequencyBand": None, "axis": None, "precision": 1} for mp in mp_ids for ind in ref_indicators if ind["label"] in selected_labels]
    if not indicators_payload: return None

    payload = {"start": f"{start_date}T00:00:00Z", "end": f"{end_date}T23:59:59Z", "aggregationTime": agg_time, "indicators": indicators_payload}
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{proj_id}/data/getQuality"
    try:
        r = requests.post(url, headers={"accept": "application/json", "Content-Type": "application/json", "X-API-KEY": api_key}, json=payload)
        if r.status_code == 200:
            data = r.json()
            if not data.get('timeStamp'): return None
            time_index = pd.to_datetime(data['timeStamp']).tz_localize(None) 
            df = pd.DataFrame(index=time_index)
            df.index.name = 'Date'
            
            for item in data.get('indicators', []):
                mp_label = str(item.get('measurementPointId'))
                if 'measurementPoint' in item:
                    mp_label = item['measurementPoint'].get('measurementPointShortName') or item['measurementPoint'].get('measurementPointName') or mp_label
                dtype = item.get('primaryData', 'Val')
                if 'indicatorDescription' in item: dtype = item['indicatorDescription'].get('primaryData', dtype)
                
                col_name = f"{mp_label} | {dtype}"
                raw_vals = item.get('data', {}).get('values')
                if raw_vals:
                    vals = raw_vals[0] if (isinstance(raw_vals, list) and len(raw_vals)>0 and isinstance(raw_vals[0], list)) else raw_vals
                    try: df[col_name] = pd.Series(vals, index=time_index)
                    except: 
                        if len(vals) == len(df): df[col_name] = vals
            
            df = df.loc[(df.index >= dt_start) & (df.index < dt_end)].copy()
            return df if not df.empty else None
    except Exception as e:
        st.error(f"API Fetch Error: {e}")
    return None

def get_cadence_alerts(api_key, dash_id, start_date, end_date):
    url = "https://cadence.acoem.com/cloud-api/v1/x/environment_alerts/_search"
    headers = {"accept": "application/json", "Content-Type": "application/json", "X-API-KEY": api_key}
    all_alerts = []
    offset = 0
    limit = 50
    
    while True:
        payload = {"offset": offset, "limit": limit, "dashboardId": dash_id, "startDateUtc": f"{start_date}T00:00:00Z", "endDateUtc": f"{end_date}T23:59:59Z"}
        try:
            r = requests.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                data = r.json()
                if not data: break
                all_alerts.extend(data)
                offset += len(data)
                if len(data) < limit: break
            else: break
        except: break
            
    return pd.json_normalize(all_alerts) if all_alerts else None


# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"""<div class="logo-container"><img src="{ACOEM_LOGO_NEW}" style="width: 100%; max-width: 160px;"></div>""", unsafe_allow_html=True)
    lang = st.selectbox("Idioma / Langue / Llengua", ["Français", "Español", "Català"])
    t = translations[lang]
    st.divider()
    
    with st.expander(t["auth_title"], expanded=True):
        api_key = st.text_input(t["api_key"], type="password", help=t["api_help"])

    with st.expander(t["target_title"], expanded=True):
        project_id = st.number_input(t["proj_id"], value=689, step=1)
        dashboard_id = st.number_input(t["dash_id"], value=1, step=1)
        display_name = f"Project #{project_id}"
        if api_key:
            fetched_name = get_project_name(api_key, project_id)
            if fetched_name:
                display_name = fetched_name
                st.markdown(f"<div class='project-detected'>✅ {fetched_name}</div>", unsafe_allow_html=True)
        mps_input = st.text_input(t["points"], value="1797, 1798", help=t["points_help"])

    with st.expander(t["settings_title"], expanded=True):
        STD_INDICATORS = [{"label": "LAeq (Avg)", "code": "LAeq", "method": "average"}, {"label": "LAFMax (Max)", "code": "LAFMax", "method": "max"}, {"label": "LAFMin (Min)", "code": "LAFMin", "method": "min"}, {"label": "LCpeak (Max)", "code": "LCpeak", "method": "max"}, {"label": "Lden (Avg)", "code": "Lden", "method": "average"}]
        selected_inds_1h = st.multiselect(t["hourly"], [i["label"] for i in STD_INDICATORS], default=["LAeq (Avg)", "LAFMax (Max)"])
        selected_inds_15m = st.multiselect(t["short"], [i["label"] for i in STD_INDICATORS], default=["LAeq (Avg)"])
        
        limit_db_val = st.number_input(t["limit_db"], value=85.0, step=1.0)
        
        col_d1, col_d2 = st.columns(2)
        d_start = col_d1.date_input(t["start"], date.today() - timedelta(days=1))
        d_end = col_d2.date_input(t["end"], date.today())

    st.markdown("")
    btn_run = st.button(t["btn_load"], type="primary", use_container_width=True)


# --- MAIN UI Logic ---
st.title(f"{display_name} - {t['dashboard_title']}")

if btn_run:
    if not api_key: st.error(t["missing_key"]); st.stop()
    try: 
        mp_ids_list = [int(x) for x in re.split(r'[ ,;]+', mps_input) if x.strip()]
        if not mp_ids_list: raise ValueError
    except: st.error(t["invalid_points"]); st.stop()
    
    st.session_state['has_run'] = True
    
    with st.spinner(t["fetching"]):
        st.session_state['df_1h'] = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 3600, selected_inds_1h, STD_INDICATORS) if selected_inds_1h else None
        st.session_state['df_15m'] = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 900, selected_inds_15m, STD_INDICATORS) if selected_inds_15m else None
        st.session_state['df_alerts'] = get_cadence_alerts(api_key, dashboard_id, d_start, d_end)


# --- RENDERING FUNCTIONS ---
def render_dashboard(df, title_suffix, limit_val):
    if df is None or df.empty:
        st.warning(t["no_data"])
        return

    col_graph, col_table = st.columns([1, 1])
    with col_graph:
        fig = go.Figure()
        colors = itertools.cycle(ACOEM_COLORS)
        for col in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col, line=dict(width=2, color=next(colors))))
        
        # AJOUT DE LA LIGNE LIMITE SI > 0
        if limit_val > 0:
            fig.add_hline(y=limit_val, line_dash="dash", line_color="#ff6952", annotation_text=f"{limit_val} dB", annotation_position="top left")

        fig.update_layout(
            title=f"{title_suffix}", xaxis_title="Time", yaxis_title="Level (dB)",
            height=500, margin=dict(l=20, r=20, t=40, b=20),
            template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", y=1.1), hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_table:
        st.markdown(f"**{t['data_table']}** ({len(df)} {t['rows']})")
        st.download_button(label=t["export"], data=df.to_csv().encode('utf-8'), file_name=f"Cadence_{title_suffix}_{project_id}.csv", mime="text/csv", key=f"dl_btn_{title_suffix}", type="primary", use_container_width=True)
        st.dataframe(df.astype(str), height=450, use_container_width=True)


def render_alerts(df):
    if df is None or df.empty:
        st.warning(t["no_alerts"])
        return
        
    df_clean = df.copy()
    point_col = 'data.measurePointData.name'
    if point_col not in df.columns:
        point_col = 'data.measurePointName' if 'data.measurePointName' in df.columns else 'deviceEventId'
            
    df_clean['Point'] = df_clean[point_col].fillna(t["unknown"]) if point_col in df_clean.columns else t["unknown"]
    df_clean['Type'] = df_clean['type'].fillna(t["unknown"]) if 'type' in df_clean.columns else t["unknown"]
    
    total_alerts = len(df_clean)
    nb_validated = df_clean['validated'].fillna(False).astype(bool).sum() if 'validated' in df_clean.columns else "N/A"
    nb_unvalidated = (total_alerts - nb_validated) if isinstance(nb_validated, int) else "N/A"
    nb_open = (~df_clean['closed'].fillna(False).astype(bool)).sum() if 'closed' in df_clean.columns else "N/A"

    st.markdown(t["status_summary"])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t["total_alerts"], total_alerts)
    m2.metric(t["val_alerts"], nb_validated)
    m3.metric(t["unval_alerts"], nb_unvalidated)
    m4.metric(t["open_alerts"], nb_open)
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(t["chart_title_1"])
        summary = df_clean.groupby(['Point', 'Type']).size().reset_index(name='Count')
        fig_bar = go.Figure()
        for type_alert in summary['Type'].unique():
            df_t = summary[summary['Type'] == type_alert]
            fig_bar.add_trace(go.Bar(x=df_t['Point'], y=df_t['Count'], name=type_alert))
        fig_bar.update_layout(barmode='stack', template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col2:
        st.markdown(t["chart_title_2"])
        if 'identified' in df_clean.columns and 'sourceRecognitionId' in df_clean.columns:
            df_ident = df_clean[df_clean['identified'].fillna(False).astype(bool) == True].copy()
            if not df_ident.empty:
                source_col = 'sourceRecognitionId'
                df_ident[source_col] = df_ident[source_col].replace({None: t["unknown"], '': t["unknown"], float('nan'): t["unknown"]})
                pie_data = df_ident.groupby(source_col).size().reset_index(name='Count')
                fig_pie = go.Figure(data=[go.Pie(labels=pie_data[source_col], values=pie_data['Count'], hole=.4, marker=dict(colors=ACOEM_COLORS))])
                fig_pie.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig_pie, use_container_width=True)
            else: st.info(t["no_ident"])
        else: st.warning(t["no_source_info"])
        
    st.divider()
    st.markdown(t["raw_data"])
    st.dataframe(df_clean.astype(str), use_container_width=True)


def process_local_query(prompt, lang):
    """Analyse la question et cherche dans les données chargées en session state."""
    prompt_low = prompt.lower()
    response = ""
    
    df_1h = st.session_state.get('df_1h')
    df_15m = st.session_state.get('df_15m')
    df_alerts = st.session_state.get('df_alerts')
    
    # 1. Recherche d'alertes ou d'événements
    if any(w in prompt_low for w in ["alerte", "alert", "évènement", "événement", "event"]):
        if df_alerts is not None and not df_alerts.empty:
            response += f"🚨 **Analyse des alertes :** J'ai trouvé **{len(df_alerts)}** événement(s) sur cette période.\n\n"
        else:
            response += "✅ **Analyse des alertes :** Aucune alerte n'a été chargée ou trouvée pour le moment.\n\n"
            
    # 2. Recherche de Max, Min, Moyenne (Utilise df_15m en priorité car plus précis, sinon df_1h)
    df_data = df_15m if df_15m is not None and not df_15m.empty else df_1h
    
    if df_data is not None and not df_data.empty:
        # On s'assure de ne traiter que les colonnes avec des chiffres (pour éviter les crashs)
        try:
            df_num = df_data.apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all')
            
            if not df_num.empty:
                if "max" in prompt_low:
                    response += "📈 **Valeurs Maximales enregistrées :**\n"
                    for col in df_num.columns:
                        response += f"- {col} : **{df_num[col].max():.1f} dB**\n"
                    response += "\n"
                    
                if "min" in prompt_low:
                    response += "📉 **Valeurs Minimales enregistrées :**\n"
                    for col in df_num.columns:
                        response += f"- {col} : **{df_num[col].min():.1f} dB**\n"
                    response += "\n"
                    
                if any(w in prompt_low for w in ["moyen", "avg", "average", "mitjana"]):
                    response += "📏 **Moyennes sur la période :**\n"
                    for col in df_num.columns:
                        response += f"- {col} : **{df_num[col].mean():.1f} dB**\n"
                    response += "\n"
        except Exception as e:
            response += "⚠️ Une erreur est survenue lors de l'analyse mathématique des colonnes.\n"
    else:
        # Si on demande des calculs mais que rien n'est chargé
        if any(w in prompt_low for w in ["max", "min", "moyen", "avg"]):
            response += "⚠️ Vous devez d'abord charger les données (cliquez sur '🚀 CHARGER LES DONNÉES') pour que je puisse calculer les niveaux.\n\n"
            
    # Fallback : Si l'utilisateur tape une phrase sans mots-clés connus
    if not response:
        response = "🤖 *Je suis un moteur de recherche interne (sans IA externe).* Je parcours les données que vous avez chargées. Essayez de me demander :\n- 'Combien d'**alertes** y a-t-il ?'\n- 'Quel est le **max** ?'\n- 'Donne moi la **moyenne**'\n- 'Quel est le **min** ?'"
        
    return response


def render_chat_agent(api_key, proj_id):
    st.markdown(f"### {t['tab_ai']}")
    
    # Message de bienvenue
    if not st.session_state['messages']:
        st.session_state['messages'].append({"role": "assistant", "content": t["ai_welcome"]})

    # Affichage de l'historique
    for message in st.session_state['messages']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Zone de saisie
    if prompt := st.chat_input(t["chat_placeholder"]):
        
        # 1. Affiche le message de l'utilisateur
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state['messages'].append({"role": "user", "content": prompt})

        # 2. L'assistant local analyse la demande
        with st.chat_message("assistant"):
            with st.spinner("Analyse locale des données en cours..."):
                # On appelle notre nouvelle fonction locale
                response = process_local_query(prompt, lang)
                st.markdown(response)
        
        st.session_state['messages'].append({"role": "assistant", "content": response})
        # --- DISPLAY TABS (If we have run at least once) ---
if st.session_state['has_run']:
    if st.session_state['df_1h'] is None and st.session_state['df_15m'] is None and st.session_state['df_alerts'] is None:
        st.error(t["api_empty"])
    else:
        # On ajoute t4 pour le chat
        t1, t2, t3, t4 = st.tabs([t["tab_1h"], t["tab_15m"], t["tab_alerts"], t["tab_ai"]])
        
        with t1: render_dashboard(st.session_state['df_1h'], t["hourly"], limit_db_val)
        with t2: render_dashboard(st.session_state['df_15m'], t["short"], limit_db_val)
        with t3: render_alerts(st.session_state['df_alerts'])
        
        # Appel de l'assistant IA dans le 4ème onglet
        with t4: render_chat_agent(api_key, project_id)
else:
    if lang == 'Français': msg = "👈 Ouvrez les sections de la barre latérale pour configurer et charger les données."
    elif lang == 'Español': msg = "👈 Abre las secciones en la barra lateral para configurar y cargar datos."
    else: msg = "👈 Obre les seccions a la barra lateral per configurar i carregar dades."
    st.info(msg)
