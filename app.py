import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, time
import itertools

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Cadence Data Extractor", page_icon="📊", layout="wide")

# --- ACOEM BRANDING ASSETS ---
ACOEM_LOGO = "https://cdn.bfldr.com/Q3Z2TZY7/at/2rg3rwh4gcnrvn5gkh8rckpp/ACOEM-LOGO-Brandsymbol-RGB-Orange.png?auto=webp&format=png"
ACOEM_COLORS = ['#ff6952', '#2c5078', '#96c8de'] # Orange, Dark Blue, Light Blue

# --- SIDEBAR ---
with st.sidebar:
    st.image(ACOEM_LOGO, width=60)
    st.title("Cadence Data")
    
    st.divider()
    
    st.header("1. Authentication")
    api_key = st.text_input("API Key", type="password")
    
    st.header("2. Target")
    project_id = st.number_input("Project ID", value=689, step=1)
    mps_input = st.text_input("Point IDs", value="1797", help="e.g.: 1797, 1798")
    
    st.header("3. Settings")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        use_1h = st.checkbox("1h Data", value=True)
    with col_c2:
        use_15m = st.checkbox("15min Data", value=True)
        
    d_start = st.date_input("Start Date", date(2025, 1, 21))
    d_end = st.date_input("End Date", date.today())
    
    st.divider()
    btn_run = st.button("🚀 GET DATA", type="primary")

# --- MAIN TITLE ---
st.title("Get Aggregated Data")

# --- SESSION STATE ---
if 'df_1h' not in st.session_state: st.session_state['df_1h'] = None
if 'df_15m' not in st.session_state: st.session_state['df_15m'] = None

# --- FUNCTION: FETCH DATA ---
def get_cadence_data(api_key, proj_id, mp_ids, start_date, end_date, agg_time, suffix):
    """Fetches data and strictly clips it to the requested time range."""
    
    # Define exact datetime boundaries
    dt_start = datetime.combine(start_date, time.min) # 00:00:00
    dt_end = datetime.combine(end_date, time.max)     # 23:59:59.999999
    
    # 1. Build Payload
    indicators = []
    for mp in mp_ids:
        indicators.append({
            "measurementPointId": mp, "primaryData": "LAeq", "aggregationMethod": "average",
            "timeFrequency": "global", "frequencyBand": None, "axis": None, "precision": 1
        })
        if agg_time == 3600:
            indicators.append({
                "measurementPointId": mp, "primaryData": "LAFMax", "aggregationMethod": "max",
                "timeFrequency": "global", "frequencyBand": None, "axis": None, "precision": 1
            })

    # API Request (UTC ISO)
    payload = {
        "start": f"{start_date}T00:00:00Z", "end": f"{end_date}T23:59:59Z",
        "aggregationTime": agg_time, "indicators": indicators
    }
    
    headers = {"accept": "application/json", "Content-Type": "application/json", "X-API-KEY": api_key}
    url = f"https://cadence.acoem.com/cloud-api/v1/projects/{proj_id}/data"
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            data = r.json()
            if not data.get('timeStamp'): return None
            
            # Create DataFrame
            df = pd.DataFrame({'Date': pd.to_datetime(data['timeStamp'])})
            
            # --- STRICT FILTERING ---
            # Keep only data within the requested range
            mask = (df['Date'] >= dt_start) & (df['Date'] <= dt_end)
            # We filter the dataframe structure later, but first we need to align values
            
            for item in data.get('indicators', []):
                # ID/Name logic
                mp_name = "Unknown"
                if 'measurementPoint' in item:
                    mp_name = item['measurementPoint'].get('measurementPointName', str(item['measurementPoint'].get('measurementPointId')))
                elif 'measurementPointId' in item:
                    mp_name = str(item['measurementPointId'])
                
                # Data Type
                dtype = item.get('indicatorDescription', {}).get('primaryData', item.get('primaryData', 'Val'))
                col_name = f"{mp_name} | {dtype}"
                
                # Values extraction
                raw_vals = item.get('data', {}).get('values')
                if raw_vals:
                    final_vals = raw_vals[0] if (isinstance(raw_vals, list) and len(raw_vals)>0 and isinstance(raw_vals[0], list)) else raw_vals
                    
                    if len(final_vals) == len(df):
                        # Add column
                        df[col_name] = final_vals
                    else:
                        pass # Ignore mismatch size
            
            # Apply Filter NOW
            df = df.loc[mask].copy()
            
            if df.empty:
                return None
                
            df.set_index('Date', inplace=True)
            return df
        else:
            st.error(f"API Error ({suffix}): {r.status_code}")
            return None
    except Exception as e:
        st.error(f"Script Error ({suffix}): {e}")
        return None

