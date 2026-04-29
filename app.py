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
st.set_page_config(
    page_title="Cadence Data", 
    page_icon=ACOEM_LOGO_NEW, 
    layout="wide"
)

# --- 2. CSS CUSTOMIZATION ---
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 1rem; }
        [data-testid="stSidebarUserContent"] { padding-top: 1rem; }
        
        .logo-container {
            background-color: white; padding: 12px; border-radius: 6px;
            display: flex; justify-content: center; align-items: center; margin-bottom: 20px;
        }
        
        .streamlit-expanderHeader {
            font-size: 1rem; font-weight: bold; color: #ff6952;
        }
        
        .project-detected {
            color: #50C878; font-size: 0.85rem; font-weight: bold; margin-top: -10px; margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'df_1h' not in st.session_state: st.session_state['df_1h'] = None
if 'df_15m' not in st.session_state: st.session_state['df_15m'] = None
if 'df_alerts' not in st.session_state: st.session_state['df_alerts'] = None

# --- HELPER: GET PROJECT NAME ---
@st.cache_data(ttl=3600)
def get_project_name(api_key, proj_id):
    if not api_key: return None
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{proj_id}"
    headers = {"accept": "application/json", "X-API-KEY": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=2)
        if r.status_code == 200:
            return r.json().get('name', None)
    except:
        pass
    return None

# --- TRANSLATIONS ---
translations = {
    "Español": {
        "auth_title": "🔐 1. Autenticación",
        "api_key": "Clave API",
        "api_help": "Empieza con EZfX...",
        "target_title": "🎯 2. Objetivo",
        "proj_id": "ID del Proyecto",
        "dash_id": "ID del Dashboard (Para Alertas)",
        "points": "IDs de los Puntos",
        "points_help": "Ej: 1797, 1798",
        "settings_title": "⚙️ 3. Configuración",
        "metrics": "Selección de Métricas:",
        "hourly": "Por Hora (1h)",
        "short": "Corto (15min)",
        "time_range": "Rango de Tiempo:",
        "start": "Inicio",
        "end": "Fin",
        "btn_load": "🚀 CARGAR DATOS",
        "dashboard_title": "Dashboard de Datos",
        "tab_1h": "⏱️ Datos por Hora (1h)",
        "tab_15m": "⚡ Datos Cortos (15min)",
        "tab_alerts": "🚨 Alertas",
        "no_data": "No se obtuvieron datos.",
        "data_table": "Tabla de Datos",
        "rows": "filas",
        "export": "📥 Exportar CSV",
        "missing_key": "⚠️ Falta la Clave API",
        "invalid_points": "⚠️ Formato de IDs de Puntos inválido",
        "analyzing": "🔍 Analizando {} puntos...",
        "fetching": "Obteniendo datos de la nube...",
        "no_alerts": "No se encontraron alertas para este período.",
        "unknown": "Desconocido",
        "status_summary": "### 📊 Resumen de estados",
        "total_alerts": "Total de alertas",
        "val_alerts": "✅ Alertas Validadas",
        "unval_alerts": "⏳ No Validadas",
        "open_alerts": "🚨 Abiertas (a tratar)",
        "chart_title_1": "#### Número de alertas por Punto y Tipo",
        "chart_title_2": "#### Distribución de Fuentes Identificadas",
        "no_ident": "Ninguna alerta está marcada como identificada para generar el gráfico.",
        "no_source_info": "Información sobre la identificación de la fuente no disponible en estos datos.",
        "raw_data": "### 📋 Datos Brutos de las Alertas"
    },
    "Català": {
        "auth_title": "🔐 1. Autenticació",
        "api_key": "Clau API",
        "api_help": "Comença amb EZfX...",
        "target_title": "🎯 2. Objectiu",
        "proj_id": "ID del Projecte",
        "dash_id": "ID del Dashboard (Per a Alertes)",
        "points": "IDs dels Punts",
        "points_help": "Ex: 1797, 1798",
        "settings_title": "⚙️ 3. Configuració",
        "metrics": "Selecció de Mètriques:",
        "hourly": "Per Hora (1h)",
        "short": "Curt (15min)",
        "time_range": "Rang de Temps:",
        "start": "Inici",
        "end": "Fi",
        "btn_load": "🚀 CARREGAR DADES",
        "dashboard_title": "Dashboard de Dades",
        "tab_1h": "⏱️ Dades per Hora (1h)",
        "tab_15m": "⚡ Dades Curtes (15min)",
        "tab_alerts": "🚨 Alertes",
        "no_data": "No s'han obtingut dades.",
        "data_table": "Taula de Dades",
        "rows": "files",
        "export": "📥 Exportar CSV",
        "missing_key": "⚠️ Falta la Clau API",
        "invalid_points": "⚠️ Format d'IDs de Punts invàlid",
        "analyzing": "🔍 Analitzant {} punts...",
        "fetching": "Obtenint dades del núvol...",
        "no_alerts": "No s'han trobat alertes per a aquest període.",
        "unknown": "Desconegut",
        "status_summary": "### 📊 Resum d'estats",
        "total_alerts": "Total d'alertes",
        "val_alerts": "✅ Alertes Validades",
        "unval_alerts": "⏳ No Validades",
        "open_alerts": "🚨 Obertes (a tractar)",
        "chart_title_1": "#### Nombre d'alertes per Punt i Tipus",
        "chart_title_2": "#### Distribució de Fonts Identificades",
        "no_ident": "Cap alerta està marcada com a identificada per generar el gràfic.",
        "no_source_info": "Informació sobre la identificació de la font no disponible en aquestes dades.",
        "raw_data": "### 📋 Dades Brutes de les Alertes"
    }
}

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"""
        <div class="logo-container">
            <img src="{ACOEM_LOGO_NEW}" style="width: 100%; max-width: 160px;">
        </div>
    """, unsafe_allow_html=True)
    
    # LANGUAGE SELECTOR
    lang = st.selectbox("Idioma / Llengua", ["Español", "Català"])
    t = translations[lang]
    
    st.divider()
    
    # --- 1. AUTH ---
    with st.expander(t["auth_title"], expanded=True):
        api_key = st.text_input(t["api_key"], type="password", help=t["api_help"])

    # --- 2. TARGET ---
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

    # --- 3. SETTINGS ---
    with st.expander(t["settings_title"], expanded=True):
        STD_INDICATORS = [
            {"label": "LAeq (Avg)", "code": "LAeq", "method": "average"},
            {"label": "LAFMax (Max)", "code": "LAFMax", "method": "max"},
            {"label": "LAFMin (Min)", "code": "LAFMin", "method": "min"},
            {"label": "LCpeak (Max)", "code": "LCpeak", "method": "max"},
            {"label": "Lden (Avg)", "code": "Lden", "method": "average"}
        ]
        
        st.caption(t["metrics"])
        selected_inds_1h = st.multiselect(t["hourly"], [i["label"] for i in STD_INDICATORS], default=["LAeq (Avg)", "LAFMax (Max)"])
        selected_inds_15m = st.multiselect(t["short"], [i["label"] for i in STD_INDICATORS], default=["LAeq (Avg)"])
        
        st.divider()
        st.caption(t["time_range"])
        col_d1, col_d2 = st.columns(2)
        d_start = col_d1.date_input(t["start"], date.today())
        d_end = col_d2.date_input(t["end"], date.today())

    st.markdown("")
    btn_run = st.button(t["btn_load"], type="primary", use_container_width=True)

