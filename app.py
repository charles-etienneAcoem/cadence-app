import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- PAGE CONFIGURATION ---
# Dark mode is default in Streamlit if the user's OS is dark, 
# or can be forced in settings. We use a wide layout.
st.set_page_config(page_title="Cadence Data Extractor", page_icon="🌍", layout="wide")

st.title("🌍 Get Aggregated Data")
st.markdown("### Acoem Cadence Interface")

# --- SESSION STATE INITIALIZATION ---
if 'df_1h' not in st.session_state: st.session_state['df_1h'] = None
if 'df_15m' not in st.session_state: st.session_state['df_15m'] = None

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("1. Authentication")
    api_key = st.text_input("API Key", type="password", help="Starts with EZfX...")
    
    st.divider()
    
    st.header("2. Target (Manual Mode)")
    # Default values from your project
    project_id = st.number_input("Project ID", value=689, step=1)
    mps_input = st.text_input("Measurement Point IDs", value="1797", help="e.g.: 1797, 1798")
    
    st.divider()
    
    st.header("3. Configuration")
    st.caption("Data aggregation:")
    use_1h = st.checkbox("Hourly Data (1h)", value=True, help="LAeq + LAFMax")
    use_15m = st.checkbox("Short Data (15min)", value=True, help="LAeq only")
    
    st.caption("Time Range:")
    d_start = st.date_input("Start Date", date(2025, 1, 21))
    d_end = st.date_input("End Date", date.today())
    
    st.divider()
    
    # Primary button (often red/orange by default, but distinct)
    btn_run = st.button("🚀 GET DATA", type="primary")

# --- CORE FUNCTION: DATA FETCHING ---
def get_cadence_data(api_key, proj_id, mp_ids, start, end, agg_time, suffix):
    """
    Fetches data from Cadence Cloud API.
    Handles nested JSON structures robustly.
    """
    
    # 1. Build Payload (Strict AppScript format)
    indicators = []
    for mp in mp_ids:
        # LAeq (Base for both)
        indicators.append({
            "measurementPointId": mp, "primaryData": "LAeq", "aggregationMethod": "average",
            "timeFrequency": "global", "frequencyBand": None, "axis": None, "precision": 1
        })
        # Add Max only for Hourly to keep it clean
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
            
            # Create Base DataFrame
            df = pd.DataFrame({'Date': pd.to_datetime(data['timeStamp'])})
            
            # Parse Indicators
            for item in data.get('indicators', []):
                
                # A. Robust ID/Name Extraction
                mp_id = "Unknown"
                mp_name = "Unknown"
                
                # Check for nested object (New API format)
                if 'measurementPoint' in item:
                    mp_obj = item['measurementPoint']
                    mp_id = mp_obj.get('measurementPointId')
                    mp_name = mp_obj.get('measurementPointName', str(mp_id))
                # Check for flat object (Old API format)
                elif 'measurementPointId' in item:
                    mp_id = item['measurementPointId']
                    mp_name = str(mp_id)
                
                # B. Data Type
                dtype = "Val"
                if 'indicatorDescription' in item:
                    dtype = item['indicatorDescription'].get('primaryData', 'Val')
                elif 'primaryData' in item:
                    dtype = item['primaryData']

                col_name = f"{mp_name} | {dtype}"
                
                # C. Value Extraction (Handle [[v]] vs [v])
                raw_vals = item.get('data', {}).get('values')
                if raw_vals:
                    # Flatten list if nested
                    final_vals = raw_vals[0] if (isinstance(raw_vals, list) and len(raw_vals)>0 and isinstance(raw_vals[0], list)) else raw_vals
                    
                    # Size check
                    if len(final_vals) == len(df):
                        df[col_name] = final_vals
            
            df.set_index('Date', inplace=True)
            return df
            
        else:
            st.error(f"API Error ({suffix}): {r.status_code} - {r.text}")
            return None
            
    except Exception as e:
        st.error(f"Script Error ({suffix}): {e}")
        return None