# --- EXECUTION ---
if btn_run:
    if not api_key:
        st.error("⚠️ Please enter your API Key.")
        st.stop()
        
    try:
        mp_ids_list = [int(x.strip()) for x in mps_input.split(",") if x.strip()]
    except:
        st.error("⚠️ Invalid format for Points IDs.")
        st.stop()

    st.session_state['df_1h'] = None
    st.session_state['df_15m'] = None
    
    if use_1h:
        with st.spinner("Fetching Hourly Data..."):
            st.session_state['df_1h'] = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 3600, "1h")
    
    if use_15m:
        with st.spinner("Fetching 15min Data..."):
            st.session_state['df_15m'] = get_cadence_data(api_key, project_id, mp_ids_list, d_start, d_end, 900, "15m")

# --- VISUALIZATION ---
if st.session_state['df_1h'] is not None or st.session_state['df_15m'] is not None:
    
    tab1, tab2 = st.tabs(["🕒 Hourly Data (1h)", "⏱️ Short Data (15min)"])
    
    # Calculate Axis Boundaries (Force 00:00 to 23:59)
    x_axis_min = datetime.combine(d_start, time.min)
    x_axis_max = datetime.combine(d_end, time.max)
    
    # --- TAB 1: HOURLY ---
    with tab1:
        if st.session_state['df_1h'] is not None:
            df = st.session_state['df_1h']
            
            fig = go.Figure()
            colors = itertools.cycle(ACOEM_COLORS)
            
            for col in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df[col],
                    mode='lines',
                    name=col,
                    line=dict(width=2, color=next(colors))
                ))
            
            fig.update_layout(
                title=f"Hourly Evolution ({d_start} to {d_end})",
                xaxis_title="Time", yaxis_title="dB",
                # FORCE EXACT RANGE
                xaxis=dict(range=[x_axis_min, x_axis_max]),
                height=500, hovermode="x unified",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            col_btn, _ = st.columns([1, 4])
            csv = df.to_csv().encode('utf-8')
            col_btn.download_button("📥 Download CSV (1h)", csv, f"Cadence_1h_{project_id}.csv", "text/csv", type="primary")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No Hourly Data.")

    # --- TAB 2: 15 MIN ---
    with tab2:
        if st.session_state['df_15m'] is not None:
            df = st.session_state['df_15m']
            
            fig = go.Figure()
            colors = itertools.cycle(ACOEM_COLORS)
            
            for col in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df[col],
                    mode='lines',
                    name=col,
                    line=dict(width=2, color=next(colors))
                ))
            
            fig.update_layout(
                title=f"15min Evolution ({d_start} to {d_end})",
                xaxis_title="Time", yaxis_title="dB",
                # FORCE EXACT RANGE
                xaxis=dict(range=[x_axis_min, x_axis_max]),
                height=500, hovermode="x unified",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            col_btn, _ = st.columns([1, 4])
            csv = df.to_csv().encode('utf-8')
            col_btn.download_button("📥 Download CSV (15m)", csv, f"Cadence_15m_{project_id}.csv", "text/csv", type="primary")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No 15min Data.")