# --- MAIN TITLE ---
st.title(f"{display_name} - {t['dashboard_title']}")

# --- DATA FETCHING FUNCTIONS ---
def get_cadence_data(api_key, proj_id, mp_ids, start_date, end_date, agg_time, selected_labels, ref_indicators):
    dt_start = datetime.combine(start_date, time.min)
    dt_end = datetime.combine(end_date + timedelta(days=1), time.min)
    
    indicators_payload = []
    active_inds = [i for i in ref_indicators if i["label"] in selected_labels]
    
    for mp in mp_ids:
        for ind in active_inds:
            indicators_payload.append({
                "measurementPointId": mp, "primaryData": ind["code"],
                "aggregationMethod": ind["method"], "timeFrequency": "global",
                "frequencyBand": None, "axis": None, "precision": 1
            })

    if not indicators_payload: return None

    payload = {
        "start": f"{start_date}T00:00:00Z", "end": f"{end_date}T23:59:59Z",
        "aggregationTime": agg_time, "indicators": indicators_payload
    }
    
    headers = {"accept": "application/json", "Content-Type": "application/json", "X-API-KEY": api_key}
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{proj_id}/data/getQuality"
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            data = r.json()
            if not data.get('timeStamp'): return None
            
            time_index = pd.to_datetime(data['timeStamp'])
            time_index = time_index.tz_localize(None) 
            
            df = pd.DataFrame(index=time_index)
            df.index.name = 'Date'
            
            for item in data.get('indicators', []):
                mp_label = str(item.get('measurementPointId'))
                
                if 'measurementPoint' in item:
                    mp_obj = item['measurementPoint']
                    mp_label = mp_obj.get('measurementPointShortName') or mp_obj.get('measurementPointName') or mp_label
                
                dtype = item.get('primaryData', 'Val')
                if 'indicatorDescription' in item:
                    dtype = item['indicatorDescription'].get('primaryData', dtype)

                col_name = f"{mp_label} | {dtype}"
                
                raw_vals = item.get('data', {}).get('values')
                if raw_vals:
                    vals = raw_vals[0] if (isinstance(raw_vals, list) and len(raw_vals)>0 and isinstance(raw_vals[0], list)) else raw_vals
                    try:
                        series = pd.Series(vals, index=time_index)
                        df[col_name] = series
                    except:
                        if len(vals) == len(df): df[col_name] = vals

            mask = (df.index >= dt_start) & (df.index < dt_end)
            df = df.loc[mask].copy()
            
            if df.empty: return None
            return df
        else:
            st.error(f"API Error: {r.status_code} - {r.text}"); return None
    except Exception as e:
        st.error(f"Error: {e}"); return None