# --- MAIN EXECUTION ---
if btn_run:
    if not api_key:
        st.error("⚠️ Please enter your API Key.")
        st.stop()
        
    try:
        mp_ids_list = [int(x.strip()) for x in mps_input.split(",") if x.strip()]
    except:
        st.error("⚠️ Invalid format for Points IDs (use: 1797, 1798)")
        st.stop()

    # Reset State
    st.session_state['df_1h'] = None
    st.session_state['df_15m'] = None
    
    # 1. Fetch 1H Data
    if use_1h:
        with st.spinner("Fetching Hourly Data..."):
            st.session_state['df_1h'] = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 3600, "1h")

    # 2. Fetch 15min Data
    if use_15m:
        with st.spinner("Fetching 15min Data..."):
            st.session_state['df_15m'] = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 900, "15m")

# --- VISUALIZATION SECTION ---
if st.session_state['df_1h'] is not None or st.session_state['df_15m'] is not None:
    
    st.success("✅ Data successfully retrieved!")
    st.divider()
    
    # --- CHART: SUPERIMPOSED ---
    st.markdown("### 📈 Time Analysis")
    fig = go.Figure()
    
    # 15 min (Thin lines, background) - Using Acoem-like Green
    if st.session_state['df_15m'] is not None:
        df = st.session_state['df_15m']
        cols = [c for c in df.columns if "LAeq" in c]
        for i, c in enumerate(cols):
            fig.add_trace(go.Scatter(
                x=df.index, y=df[c], mode='lines', name=f"15m - {c}",
                line=dict(width=1, color='#00B0F0'), # Cyan/Blue
                opacity=0.6
            ))
            
    # 1h (Thick lines + Markers, foreground) - Using Acoem-like Blue/Contrast
    if st.session_state['df_1h'] is not None:
        df = st.session_state['df_1h']
        cols = [c for c in df.columns if "LAeq" in c]
        for i, c in enumerate(cols):
            fig.add_trace(go.Scatter(
                x=df.index, y=df[c], mode='lines+markers', name=f"1H - {c}",
                line=dict(width=3, color='#FFFFFF'), # White for high contrast on dark bg
                marker=dict(size=7, symbol="circle", color='#00CC96') # Green dots
            ))

    fig.update_layout(
        title="LAeq Comparison (1h vs 15min)",
        xaxis_title="Date / Time",
        yaxis_title="Level (dB)",
        hovermode="x unified",
        height=550,
        legend=dict(orientation="h", y=1.1),
        template="plotly_dark", # Forces dark theme for the chart
        plot_bgcolor='rgba(0,0,0,0)', # Transparent background
        paper_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # --- DATA TABLES (BUTTONS ON TOP) ---
    st.markdown("### 📋 Data Tables")
    
    tab1, tab2 = st.tabs(["🕒 Hourly Data (1h)", "⏱️ Short Data (15min)"])
    
    # TAB 1: 1H
    with tab1:
        if st.session_state['df_1h'] is not None:
            # 1. DOWNLOAD BUTTON (TOP)
            csv_1h = st.session_state['df_1h'].to_csv().encode('utf-8')
            st.download_button(
                label="📥 Download CSV (1h)",
                data=csv_1h,
                file_name=f"Cadence_1h_{project_id}.csv",
                mime="text/csv",
                type="primary"
            )
            # 2. TABLE
            st.dataframe(st.session_state['df_1h'], use_container_width=True)
        else:
            st.info("No Hourly data available.")
            
    # TAB 2: 15MIN
    with tab2:
        if st.session_state['df_15m'] is not None:
            # 1. DOWNLOAD BUTTON (TOP)
            csv_15m = st.session_state['df_15m'].to_csv().encode('utf-8')
            st.download_button(
                label="📥 Download CSV (15min)",
                data=csv_15m,
                file_name=f"Cadence_15m_{project_id}.csv",
                mime="text/csv",
                type="primary"
            )
            # 2. TABLE
            st.dataframe(st.session_state['df_15m'], use_container_width=True)
        else:
            st.info("No 15min data available.")
