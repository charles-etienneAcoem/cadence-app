import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, time, timedelta
import itertools

# --- ASSETS ---
ACOEM_LOGO = "https://cdn.bfldr.com/Q3Z2TZY7/at/2rg3rwh4gcnrvn5gkh8rckpp/ACOEM-LOGO-Brandsymbol-RGB-Orange.png?auto=webp&format=png"
AECOM_LOGO = "https://zerionsoftware.com/wp-content/uploads/2023/10/aecom-logo.png"
ACOEM_COLORS = ['#ff6952', '#2c5078', '#96c8de', '#FFB000', '#50C878'] 

# --- 1. PAGE CONFIGURATION ---
# Titre de l'onglet et Favicon Acoem
st.set_page_config(
    page_title="Cadence Data", 
    page_icon=ACOEM_LOGO, 
    layout="wide"
)

# --- 2. CSS HACKS (COMPACT HEADER & SIDEBAR) ---
st.markdown("""
    <style>
        /* Réduire l'espace en haut de la page principale */
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        
        /* Réduire l'espace en haut de la sidebar */
        [data-testid="stSidebarUserContent"] { padding-top: 1rem; }
        
        /* Alignement des logos */
        .logo-container { display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 5px; }
        .powered-by { text-align: center; font-size: 0.8rem; font-weight: bold; color: #555; margin-bottom: 20px; }
        
        /* Ajustement des titres */
        h1 { font-size: 1.8rem !important; }
        h3 { font-size: 1.2rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'df_1h' not in st.session_state: st.session_state['df_1h'] = None
if 'df_15m' not in st.session_state: st.session_state['df_15m'] = None

# --- SIDEBAR ---
with st.sidebar:
    # --- HEADER BRANDING ---
    # Affichage des deux logos côte à côte
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.image(AECOM_LOGO, use_container_width=True)
    with col_l2:
        st.image(ACOEM_LOGO, use_container_width=True)
        
    st.markdown("<div class='powered-by'>AECOM powered by Acoem</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    # 1. AUTH
    api_key = st.text_input("API Key", type="password")
    project_id = st.number_input("Project ID", value=689, step=1)
    
    # 2. POINTS
    mps_input = st.text_input("Point IDs", value="1797", help="Ex: 1797, 1798")

    st.markdown("---")
    st.markdown("**📊 Indicators**")

    # STD INDICATORS LIST
    STD_INDICATORS = [
        {"label": "LAeq (Avg)", "code": "LAeq", "method": "average"},
        {"label": "LAFMax (Max)", "code": "LAFMax", "method": "max"},
        {"label": "LAFMin (Min)", "code": "LAFMin", "method": "min"},
        {"label": "LCpeak (Max)", "code": "LCpeak", "method": "max"},
        {"label": "Lden (Avg)", "code": "Lden", "method": "average"}
    ]
    
    # Selection 1H
    with st.expander("Hourly (1h)", expanded=True):
        selected_inds_1h = st.multiselect(
            "Select Metrics:", 
            options=[i["label"] for i in STD_INDICATORS],
            default=["LAeq (Avg)", "LAFMax (Max)"]
        )
    
    # Selection 15min
    with st.expander("Short (15min)", expanded=False):
        selected_inds_15m = st.multiselect(
            "Select Metrics:", 
            options=[i["label"] for i in STD_INDICATORS],
            default=["LAeq (Avg)"]
        )
        
    st.markdown("---")
    # Dates
    c_d1, c_d2 = st.columns(2)
    d_start = c_d1.date_input("Start", date(2025, 1, 21))
    d_end = c_d2.date_input("End", date.today())
    
    st.markdown("")
    btn_run = st.button("🚀 LOAD DATA", type="primary")

# --- MAIN PAGE TITLE ---
st.title(f"Project #{project_id} - Data Dashboard")

# --- CORE FUNCTION ---
def get_cadence_data(api_key, proj_id, mp_ids, start_date, end_date, agg_time, selected_labels, ref_indicators):
    """
    Fetches data dynamically based on user selection.
    Strictly clips time range.
    """
    dt_start = datetime.combine(start_date, time.min)
    dt_end = datetime.combine(end_date + timedelta(days=1), time.min)
    
    # 1. Build Dynamic Indicators List
    indicators_payload = []
    
    # Filter reference list based on user selection
    active_inds = [i for i in ref_indicators if i["label"] in selected_labels]
    
    for mp in mp_ids:
        for ind in active_inds:
            indicators_payload.append({
                "measurementPointId": mp,
                "primaryData": ind["code"],
                "aggregationMethod": ind["method"],
                "timeFrequency": "global",
                "frequencyBand": None,
                "axis": None,
                "precision": 1
            })

    if not indicators_payload:
        return None

    # API Request
    payload = {
        "start": f"{start_date}T00:00:00Z", "end": f"{end_date}T23:59:59Z",
        "aggregationTime": agg_time, "indicators": indicators_payload
    }
    
    headers = {"accept": "application/json", "Content-Type": "application/json", "X-API-KEY": api_key}
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{proj_id}/data"
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            data = r.json()
            if not data.get('timeStamp'): return None
            
            df = pd.DataFrame({'Date': pd.to_datetime(data['timeStamp'])})
            
            # Remove Timezone for strict comparison
            df['Date'] = df['Date'].dt.tz_localize(None)
            
            # Apply Strict Date Filter
            mask = (df['Date'] >= dt_start) & (df['Date'] < dt_end)
            
            # Parse Data
            for item in data.get('indicators', []):
                # Resolve Name
                mp_name = str(item.get('measurementPointId'))
                if 'measurementPoint' in item:
                    mp_name = item['measurementPoint'].get('measurementPointName', mp_name)
                elif 'measurementPointId' in item: # Fallback
                     mp_name = str(item['measurementPointId'])

                # Resolve Type
                dtype = item.get('primaryData', 'Val')
                if 'indicatorDescription' in item:
                    dtype = item['indicatorDescription'].get('primaryData', dtype)

                col_name = f"{mp_name} | {dtype}"
                
                # Extract Values
                raw_vals = item.get('data', {}).get('values')
                if raw_vals:
                    vals = raw_vals[0] if (isinstance(raw_vals, list) and len(raw_vals)>0 and isinstance(raw_vals[0], list)) else raw_vals
                    if len(vals) == len(df):
                        df[col_name] = vals

            # Filter Rows
            df = df.loc[mask].copy()
            if df.empty: return None
            
            df.set_index('Date', inplace=True)
            return df
        else:
            st.error(f"API Error: {r.status_code}")
            return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- EXECUTION ---
if btn_run:
    if not api_key:
        st.error("⚠️ Missing API Key")
        st.stop()
        
    try:
        mp_ids_list = [int(x.strip()) for x in mps_input.split(",") if x.strip()]
    except:
        st.error("⚠️ Invalid Point IDs")
        st.stop()
        
    # Clear old data
    st.session_state['df_1h'] = None
    st.session_state['df_15m'] = None
    
    with st.spinner("Fetching data from cloud..."):
        # 1. Fetch 1H
        if selected_inds_1h:
            st.session_state['df_1h'] = get_cadence_data(
                api_key, project_id, mp_ids_list, d_start, d_end, 3600, selected_inds_1h, STD_INDICATORS
            )
            
        # 2. Fetch 15m
        if selected_inds_15m:
            st.session_state['df_15m'] = get_cadence_data(
                api_key, project_id, mp_ids_list, d_start, d_end, 900, selected_inds_15m, STD_INDICATORS
            )

# --- VISUALIZATION (50/50 SPLIT) ---
if st.session_state['df_1h'] is not None or st.session_state['df_15m'] is not None:
    
    # Definition des Onglets
    t1, t2 = st.tabs(["⏱️ Hourly Data (1h)", "⚡ Short Data (15min)"])
    
    # Helper pour afficher Graph + Tableau cote a cote (50/50)
    def render_dashboard(df, title_suffix):
        if df is None:
            st.info("No data fetched for this aggregation.")
            return

        # Layout: Graph (50%) | Table (50%)
        col_graph, col_table = st.columns([1, 1])
        
        # --- LEFT: GRAPH ---
        with col_graph:
            fig = go.Figure()
            colors = itertools.cycle(ACOEM_COLORS)
            
            for col in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df[col],
                    mode='lines', # Clean lines
                    name=col,
                    line=dict(width=2, color=next(colors))
                ))
            
            # Force X Axis (Strict Range)
            x_min = datetime.combine(d_start, time.min)
            x_max = datetime.combine(d_end + timedelta(days=1), time.min)
            
            fig.update_layout(
                title=f"Evolution {title_suffix}",
                xaxis_title="Time", yaxis_title="Level (dB)",
                xaxis=dict(range=[x_min, x_max]), # Lock range
                height=500, # Hauteur fixe
                margin=dict(l=20, r=20, t=40, b=20),
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", y=1.1),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

        # --- RIGHT: TABLE ---
        with col_table:
            st.markdown(f"**Data Table** ({len(df)} rows)")
            
            # Export Button (Top)
            csv = df.to_csv().encode('utf-8')
            st.download_button(
                label="📥 CSV Export",
                data=csv,
                file_name=f"Cadence_{title_suffix}_{project_id}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )
            
            # Table (50% width, matched height)
            st.dataframe(df, height=450, use_container_width=True)

    # --- RENDER TABS ---
    with t1:
        render_dashboard(st.session_state['df_1h'], "1h")
        
    with t2:
        render_dashboard(st.session_state['df_15m'], "15min")

else:
    # Empty state - Placeholder
    st.info("👈 Please configure the extraction in the sidebar and click LOAD DATA.")