def get_cadence_alerts(api_key, dash_id, start_date, end_date):
    url = "https://cadence.acoem.com/cloud-api/v1/x/environment_alerts/_search"
    headers = {"accept": "application/json", "Content-Type": "application/json", "X-API-KEY": api_key}
    
    dt_start = f"{start_date}T00:00:00Z"
    dt_end = f"{end_date}T23:59:59Z"
    
    all_alerts = []
    offset = 0
    limit = 50
    
    while True:
        payload = {
            "offset": offset,
            "limit": limit,
            "dashboardId": dash_id,
            "startDateUtc": dt_start,
            "endDateUtc": dt_end
        }
        
        try:
            r = requests.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                data = r.json()
                if not data:
                    break
                all_alerts.extend(data)
                offset += len(data)
                
                if len(data) < limit:
                    break
            else:
                st.error(f"Alerts API Error: {r.status_code} - {r.text}")
                break
        except Exception as e:
            st.error(f"Error fetching alerts: {e}")
            break
            
    if not all_alerts:
        return None
        
    return pd.json_normalize(all_alerts)

# --- EXECUTION ---
if btn_run:
    if not api_key: st.error(t["missing_key"]); st.stop()
    
    try: 
        mp_ids_list = [int(x) for x in re.split(r'[ ,;]+', mps_input) if x.strip()]
        if not mp_ids_list: raise ValueError
    except: st.error(t["invalid_points"]); st.stop()
    
    st.success(t["analyzing"].format(len(mp_ids_list)))
        
    st.session_state['df_1h'] = None
    st.session_state['df_15m'] = None
    st.session_state['df_alerts'] = None
    
    with st.spinner(t["fetching"]):
        if selected_inds_1h:
            st.session_state['df_1h'] = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 3600, selected_inds_1h, STD_INDICATORS)
        if selected_inds_15m:
            st.session_state['df_15m'] = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 900, selected_inds_15m, STD_INDICATORS)
            
        st.session_state['df_alerts'] = get_cadence_alerts(api_key, dashboard_id, d_start, d_end)


