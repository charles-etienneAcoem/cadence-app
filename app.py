import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, time, timedelta
import itertools

# --- ASSETS ---
ACOEM_LOGO_NEW = "https://cdn.bfldr.com/Q3Z2TZY7/at/b4z3s28jpswp92h6z35h9f3/ACOEM-LOGO-WithoutBaseline-RGB-Bicolor.jpg?auto=webp&format=jpg"
AECOM_LOGO = "https://zerionsoftware.com/wp-content/uploads/2023/10/aecom-logo.png"
ACOEM_COLORS = ['#ff6952', '#2c5078', '#96c8de', '#FFB000', '#50C878'] 

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
        .powered-text {
            text-align: center; color: white; font-size: 0.8rem;
            margin-top: 5px; margin-bottom: 5px; font-style: italic; opacity: 0.8;
        }
        .aecom-container {
            background-color: white; padding: 10px; border-radius: 6px;
            display: flex; justify-content: center; align-items: center; margin-bottom: 5px;
        }
        .streamlit-expanderHeader {
            font-size: 1rem; font-weight: bold; color: #ff6952;
        }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'df_1h' not in st.session_state: st.session_state['df_1h'] = None
if 'df_15m' not in st.session_state: st.session_state['df_15m'] = None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"""
        <div class="aecom-container"><img src="{AECOM_LOGO}" style="width: 100%; max-width: 160px;"></div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="powered-text">Powered by</div>', unsafe_allow_html=True)
    st.image(ACOEM_LOGO_NEW, use_container_width=True)
    
    st.divider()
    
    with st.expander("🔐 1. Authentication", expanded=True):
        api_key = st.text_input("API Key", type="password", help="Starts with EZfX...")

    with st.expander("🎯 2. Target", expanded=True):
        project_id = st.number_input("Project ID", value=689, step=1)
        mps_input = st.text_input("Point IDs", value="1797", help="Ex: 1797, 1798")

    with st.expander("⚙️ 3. Settings", expanded=True):
        STD_INDICATORS = [
            {"label": "LAeq (Avg)", "code": "LAeq", "method": "average"},
            {"label": "LAFMax (Max)", "code": "LAFMax", "method": "max"},
            {"label": "LAFMin (Min)", "code": "LAFMin", "method": "min"},
            {"label": "LCpeak (Max)", "code": "LCpeak", "method": "max"},
            {"label": "Lden (Avg)", "code": "Lden", "method": "average"}
        ]
        
        st.caption("Metrics Selection:")
        selected_inds_1h = st.multiselect("Hourly (1h)", [i["label"] for i in STD_INDICATORS], default=["LAeq (Avg)", "LAFMax (Max)"])
        selected_inds_15m = st.multiselect("Short (15min)", [i["label"] for i in STD_INDICATORS], default=["LAeq (Avg)"])
        
        st.divider()
        st.caption("Time Range:")
        col_d1, col_d2 = st.columns(2)
        d_start = col_d1.date_input("Start", date(2025, 1, 21))
        d_end = col_d2.date_input("End", date.today())

    st.markdown("")
    btn_run = st.button("🚀 LOAD DATA", type="primary", use_container_width=True)

# --- MAIN TITLE ---
st.title(f"Project #{project_id} - Data Dashboard")

# --- DATA FETCHING ---
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
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{proj_id}/data"
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            data = r.json()
            if not data.get('timeStamp'): return None
            
            df = pd.DataFrame({'Date': pd.to_datetime(data['timeStamp'])})
            df['Date'] = df['Date'].dt.tz_localize(None) 
            
            mask = (df['Date'] >= dt_start) & (df['Date'] < dt_end)
            
            for item in data.get('indicators', []):
                mp_name = str(item.get('measurementPointId'))
                if 'measurementPoint' in item:
                    mp_name = item['measurementPoint'].get('measurementPointName', mp_name)
                elif 'measurementPointId' in item:
                     mp_name = str(item['measurementPointId'])

                dtype = item.get('primaryData', 'Val')
                if 'indicatorDescription' in item:
                    dtype = item['indicatorDescription'].get('primaryData', dtype)

                col_name = f"{mp_name} | {dtype}"
                
                raw_vals = item.get('data', {}).get('values')
                if raw_vals:
                    vals = raw_vals[0] if (isinstance(raw_vals, list) and len(raw_vals)>0 and isinstance(raw_vals[0], list)) else raw_vals
                    if len(vals) == len(df):
                        df[col_name] = vals

            df = df.loc[mask].copy()
            if df.empty: return None
            df.set_index('Date', inplace=True)
            return df
        else:
            st.error(f"API Error: {r.status_code}"); return None
    except Exception as e:
        st.error(f"Error: {e}"); return None

# --- EXECUTION ---
if btn_run:
    if not api_key: st.error("⚠️ Missing API Key"); st.stop()
    try: mp_ids_list = [int(x.strip()) for x in mps_input.split(",") if x.strip()]
    except: st.error("⚠️ Invalid Point IDs"); st.stop()
        
    st.session_state['df_1h'] = None
    st.session_state['df_15m'] = None
    
    with st.spinner("Fetching data from cloud..."):
        if selected_inds_1h:
            st.session_state['df_1h'] = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 3600, selected_inds_1h, STD_INDICATORS)
        if selected_inds_15m:
            st.session_state['df_15m'] = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 900, selected_inds_15m, STD_INDICATORS)

# --- VISUALIZATION ---
if st.session_state['df_1h'] is not None or st.session_state['df_15m'] is not None:
    
    t1, t2 = st.tabs(["⏱️ Hourly Data (1h)", "⚡ Short Data (15min)"])
    
    def render_dashboard(df, title_suffix):
        if df is None: st.info("No data fetched."); return

        col_graph, col_table = st.columns([1, 1])
        
        with col_graph:
            fig = go.Figure()
            colors = itertools.cycle(ACOEM_COLORS)
            for col in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col, line=dict(width=2, color=next(colors))))
            
            x_min = datetime.combine(d_start, time.min)
            x_max = datetime.combine(d_end + timedelta(days=1), time.min)
            
            fig.update_layout(
                title=f"Evolution {title_suffix}", xaxis_title="Time", yaxis_title="Level (dB)",
                xaxis=dict(range=[x_min, x_max]), height=500,
                margin=dict(l=20, r=20, t=40, b=20),
                template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", y=1.1), hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            st.markdown(f"**Data Table** ({len(df)} rows)")
            csv = df.to_csv().encode('utf-8')
            
            # --- CORRECTION DE L'ERREUR ICI ---
            # On ajoute 'key' pour que chaque bouton soit unique
            unique_key = f"dl_btn_{title_suffix}"
            
            st.download_button(
                label="📥 CSV Export",
                data=csv,
                file_name=f"Cadence_{title_suffix}_{project_id}.csv",
                mime="text/csv",
                key=unique_key, # La clé unique qui sauve la mise !
                type="primary",
                use_container_width=True
            )
            st.dataframe(df, height=450, use_container_width=True)

    with t1: render_dashboard(st.session_state['df_1h'], "1h")
    with t2: render_dashboard(st.session_state['df_15m'], "15min")

else:
    st.info("👈 Open the sections in the sidebar to configure and load data.")
