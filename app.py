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
                    # CORRECTION ICI : on utilise explicitement le nom de la colonne en texte
                    source_col = 'sourceRecognitionId'
                    
                    df_ident[source_col] = df_ident[source_col].replace({None: t["unknown"], '': t["unknown"], float('nan'): t["unknown"]})
                    pie_data = df_ident.groupby(source_col).size().reset_index(name='Count')
                    
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=pie_data[source_col], 
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