# --- VISUALIZATION ---
if st.session_state['df_1h'] is not None or st.session_state['df_15m'] is not None or st.session_state['df_alerts'] is not None:
    
    t1, t2, t3 = st.tabs([t["tab_1h"], t["tab_15m"], t["tab_alerts"]])
    
    def render_dashboard(df, title_suffix):
        if df is None: st.info(t["no_data"]); return

        col_graph, col_table = st.columns([1, 1])
        
        with col_graph:
            fig = go.Figure()
            colors = itertools.cycle(ACOEM_COLORS)
            for col in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col, line=dict(width=2, color=next(colors))))
            
            x_min = datetime.combine(d_start, time.min)
            x_max = datetime.combine(d_end + timedelta(days=1), time.min)
            
            fig.update_layout(
                title=f"{title_suffix}",
                xaxis_title="Time", yaxis_title="Level (dB)",
                xaxis=dict(range=[x_min, x_max]), height=500,
                margin=dict(l=20, r=20, t=40, b=20),
                template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", y=1.1), hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            st.markdown(f"**{t['data_table']}** ({len(df)} {t['rows']})")
            csv = df.to_csv().encode('utf-8')
            unique_key = f"dl_btn_{title_suffix}"
            st.download_button(
                label=t["export"],
                data=csv,
                file_name=f"Cadence_{title_suffix}_{project_id}.csv",
                mime="text/csv",
                key=unique_key, 
                type="primary",
                use_container_width=True
            )
            st.dataframe(df, height=450, use_container_width=True)

    def render_alerts(df):
        if df is None or df.empty:
            st.info(t["no_alerts"])
            return
            
        df_clean = df.copy()
        
        # --- PREPARATION DES COLONNES ---
        point_col = 'data.measurePointData.name'
        if point_col not in df.columns:
            point_col = 'data.measurePointName' if 'data.measurePointName' in df.columns else 'deviceEventId'
                
        df_clean['Point'] = df_clean[point_col].fillna(t["unknown"]) if point_col in df_clean.columns else t["unknown"]
        df_clean['Type'] = df_clean['type'].fillna(t["unknown"]) if 'type' in df_clean.columns else t["unknown"]
        
        has_validated = 'validated' in df_clean.columns
        has_closed = 'closed' in df_clean.columns
        has_identified = 'identified' in df_clean.columns
        has_source = 'sourceRecognitionId' in df_clean.columns

        # --- CALCUL DES METRIQUES ---
        total_alerts = len(df_clean)
        
        if has_validated:
            nb_validated = df_clean['validated'].fillna(False).astype(bool).sum()
            nb_unvalidated = total_alerts - nb_validated
        else:
            nb_validated = "N/A"
            nb_unvalidated = "N/A"
            
        if has_closed:
            nb_open = (~df_clean['closed'].fillna(False).astype(bool)).sum()
        else:
            nb_open = "N/A"

        # --- AFFICHAGE DES COMPTEURS ---
        st.markdown(t["status_summary"])
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t["total_alerts"], total_alerts)
        m2.metric(t["val_alerts"], nb_validated)
        m3.metric(t["unval_alerts"], nb_unvalidated)
        m4.metric(t["open_alerts"], nb_open)
        
        st.divider()

        # --- GRAPHIQUES ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(t["chart_title_1"])
            summary = df_clean.groupby(['Point', 'Type']).size().reset_index(name='Count')
            fig_bar = go.Figure()
            for type_alert in summary['Type'].unique():
                df_t = summary[summary['Type'] == type_alert]
                fig_bar.add_trace(go.Bar(x=df_t['Point'], y=df_t['Count'], name=type_alert))
            
            fig_bar.update_layout(
                barmode='stack',
                template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col2:
            st.markdown(t["chart_title_2"])
            if has_identified and has_source:
                df_ident = df_clean[df_clean['identified'].fillna(False).astype(bool) == True].copy()
                
                if not df_ident.empty:
                    df_ident[has_source] = df_ident[has_source].replace({None: t["unknown"], '': t["unknown"], float('nan'): t["unknown"]})
                    pie_data = df_ident.groupby(has_source).size().reset_index(name='Count')
                    
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=pie_data[has_source], 
                        values=pie_data['Count'], 
                        hole=.4,
                        marker=dict(colors=ACOEM_COLORS)
                    )])
                    
                    fig_pie.update_layout(
                        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        legend=dict(orientation="h", y=1.1)
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info(t["no_ident"])
            else:
                st.warning(t["no_source_info"])
            
        st.divider()
        st.markdown(t["raw_data"])
        st.dataframe(df, use_container_width=True)

    with t1: render_dashboard(st.session_state['df_1h'], t["hourly"])
    with t2: render_dashboard(st.session_state['df_15m'], t["short"])
    with t3: render_alerts(st.session_state['df_alerts'])

else:
    lang = st.session_state.get('lang', 'Español')
    msg = "👈 Abre las secciones en la barra lateral para configurar y cargar datos." if lang == 'Español' else "👈 Obre les seccions a la barra lateral per configurar i carregar dades."
    st.info(msg)
