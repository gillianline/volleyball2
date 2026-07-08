import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math 
from datetime import timedelta

# --- 1. CONFIG & SYSTEM GLOBAL CSS ---
st.set_page_config(page_title="Volleyball Performance Dashboard", layout="wide")

st.markdown("""
    <style>
    th, td {text-align: center !important;}
    [data-testid="stMetricValue"] {font-size: 24px;}
    
    @media print {
        [data-testid="stSidebar"], [data-testid="stHeader"] {
            display: none !important;
        }
        .main .block-container {
            padding: 1rem !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        body {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
    }
    .stApp { background-color: #FFFFFF; color: #1D1D1F; }
    hr { display: none !important; }
    .block-container { padding-top: 2rem !important; }
    .viewerBadge_link__1S137, .main_heading_anchor__m6v0K, a.header-anchor { display: none !important; }
    header a { display: none !important; }
    .scout-table { width: 100%; border-collapse: collapse; text-align: center; table-layout: auto; }
    .scout-table th { background-color: #4895DB; color: white; padding: 4px; border-bottom: 2px solid #515154; font-weight: 700; font-size: 11px; text-transform: uppercase; }
    .scout-table td { padding: 4px; border-bottom: 1px solid #F5F5F7; font-size: 11px; color: #1D1D1F; }
    .bg-highlight-red { background-color: #ffcccc !important; font-weight: 900; }
    .arrow-red { color: #b30000 !important; font-weight: 900; margin-left: 4px; }
    .player-photo-large { border-radius: 50%; width: 220px; height: 220px; object-fit: contain; border: 6px solid #4895DB; }
    .score-box { padding: 12px 20px; border-radius: 12px; font-size: 28px; font-weight: 800; min-width: 100px; color: #FFFFFF; line-height: 1.2; text-align: center;}
    .info-box { background-color: #f8f9fa; border-left: 5px solid #4895DB; padding: 12px; margin-top: 10px; font-size: 12px; color: #1D1D1F; font-weight: 600; line-height: 1.4; }
    
    .player-row-container { 
        break-inside: avoid !important; 
        page-break-inside: avoid !important; 
        display: block !important; 
        margin-bottom: 30px; 
    }
    
    .player-divider { border: 0; height: 1px; background: #E5E5E7; margin-bottom: 15px; width: 100%; }
    .gallery-photo { border-radius: 50%; width: 110px; height: 110px; object-fit: cover; border: 4px solid #4895DB; }
    .section-header { font-size: 20px; font-weight: 800; color: #4895DB; border-bottom: 2px solid #515154; margin-top: 15px; margin-bottom: 10px; padding-bottom: 5px; text-transform: uppercase; }

    @media print {
        .main-logo-container { display: block !important; margin-bottom: 0 !important; }
        .stTabs [role="tablist"], [data-testid="stSidebar"], header, footer, button, .stButton { display: none !important; }
        .main .block-container { padding: 0 !important; max-width: 100% !important; }
        .scout-table td, p, span, div { color: #000000 !important; }
    }
    </style>
    """, unsafe_allow_html=True)


# --- 2. PASSWORD VALIDATION ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        st.error("Incorrect Password")
        return False
    else:
        return True

def get_flipped_gradient(score):
    """
    Returns an HEX color string representing an athletic performance gradient.
    Low scores get a muted red/grey warning tile, mid-scores lean into light blue,
    and high scores scale into deep athletic blue.
    """
    score = max(0, min(100, int(round(score))))
    
    if score < 40:
        return "#DC3545" 
    elif score < 70:
        return "#4895DB"
    else:
        return "#1F517F"


# --- 3. HARD DECOUPLED DATA FETCHING ENGINE ---
@st.cache_data(ttl=10)
def load_all_data():
    def heavy_sanitize(frame):
        frame.columns = frame.columns.str.strip()
        for col in frame.columns:
            c_low = col.lower()
            if 'player' in c_low and 'load' in c_low: frame.rename(columns={col: 'Player Load'}, inplace=True)
            if 'total' in c_low and 'jumps' in c_low: frame.rename(columns={col: 'Total Jumps'}, inplace=True)
            if 'estimated' in c_low and 'dist' in c_low: frame.rename(columns={col: 'Estimated Distance (y)'}, inplace=True)
            if 'explosive' in c_low: frame.rename(columns={col: 'Explosive Efforts'}, inplace=True)
            if 'duration' in c_low: frame.rename(columns={col: 'Duration'}, inplace=True)

        math_cols = ['Player Load', 'Total Jumps', 'Estimated Distance (y)', 'Explosive Efforts', 'Duration', 
                     'Moderate Jumps', 'High Jumps', 'Jump Load', 'High Intensity Movement']
        
        for col in math_cols:
            if col in frame.columns:
                frame[col] = pd.to_numeric(frame[col].astype(str).str.replace(r'[^0-9.]', '', regex=True), errors='coerce').fillna(0).astype(float)
            else:
                frame[col] = 0.0
        return frame

    def assign_season(date_val):
        if pd.isna(date_val): return 'Spring'
        m = date_val.month
        d = date_val.day
        if 1 <= m <= 4: return 'Spring'
        elif m == 5 and d >= 26: return 'Summer'
        elif m > 5: return 'Summer'
        else: return 'Spring'

    df = pd.read_csv(st.secrets["GOOGLE_SHEET_URL"])
    match_df = pd.read_csv(st.secrets["MATCHES_SHEET_URL"])
    
    df = heavy_sanitize(df)
    df['Sheet_Order'] = range(len(df))
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    if 'Week' in df.columns:
        df['Week'] = pd.to_numeric(df['Week'].astype(str).str.extract('(\d+)', expand=False), errors='coerce').fillna(0).astype(int)
    df['Session_Name'] = df['Activity'].fillna(df['Date'].dt.strftime('%m/%d/%Y'))
    df['Position'] = df.groupby('Name')['Position'].ffill().bfill().fillna("N/A")
    df['PhotoURL'] = df.groupby('Name')['PhotoURL'].ffill().bfill().fillna("https://www.w3schools.com/howto/img_avatar.png")
    df['Session_Type'] = df['Activity'].apply(lambda x: 'Game' if any(w in str(x).lower() for w in ['game', 'match', 'v.']) else 'Practice')
    df['Season'] = df['Date'].apply(assign_season)

    match_df = heavy_sanitize(match_df)
    match_df['Sheet_Order'] = range(len(match_df))
    match_df['Date'] = pd.to_datetime(match_df['Date'], errors='coerce')
    if 'Week' in match_df.columns:
        match_df['Week'] = pd.to_numeric(match_df['Week'].astype(str).str.extract('(\d+)', expand=False), errors='coerce').fillna(0).astype(int)
    match_df['Session_Name'] = match_df['Activity'].fillna(match_df['Date'].dt.strftime('%m/%d/%Y'))
    match_df['Position'] = match_df.groupby('Name')['Position'].ffill().bfill().fillna("N/A")
    match_df['PhotoURL'] = match_df.groupby('Name')['PhotoURL'].ffill().bfill().fillna("https://www.w3schools.com/howto/img_avatar.png")
    match_df['Session_Type'] = match_df['Activity'].apply(lambda x: 'Game' if any(w in str(x).lower() for w in ['game', 'match', 'v.']) else 'Practice')
    match_df['Season'] = match_df['Date'].apply(assign_season)

    cmj_df = pd.read_csv(st.secrets["CMJ_SHEET_URL"])
    cmj_df.columns = cmj_df.columns.str.strip()
    cmj_df.rename(columns={'Athlete': 'Name'}, inplace=True)
    cmj_df['Test Date'] = pd.to_datetime(cmj_df['Test Date'], errors='coerce')
    if 'Week' in cmj_df.columns:
        cmj_df['Week'] = pd.to_numeric(cmj_df['Week'].astype(str).str.extract('(\d+)', expand=False), errors='coerce').fillna(0).astype(int)
    cmj_df['Season'] = cmj_df['Test Date'].apply(assign_season)

    try:
        ash_df = pd.read_csv(st.secrets["ASH_SHEET_URL"])
        ash_df.columns = ash_df.columns.str.strip()
        ash_df.rename(columns={'Athlete': 'Name', 'Date': 'Test Date'}, inplace=True)
        ash_df['Test Date'] = pd.to_datetime(ash_df['Test Date'], errors='coerce')
        for col in ['Peak Vertical Force [N] (L)', 'Peak Vertical Force [N] (R)', 'Peak Vertical Force [N] (Asym)(%)']:
            if col in ash_df.columns:
                ash_df[col] = pd.to_numeric(ash_df[col].astype(str).str.replace(r'[^0-9.-]', '', regex=True), errors='coerce').fillna(0.0)
        ash_df['Season'] = ash_df['Test Date'].apply(assign_season)
    except:
        ash_df = pd.DataFrame(columns=['Name', 'Test Date', 'Isometric Type', 'Peak Vertical Force [N] (L)', 'Peak Vertical Force [N] (R)', 'Peak Vertical Force [N] (Asym)(%)', 'Season'])

    try:
        er_df = pd.read_csv(st.secrets["ER_SHEET_URL"])
        er_df.columns = er_df.columns.str.strip()
        er_df.rename(columns={'Athlete': 'Name', 'Date': 'Test Date'}, inplace=True)
        er_df['Test Date'] = pd.to_datetime(er_df['Test Date'], errors='coerce')
        for col in ['L Max ROM (°)', 'R Max ROM (°)', 'ROM Asymmetry (%)']:
            if col in er_df.columns:
                er_df[col] = pd.to_numeric(er_df[col].astype(str).str.replace(r'[^0-9.-]', '', regex=True), errors='coerce').fillna(0.0)
        er_df['Season'] = er_df['Test Date'].apply(assign_season)
    except:
        er_df = pd.DataFrame(columns=['Name', 'Test Date', 'Movement', 'L Max ROM (°)', 'R Max ROM (°)', 'ROM Asymmetry (%)', 'Season'])

    phase_df = pd.read_csv(st.secrets["PHASES_SHEET_URL"])
    phase_df = heavy_sanitize(phase_df)
    if 'Phases' in phase_df.columns: phase_df = phase_df.rename(columns={'Phases': 'Phase'})
    phase_df['Date'] = pd.to_datetime(phase_df['Date'], errors='coerce')
    date_season_map = df.drop_duplicates('Date').set_index('Date')['Season'].to_dict()
    phase_df['Season'] = phase_df['Date'].map(date_season_map).fillna('Spring')
    
    try:
        thresh_df = pd.read_csv(st.secrets["THRESH_SHEET_URL"])
        thresh_df.columns = thresh_df.columns.str.strip()
        for col in ['Load_Limit', 'Jump_Limit']:
            if col in thresh_df.columns:
                thresh_df[col] = pd.to_numeric(thresh_df[col].astype(str).str.replace(r'[^0-9.]', '', regex=True), errors='coerce').fillna(0).astype(float)
    except:
        thresh_df = None
        
    return df.dropna(subset=['Date']), match_df.dropna(subset=['Date']), cmj_df, phase_df, thresh_df, ash_df, er_df


# --- 4. ENGINE CORE BLOCK INTERACTION ---
if check_password():
    if "is_printing" not in st.session_state:
        st.session_state.is_printing = False

    LOCKED_CONFIG = {'staticPlot': False, 'displayModeBar': False}

    try:
        raw_df, raw_match_df, raw_cmj_df, raw_phase_df, thresh_df, raw_ash_df, raw_er_df = load_all_data()

        # --- SIDEBAR CONFIG (ISOLATED TO SPRING ONLY) ---
        st.sidebar.markdown("### Season")
        selected_season = "Spring"
        st.sidebar.info("Displaying Spring Season Performance Data.")
        
        df_master = raw_df[raw_df['Season'] == selected_season].copy()
        match_master = raw_match_df[raw_match_df['Season'] == selected_season].copy()
        cmj_master = raw_cmj_df[raw_cmj_df['Season'] == selected_season].copy()
        ash_master = raw_ash_df[raw_ash_df['Season'] == selected_season].copy()
        er_master = raw_er_df[raw_er_df['Season'] == selected_season].copy()
        phase_master = raw_phase_df[raw_phase_df['Season'] == selected_season].copy()
        
        phase_map = {
            "Mini Games (Set 1)": "Mini Games", "Mini Games (Set 2)": "Mini Games", "Brizo (2)": "Brizo",
            "2 Ball (Set 1)": "2 Ball", "2 Ball (Set 2)": "2 Ball", "2 Ball (Set 3)": "2 Ball", "2 Ball (Set 4)": "2 Ball",
            "serving (2)": "Serving", "serving": "Serving", "Serving (2)": "Serving", "2/3 Hitters (2)": "2/3 Hitters",
            "5v5 (2)": "5v5", "Serve & Pass": "Serve and Pass"
        }
        all_metrics = ['Total Jumps', 'Moderate Jumps', 'High Jumps', 'Jump Load', 'Player Load', 'Estimated Distance (y)', 'Explosive Efforts', 'High Intensity Movement']
        cmj_col = 'Jump Height (Imp-Mom) [cm]'
        rsi_col = 'RSI-modified [m/s]'
        
        master_athlete_list = sorted(list(set(df_master['Name'].unique()) | set(cmj_master['Name'].unique()) | set(ash_master['Name'].unique()) | set(er_master['Name'].unique())))
        session_list = df_master[df_master['Session_Name'].notna()].sort_values('Date', ascending=False)['Session_Name'].unique().tolist()

        # --- CLEAN REMOVAL OF LOGO & GENERIC TITLE ---
        st.markdown('<div class="main-logo-container" style="text-align: center; margin-top: 10px; margin-bottom: 25px;"><div style="color: #4895DB; font-size: 2.2rem; font-weight: 900; letter-spacing: -0.5px;">VOLLEYBALL PERFORMANCE</div></div>', unsafe_allow_html=True)

        # --- MANDATORY ISOLATION ARCHITECTURE: NATIVE STATE LINKING ---
        tab_titles = ["Individual Profile", "Practice Scores", "Practice History", "Match v. Practice", "Match Summary", "Position Analysis", "Phase Analysis", "Practice Planner"]
        
        if "active_tab_state" not in st.session_state:
            st.session_state.active_tab_state = "Individual Profile"

        selected_tab_label = st.radio("Navigation View Menu Selection Control", tab_titles, label_visibility="collapsed", horizontal=True, key="master_app_structural_gate_radio")
        st.session_state.active_tab_state = selected_tab_label

        # ==========================================
        # --- TAB CLAUSE 1: INDIVIDUAL PROFILE -----
        # ==========================================
        if st.session_state.active_tab_state == "Individual Profile":
            df_t0 = df_master.copy()
            cmj_t0 = cmj_master.copy()
            ash_t0 = ash_master.copy()
            er_t0 = er_master.copy()
            phase_t0 = phase_master.copy()

            c_prof1, c_prof2 = st.columns(2)
            with c_prof1: selected_session_prof = st.selectbox("Session Selection", session_list if session_list else ["No Sessions"], index=0, key="nav_sel_prof_t0")
            with c_prof2: selected_athlete_prof = st.selectbox("Athlete Selection", master_athlete_list, key="nav_ath_prof_t0")

            p_session_data = df_t0[(df_t0['Name'] == selected_athlete_prof) & (df_t0['Session_Name'] == selected_session_prof)]
            p_row = p_session_data.iloc[0] if not p_session_data.empty else pd.Series()
            curr_date_prof = p_row['Date'] if not p_row.empty else None
            p_meta = p_row

            if p_row.empty:
                curr_date_prof = pd.to_datetime(df_t0['Date'].max() if not df_t0.empty else "2026-01-01")
                meta_lookup = df_t0[df_t0['Name'] == selected_athlete_prof]
                pos_val = meta_lookup['Position'].iloc[0] if not meta_lookup.empty else "N/A"
                photo_val = meta_lookup['PhotoURL'].iloc[0] if not meta_lookup.empty else "https://www.w3schools.com/howto/img_avatar.png"
                p_meta = pd.Series({'Name': selected_athlete_prof, 'Position': pos_val, 'PhotoURL': photo_val})
                p_row = pd.Series({m: 0.0 for m in all_metrics})
                p_row['Name'] = selected_athlete_prof

            p_full_prof = df_t0[df_t0['Name'] == selected_athlete_prof]
            daily_sums_prof = p_full_prof.groupby('Date')[all_metrics].sum().reset_index()
            lb_prof = daily_sums_prof[(daily_sums_prof['Date'] >= pd.to_datetime(curr_date_prof) - timedelta(days=30)) & (daily_sums_prof['Date'] <= pd.to_datetime(curr_date_prof))]

            filtered_metrics_prof = [m for m in all_metrics if m not in ['High Jumps', 'Moderate Jumps', 'High Intensity Movement']]
            r_html_prof = ""; t_grade_prof = 0; c_metrics_prof = 1

            for k in filtered_metrics_prof:
                val = p_row.get(k, 0.0)
                mx = lb_prof[k].max() if (not lb_prof.empty and k in lb_prof.columns and lb_prof[k].max() > 0) else 1.0
                avg = lb_prof[k].mean() if (not lb_prof.empty and k in lb_prof.columns and lb_prof[k].mean() > 0) else 1.0
                g = math.ceil((val / mx) * 100) if mx > 0 else 0
                t_grade_prof += g; c_metrics_prof += 1
                diff = (val - avg) / avg if avg != 0 else 0
                h_class = "class='bg-highlight-red'" if abs(diff) > 0.10 else ""
                arr_val = f"<span class='arrow-red'>{'↑' if diff > 0.10 else '↓'}</span>" if abs(diff) > 0.10 else ""
                r_html_prof += f"<tr><td>{k}</td><td {h_class}>{val:.1f} {arr_val}</td><td>{mx:.1f}</td><td>{g}</td></tr>"

            sc_prof = math.ceil(t_grade_prof / c_metrics_prof) if c_metrics_prof > 0 else 0

            c1, c2, c3 = st.columns([1.2, 2.5, 1.2])
            with c1: st.markdown(f'<div style="text-align:center;"><img src="{p_meta.get("PhotoURL", "https://www.w3schools.com/howto/img_avatar.png")}" class="player-photo-large"></div><h3 style="text-align:center;">{p_meta.get("Name", selected_athlete_prof)}</h3>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div style="width:100%;"><table class="scout-table"><thead><tr><th>Metric</th><th>Today Total</th><th>30d Max Day</th><th>Grade</th></tr></thead><tbody>{r_html_prof}</tbody></table></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div style="display:flex; justify-content:center;"><div class="score-box" style="background-color:{get_flipped_gradient(sc_prof)};">{sc_prof}</div></div><p style="text-align:center; font-weight:bold; color:grey; margin-top:10px;">SESSION SCORE</p>', unsafe_allow_html=True)
            
            st.markdown('<div class="section-header">Weekly Readiness Profile</div>', unsafe_allow_html=True)
            st.markdown('<h4 style="color:#4895DB; font-weight:800; margin-bottom:5px;">COUNTERMOVEMENT JUMP</h4>', unsafe_allow_html=True)
            
            jc1, jc2 = st.columns([1.5, 3.5])
            p_cmj_hist = cmj_t0[(cmj_t0['Name'] == selected_athlete_prof) & (cmj_t0['Test Date'] <= curr_date_prof)].sort_values('Test Date')

            with jc1:
                baseline_cmj = cmj_t0[(cmj_t0['Name'] == selected_athlete_prof) & (cmj_t0['Week'] == 4)]
                if not baseline_cmj.empty and not p_cmj_hist.empty:
                    base_h = baseline_cmj.iloc[-1][cmj_col]
                    base_rsi = baseline_cmj.iloc[-1][rsi_col]
                    latest_cmj = p_cmj_hist.iloc[-1]
                    cur_h, cur_rsi = latest_cmj[cmj_col], latest_cmj[rsi_col]
                    p_diff_h = ((cur_h - base_h) / base_h * 100) if base_h > 0 else 0
                    p_diff_rsi = ((cur_rsi - base_rsi) / base_rsi * 100) if base_rsi > 0 else 0
                    color_h = "#28a745" if cur_h >= base_h else "#dc3545"
                    color_rsi = "#28a745" if cur_rsi >= base_rsi else "#dc3545"

                    sc1, sc2 = st.columns(2)
                    with sc1: st.markdown(f'<div style="text-align:center;"><div class="score-box" style="background-color:{color_h}; line-height:1.2; padding-top:15px; height:80px; width:100%;"><span style="font-size:18px;">{cur_h:.1f} cm</span><span style="font-size:10px; display:block; font-weight:bold; margin-top:2px;">CMJ HEIGHT</span></div></div>', unsafe_allow_html=True)
                    with sc2: st.markdown(f'<div style="text-align:center;"><div class="score-box" style="background-color:{color_rsi}; line-height:1.2; padding-top:15px; height:80px; width:100%;"><span style="font-size:18px;">{cur_rsi:.2f}</span><span style="font-size:10px; display:block; font-weight:bold; margin-top:2px;">RSI MOD</span></div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="info-box" style="text-align:center; margin-top:10px;"><p style="margin:0; font-size:11px; color:grey;"><b>% Change from Base:</b> CMJ: {p_diff_h:+.1f}% | RSI: {p_diff_rsi:+.1f}%</p><p style="margin:0; font-size:11px; color:grey;"><b>Base Values:</b> CMJ: {base_h:.1f} cm | RSI: {base_rsi:.2f}</p></div>', unsafe_allow_html=True)
                else:
                    st.warning("No data recorded.")

            with jc2:
                if not p_cmj_hist.empty:
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    fig.add_trace(go.Scatter(x=p_cmj_hist['Test Date'], y=p_cmj_hist[cmj_col], name="Jump Height", mode='lines+markers', line=dict(color='#1F517F', width=3)), secondary_y=False)
                    fig.add_trace(go.Scatter(x=p_cmj_hist['Test Date'], y=p_cmj_hist[rsi_col], name="RSI Modified", mode='lines+markers', line=dict(color='#4895DB', dash='dot', width=2)), secondary_y=True)
                    fig.update_layout(height=160, margin=dict(l=0, r=0, t=10, b=0), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), template="simple_white")
                    st.plotly_chart(fig, use_container_width=True, config=LOCKED_CONFIG, key="cmj_top_chart_t0")
                else:
                    st.info("No Countermovement Jump metrics recorded.")

            st.markdown('<hr style="display:block !important; margin:15px 0; border:0; border-top:1px solid #E5E5E7;" />', unsafe_allow_html=True)
            st.markdown('<h4 style="color:#4895DB; font-weight:800; margin-bottom:5px;">ASH SHOULDER: ISO I</h4>', unsafe_allow_html=True)
                
            p_ash_all = ash_t0[(ash_t0['Name'] == selected_athlete_prof) & (ash_t0['Test Date'] <= curr_date_prof)].sort_values('Test Date')
            if not p_ash_all.empty:
                ac1, ac2 = st.columns([1.5, 3.5])
                with ac1:
                    latest_date_ash = p_ash_all['Test Date'].iloc[-1]
                    today_ash_rows = p_ash_all[p_ash_all['Test Date'] == latest_date_ash]
                    row_i = today_ash_rows[today_ash_rows['Isometric Type'].str.contains('I', case=False, na=False)]
                    li = row_i.iloc[-1]['Peak Vertical Force [N] (L)'] if not row_i.empty else 0.0
                    ri = row_i.iloc[-1]['Peak Vertical Force [N] (R)'] if not row_i.empty else 0.0
                    asym_i = row_i.iloc[-1]['Peak Vertical Force [N] (Asym)(%)'] if not row_i.empty else 0.0
                    baseline_ash = p_ash_all[p_ash_all['Isometric Type'].str.contains('I', case=False, na=False)].head(1)
                    base_li = baseline_ash.iloc[-1]['Peak Vertical Force [N] (L)'] if not baseline_ash.empty else 0.0
                    base_ri = baseline_ash.iloc[-1]['Peak Vertical Force [N] (R)'] if not baseline_ash.empty else 0.0
                    pct_l = ((li - base_li) / base_li * 100) if base_li > 0 else 0
                    pct_r = ((ri - base_ri) / base_ri * 100) if base_ri > 0 else 0
                    color_ash_l = "#28a745" if li >= 100 else "#dc3545"
                    color_ash_r = "#28a745" if ri >= 100 else "#dc3545"

                    sc1, sc2 = st.columns(2)
                    with sc1: st.markdown(f'<div style="text-align:center;"><div class="score-box" style="background-color:{color_ash_l}; line-height:1.2; padding-top:15px; height:80px; width:100%;"><span style="font-size:18px;">{li:.0f} N</span><span style="font-size:10px; display:block; font-weight:bold; margin-top:2px;">LEFT</span></div></div>', unsafe_allow_html=True)
                    with sc2: st.markdown(f'<div style="text-align:center;"><div class="score-box" style="background-color:{color_ash_r}; line-height:1.2; padding-top:15px; height:80px; width:100%;"><span style="font-size:18px;">{ri:.0f} N</span><span style="font-size:10px; display:block; font-weight:bold; margin-top:2px;">RIGHT</span></div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="info-box" style="text-align:center; margin-top:10px;"><p style="margin:0; font-size:11px; color:grey;"><b>Asymmetry:</b> {asym_i:+.1f}%</p><p style="margin:0; font-size:11px; color:grey;"><b>% Change from Base:</b> L: {pct_l:+.1f}% | R: {pct_r:+.1f}%</p><p style="margin:0; font-size:11px; color:grey;"><b>Base Force:</b> L: {base_li:.0f} N | R: {base_ri:.0f} N</p></div>', unsafe_allow_html=True)
                with ac2:
                    p_ash_i_only = p_ash_all[p_ash_all['Isometric Type'].str.contains('I', case=False, na=False)]
                    if not p_ash_i_only.empty:
                        fig_ash = go.Figure()
                        fig_ash.add_trace(go.Scatter(x=p_ash_i_only['Test Date'], y=p_ash_i_only['Peak Vertical Force [N] (L)'], name="Left Peak Force", mode='lines+markers', line=dict(color='#4895DB', width=2.5)))
                        fig_ash.add_trace(go.Scatter(x=p_ash_i_only['Test Date'], y=p_ash_i_only['Peak Vertical Force [N] (R)'], name="Right Peak Force", mode='lines+markers', line=dict(color='#1F517F', width=2.5, dash='dash')))
                        fig_ash.update_layout(height=160, margin=dict(l=0, r=0, t=10, b=0), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), template="simple_white")
                        st.plotly_chart(fig_ash, use_container_width=True, config=LOCKED_CONFIG, key="ash_profile_chart_t0")
            else:
                st.info("No ASH shoulder test dataset recorded.")

            st.markdown('<hr style="display:block !important; margin:15px 0; border:0; border-top:1px solid #E5E5E7;" />', unsafe_allow_html=True)
            st.markdown('<h4 style="color:#4895DB; font-weight:800; margin-bottom:5px;">EXTERNAL ROTATION: ROM</h4>', unsafe_allow_html=True)
            
            p_er_hist = er_t0[(er_t0['Name'] == selected_athlete_prof) & (er_t0['Test Date'] <= curr_date_prof)].sort_values('Test Date')
            if not p_er_hist.empty:
                ec1, ec2 = st.columns([1.5, 3.5])
                with ec1:
                    baseline_er = p_er_hist.head(1)
                    if not baseline_er.empty:
                        base_l_rom = baseline_er.iloc[-1]['L Max ROM (°)']
                        base_r_rom = baseline_er.iloc[-1]['R Max ROM (°)']
                        latest_er = p_er_hist.iloc[-1]
                        cur_l_rom = latest_er['L Max ROM (°)']
                        cur_r_rom = latest_er['R Max ROM (°)']
                        cur_asym_rom = latest_er['ROM Asymmetry (%)']
                        rom_pct_l = ((cur_l_rom - base_l_rom) / base_l_rom * 100) if base_l_rom > 0 else 0
                        rom_pct_r = ((cur_r_rom - base_r_rom) / base_r_rom * 100) if base_r_rom > 0 else 0
                        color_er_l = "#28a745" if cur_l_rom >= 110 else "#ffc107" if 90 <= cur_l_rom <= 109 else "#dc3545"
                        color_er_r = "#28a745" if cur_r_rom >= 110 else "#ffc107" if 90 <= cur_r_rom <= 109 else "#dc3545"

                        sc1, sc2 = st.columns(2)
                        with sc1: st.markdown(f'<div style="text-align:center;"><div class="score-box" style="background-color:{color_er_l}; line-height:1.2; padding-top:15px; height:80px; width:100%;"><span style="font-size:18px;">{cur_l_rom:.1f}°</span><span style="font-size:10px; display:block; font-weight:bold; margin-top:2px;">LEFT</span></div></div>', unsafe_allow_html=True)
                        with sc2: st.markdown(f'<div style="text-align:center;"><div class="score-box" style="background-color:{color_er_r}; line-height:1.2; padding-top:15px; height:80px; width:100%;"><span style="font-size:18px;">{cur_r_rom:.1f}°</span><span style="font-size:10px; display:block; font-weight:bold; margin-top:2px;">RIGHT</span></div></div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-box" style="text-align:center; margin-top:10px;"><p style="margin:0; font-size:11px; color:grey;"><b>Asymmetry:</b> {cur_asym_rom:+.1f}%</p><p style="margin:0; font-size:11px; color:grey;"><b>% Change from Base:</b> L: {rom_pct_l:+.1f}% | R: {rom_pct_r:+.1f}%</p><p style="margin:0; font-size:11px; color:grey;"><b>Base ROM:</b> L: {base_l_rom:.1f}° | R: {base_r_rom:.1f}°</p></div>', unsafe_allow_html=True)
                with ec2:
                    fig_er = go.Figure()
                    fig_er.add_trace(go.Scatter(x=p_er_hist['Test Date'], y=p_er_hist['L Max ROM (°)'], name="Left Max ROM", mode='lines+markers', line=dict(color='#4895DB', width=2.5)))
                    fig_er.add_trace(go.Scatter(x=p_er_hist['Test Date'], y=p_er_hist['R Max ROM (°)'], name="Right Max ROM", mode='lines+markers', line=dict(color='#1F517F', width=2.5, dash='dash')))
                    fig_er.update_layout(height=160, margin=dict(l=0, r=0, t=10, b=0), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), template="simple_white")
                    st.plotly_chart(fig_er, use_container_width=True, config=LOCKED_CONFIG, key="er_profile_chart_t0")
            else:
                st.info("No External Rotation data recorded.")

            st.divider()
            p_ph = phase_t0[(phase_t0['Name'] == selected_athlete_prof) & (phase_t0['Date'] == curr_date_prof)].copy()
            if not p_ph.empty:
                st.markdown('<div class="section-header">Practice Phase Analysis</div>', unsafe_allow_html=True)
                fig_ph = make_subplots(specs=[[{"secondary_y": True}]])
                fig_ph.add_trace(go.Bar(x=p_ph['Phase'], y=p_ph['Player Load'], name="Player Load", marker_color='#4895DB'), secondary_y=False)
                fig_ph.add_trace(go.Scatter(x=p_ph['Phase'], y=p_ph['Total Jumps'], name="Total Jumps", line=dict(color='#1F517F', width=4), mode='lines+markers'), secondary_y=True)
                fig_ph.update_layout(height=350, showlegend=True, template="simple_white", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=0, r=0, t=30, b=0))
                fig_ph.update_yaxes(title_text="Player Load", secondary_y=False)
                fig_ph.update_yaxes(title_text="Total Jumps", secondary_y=True)
                st.plotly_chart(fig_ph, use_container_width=True, config=LOCKED_CONFIG, key="phase_analysis_t0")

        # ==========================================
        # --- TAB CLAUSE 2: PRACTICE SCORES --------
        # ==========================================
        elif st.session_state.active_tab_state == "Practice Scores":
            df_t1 = df_master.copy()

            c_gal1, c_gal2 = st.columns(2)
            with c_gal1: selected_session_gal = st.selectbox("Session Selection", session_list if session_list else ["No Sessions"], index=0, key="nav_sel_gal_t1")
            with c_gal2: pos_f_gal = st.selectbox("Position Filter", ["All Positions"] + sorted([p for p in df_t1['Position'].unique() if p != "N/A"]), key="nav_pos_gal_t1")
            
            display_df = df_t1[df_t1['Session_Name'] == selected_session_gal].copy()
            if not display_df.empty: curr_date_gal = display_df['Date'].iloc[0]

            if display_df is not None and not display_df.empty:
                if pos_f_gal != "All Positions": display_df = display_df[display_df['Position'] == pos_f_gal]
                athlete_names = sorted(display_df['Name'].unique())
                filtered_metrics_gal = [m for m in all_metrics if m not in ['High Jumps', 'Moderate Jumps', 'High Intensity Movement']]

                for i in range(0, len(athlete_names), 2):
                    cols = st.columns(2)
                    for j in range(2):
                        if i + j < len(athlete_names):
                            name = athlete_names[i + j]
                            p_session_row = display_df[display_df['Name'] == name].iloc[0]
                            p_full_g = df_t1[df_t1['Name'] == name]
                            daily_sums_g = p_full_g.groupby('Date')[all_metrics].sum().reset_index()
                            lb_sums = daily_sums_g[(daily_sums_g['Date'] >= curr_date_gal - timedelta(days=30)) & (daily_sums_g['Date'] <= curr_date_gal)]
                            
                            r_html = ""; t_grade = 0; c_metrics = 0
                            for k in filtered_metrics_gal:
                                val = p_session_row[k]
                                mx = lb_sums[k].max() if not lb_sums.empty else 1.0
                                avg = lb_sums[k].mean() if not lb_sums.empty else 1.0
                                g = math.ceil((val / mx) * 100) if mx > 0 else 0
                                t_grade += g; c_metrics += 1
                                diff = (val - avg) / avg if avg != 0 else 0
                                h_class = "class='bg-highlight-red'" if abs(diff) > 0.15 else ""
                                arr_val = f"<span class='arrow-red'>{'↑' if diff > 0.15 else '↓'}</span>" if abs(diff) > 0.15 else ""
                                r_html += f"<tr><td>{k}</td><td {h_class}>{val:.1f} {arr_val}</td><td>{mx:.1f}</td><td>{g}</td></tr>"
                            
                            sc_g = math.ceil(t_grade / c_metrics) if c_metrics > 0 else 0
                            with cols[j]: st.markdown(f'<div style="border:1px solid #E5E5E7; border-radius:15px; padding:15px; margin-bottom:20px; background-color:white;"><div style="display:flex; align-items:center; gap:10px;"><div style="flex:1.2; text-align:center;"><img src="{p_session_row["PhotoURL"]}" class="gallery-photo"><p style="font-weight:bold; font-size:15px; margin-top:8px; color:#333;">{name}</p></div><div style="flex:3;"><table class="scout-table"><thead><tr><th>Metric</th><th>Total</th><th>30d Max</th><th>Grade</th></tr></thead><tbody>{r_html}</tbody></table></div><div style="flex:1; text-align:center;"><div style="background-color:{get_flipped_gradient(sc_g)}; color:white; padding:10px; border-radius:12px; font-size:32px; font-weight:900;">{sc_g}</div></div></div></div>', unsafe_allow_html=True)

        # ==========================================
        # --- TAB CLAUSE 3: PRACTICE HISTORY -------
        # ==========================================
        elif st.session_state.active_tab_state == "Practice History":
            df_t4 = df_master.copy()
            st.markdown('<div class="section-header">Season History & Team Weekly Review</div>', unsafe_allow_html=True)
            sub_tabs = st.tabs(["Individual Review", "Team Weekly Review"])
            metrics_to_score = [m for m in all_metrics if m not in ['High Jumps', 'Moderate Jumps', 'High Intensity Movement']]

            with sub_tabs[0]:
                sel_ath_hist = st.selectbox("Select Athlete", sorted(df_t4['Name'].unique()), key="master_ath_sel_t4")
                p_full = df_t4[df_t4['Name'] == sel_ath_hist].copy()
                p_full['Date'] = pd.to_datetime(p_full['Date'])
                daily_raw = p_full.groupby(['Date', 'Week']).agg({**{m: 'sum' for m in metrics_to_score}, 'Session_Name': lambda x: ' | '.join(x.astype(str)), 'Session_Type': lambda x: ' | '.join(x.astype(str))}).reset_index().sort_values('Date')
            
                scores_list = []
                for idx, row in daily_raw.iterrows():
                    row_grades = []
                    lb_sums = daily_raw[(daily_raw['Date'] >= row['Date'] - timedelta(days=30)) & (daily_raw['Date'] <= row['Date'])]
                    for m in metrics_to_score:
                        val = row[m]
                        mx = lb_sums[m].max()
                        row_grades.append(math.ceil((val / mx) * 100) if mx > 0 else 0)
                    is_match = any(w in str(row['Session_Name']).upper() or w in str(row['Session_Type']).upper() for w in ['MATCH', 'GAME'])
                    scores_list.append({'Date': row['Date'], 'Display': row['Date'].strftime('%m/%d'), 'Score': int(math.ceil(sum(row_grades) / len(row_grades))), 'Type': 'Match' if is_match else 'Practice', 'Week': str(row['Week'])})
            
                master_df_history = pd.DataFrame(scores_list).reset_index(drop=True)
                st.markdown(f"### Full Season Performance: {sel_ath_hist}")
                if not master_df_history.empty:
                    fig_master = px.line(master_df_history, x='Display', y='Score', range_y=[0, 110])
                    prac_df = master_df_history[master_df_history['Type'] == 'Practice']
                    if not prac_df.empty: fig_master.add_trace(go.Scatter(x=prac_df['Display'], y=prac_df['Score'], mode='markers+text', text=prac_df['Score'], textposition="top center", name="Practice", marker=dict(size=8, color='#4895DB', line=dict(width=1, color='white'))))
                    match_df_line = master_df_history[master_df_history['Type'] == 'Match']
                    if not match_df_line.empty: fig_master.add_trace(go.Scatter(x=match_df_line['Display'], y=match_df_line['Score'], mode='markers+text', text=[f"<b>{s}</b>" for s in match_df_line['Score']], textposition="top center", name="Match Day", marker=dict(size=15, color='#1F517F', line=dict(width=3, color='#31333F')), textfont=dict(color='#31333F', size=13, weight='bold')))
                    for i in range(1, len(master_df_history)):
                        if master_df_history.iloc[i]['Week'] != master_df_history.iloc[i-1]['Week']:
                            fig_master.add_vline(x=i-0.5, line_dash="dash", line_color="#515154", opacity=0.3)
                            fig_master.add_annotation(x=i-0.5, y=0.98, yref="paper", text=f"Wk {master_df_history.iloc[i]['Week']}", showarrow=False, bgcolor="white", font=dict(size=10, color="#515154"), yanchor="top")
                    fig_master.update_layout(template="simple_white", height=480, xaxis=dict(type='category', title="Date"), yaxis=dict(range=[0, 120], automargin=True, tickvals=[0, 20, 40, 60, 80, 100]), legend=dict(orientation="h", yanchor="bottom", y=-0.2, x=0.5, xanchor="center"))
                    st.plotly_chart(fig_master, use_container_width=True, key=f"master_full_flow_{sel_ath_hist}_t4")

                st.markdown("### CMJ Baseline vs. Post-Match Recovery")
                if raw_cmj_df is not None and not raw_cmj_df.empty:
                    c_sync = raw_cmj_df.rename(columns={'Athlete': 'Name'}) if 'Athlete' in raw_cmj_df.columns else raw_cmj_df.copy()
                    ath_cmj_data = c_sync[c_sync['Name'] == sel_ath_hist].sort_values('Test Date')
                    baseline_cmj = ath_cmj_data[ath_cmj_data['Week'] == 4]
                    post_match_cmj = ath_cmj_data[ath_cmj_data['Week'] > 4] 
                    if not baseline_cmj.empty:
                        base_row = baseline_cmj.iloc[-1]
                        latest_post = post_match_cmj.iloc[-1] if not post_match_cmj.empty else None
                        if latest_post is not None:
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Baseline", f"{base_row[cmj_col]:.1f} cm")
                            m2.metric("Latest Jump", f"{latest_post[cmj_col]:.1f} cm", f"{((latest_post[cmj_col] - base_row[cmj_col]) / base_row[cmj_col]) * 100:+.1f}%")
                            m3.metric("RSI", f"{latest_post[rsi_col]:.2f}", f"{((latest_post[rsi_col] - base_row[rsi_col]) / base_row[rsi_col]) * 100:+.1f}%")
                        
                        st.markdown("#### Jump History & Match Context")
                        comparison_list = []
                        for _, row in post_match_cmj.iterrows():
                            jump_date = pd.to_datetime(row['Test Date'])
                            try:
                                prev_matches = df_t4[(df_t4['Name'] == sel_ath_hist) & (df_t4['Date'] < jump_date) & ((df_t4['Session_Name'].str.contains('Match|Game', case=False, na=False)) | (df_t4['Session_Type'].str.contains('Match|Game', case=False, na=False)))]
                                prev_match_name = prev_matches.sort_values('Date', ascending=False).iloc[0]['Session_Name']
                            except: prev_match_name = "N/A"
                            raw_diff = float(row[cmj_col]) - float(base_row[cmj_col])
                            comparison_list.append({"Date": jump_date.strftime('%m/%d/%Y'), "Prev Match": prev_match_name, "Jump Height": f"{row[cmj_col]:.1f} cm", "Raw Diff": raw_diff, "Display Diff": f"{raw_diff:+.1f} cm", "RSI": f"{row[rsi_col]:.2f}"})
                        
                        cmj_table_html = """<table class="scout-table" style="width:100%; border-collapse: collapse; text-align: center;"><thead><tr style="background-color: #f0f2f6; font-weight: bold;"><th style="padding: 10px; border: 1px solid #ddd;">Jump Date</th><th style="padding: 10px; border: 1px solid #ddd;">Previous Match</th><th style="padding: 10px; border: 1px solid #ddd;">Jump Height</th><th style="padding: 10px; border: 1px solid #ddd;">Vs. Baseline</th><th style="padding: 10px; border: 1px solid #ddd;">RSI</th></tr></thead><tbody>"""
                        for item in comparison_list:
                            cmj_table_html += f"""<tr><td style="padding: 10px; border: 1px solid #ddd;">{item['Date']}</td><td style="padding: 10px; border: 1px solid #ddd;">{item['Prev Match']}</td><td style="padding: 10px; border: 1px solid #ddd;">{item['Jump Height']}</td><td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: {'#28a745' if item['Raw Diff'] >= 0 else '#dc3545'};">{item['Display Diff']}</td><td style="padding: 10px; border: 1px solid #ddd;">{item['RSI']}</td></tr>"""
                        st.markdown(cmj_table_html + "</tbody></table>", unsafe_allow_html=True)
                        
                        fig_cmj = make_subplots(specs=[[{"secondary_y": True}]])
                        fig_cmj.add_trace(go.Scatter(x=ath_cmj_data['Test Date'], y=ath_cmj_data[cmj_col], name="Jump Height (cm)", mode='lines+markers', line=dict(color='#4895DB', width=3)), secondary_y=False)
                        fig_cmj.add_trace(go.Scatter(x=ath_cmj_data['Test Date'], y=ath_cmj_data[rsi_col], name="RSI-mod", mode='lines+markers', line=dict(color='#1F517F', width=2, dash='dot')), secondary_y=True)
                        fig_cmj.add_hline(y=base_row[cmj_col], line_dash="dash", line_color="red")
                        fig_cmj.update_layout(height=400, template="simple_white", margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=-0.3, x=0.5, xanchor="center"), xaxis=dict(title="Date", tickformat="%m/%d"))
                        st.plotly_chart(fig_cmj, use_container_width=True, key=f"integrated_cmj_final_{sel_ath_hist}_t4")

            with sub_tabs[1]:
                sel_week = st.selectbox("Select Review Week", sorted(df_t4['Week'].unique(), reverse=True), key="team_week_sel_t4")
                week_df = df_t4[df_t4['Week'] == sel_week].copy()
                ath_names = sorted(week_df['Name'].unique())
                
                for i in range(0, len(ath_names), 2):
                    cols = st.columns(2)
                    for j in range(2):
                        if i + j < len(ath_names):
                            name = ath_names[i+j]
                            p_all = df_t4[df_t4['Name'] == name].copy()
                            p_daily = p_all.groupby(['Date', 'Week'])[metrics_to_score].sum().reset_index().sort_values('Date')
                            w_daily = p_daily[p_daily['Week'].astype(str) == str(sel_week)]
                            
                            if not w_daily.empty:
                                card_scores = []
                                for _, r in w_daily.iterrows():
                                    r_grades = []
                                    lb = p_daily[(p_daily['Date'] >= r['Date'] - timedelta(days=30)) & (p_daily['Date'] <= r['Date'])]
                                    for m in metrics_to_score:
                                        mx = lb[m].max() if not lb.empty else 1.0
                                        r_grades.append(math.ceil((r[m] / mx) * 100) if mx > 0 else 0)
                                    card_scores.append({'Display': r['Date'].strftime('%m/%d'), 'Score': round(sum(r_grades)/len(r_grades), 0)})
                                
                                with cols[j]:
                                    st.markdown(f'<div style="border:1px solid #E5E5E7; border-top:4px solid #1F517F; border-radius:10px 10px 0 0; padding:10px; background:white;"><div style="display:flex; align-items:center; gap:12px;"><div style="width:60px; height:60px; border-radius:50%; background-color:white; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 1px 3px rgba(0,0,0,0.1);"><img src="{p_all.iloc[0]["PhotoURL"]}" style="width:100%; height:100%; object-fit:contain;"></div><p style="margin:0; font-weight:900; font-size:16px; color:#31333F;">{name}</p></div></div>', unsafe_allow_html=True)
                                    fig_p = px.line(pd.DataFrame(card_scores), x='Display', y='Score', markers=True, text='Score', range_y=[0, 140])
                                    fig_p.update_traces(textposition="top center", line=dict(color='#1F517F', width=3), marker=dict(size=8, color='#4895DB', line=dict(width=1, color='white')))
                                    fig_p.update_layout(height=200, margin=dict(l=15, r=15, t=30, b=10), template="simple_white", xaxis=dict(type='category', title=None), yaxis=dict(visible=False))
                                    st.plotly_chart(fig_p, use_container_width=True, key=f"team_card_{name}_{sel_week}_t4")

        # ==========================================
        # --- TAB CLAUSE 4: MATCH V. PRACTICE ------
        # ==========================================
        elif st.session_state.active_tab_state == "Match v. Practice":
            df_t5 = df_master.copy()
            match_t5 = match_master.copy()
            st.markdown('<div class="section-header">Season Preparation vs. Match Demands</div>', unsafe_allow_html=True)
            
            c_mode, c_sel = st.columns([1, 3])
            with c_mode: view_mode_t5 = st.radio("View Level", ["Team", "Position", "Individual"], horizontal=True, key="gp_view_mode_t5")
            
            with c_sel:
                if view_mode_t5 == "Individual":
                    gp_p = st.selectbox("Select Athlete", sorted(df_t5['Name'].unique()), key="gp_p_vf_t5")
                    main_filtered = df_t5[df_t5['Name'] == gp_p].copy()
                    match_filtered = match_t5[match_t5['Name'] == gp_p].copy()
                elif view_mode_t5 == "Position":
                    gp_pos = st.selectbox("Select Position Group", sorted(df_t5['Position'].unique().tolist()), key="gp_pos_vf_t5")
                    main_filtered = df_t5[df_t5['Position'] == gp_pos].copy()
                    match_filtered = match_t5[match_t5['Position'] == gp_pos].copy()
                else:
                    main_filtered = df_t5.copy()
                    match_filtered = match_t5.copy()

            def clean_gp_data(target_df):
                if target_df.empty: return target_df
                target_df = target_df.rename(columns={'Total Player Load': 'Player Load', 'PlayerLoad': 'Player Load'})
                cols_to_clean = ['Player Load', 'Explosive Efforts', 'Total Jumps', 'Jump Load', 'Duration']
                for c in cols_to_clean:
                    if c in target_df.columns: target_df[c] = pd.to_numeric(target_df[c], errors='coerce').fillna(0)
                if 'Duration' in target_df.columns: target_df['Duration'] = target_df['Duration'].apply(lambda x: x if x > 0 else 1)
                return target_df

            main_filtered = clean_gp_data(main_filtered)
            match_filtered = clean_gp_data(match_filtered)
            calc_cols = ['Player Load', 'Jump Load', 'Total Jumps', 'Explosive Efforts']

            if not main_filtered.empty and not match_filtered.empty:
                s_p_avg = main_filtered[main_filtered['Session_Type'] == 'Practice'][calc_cols + ['Duration']].mean()
                s_m_avg = match_filtered[calc_cols + ['Duration']].mean()
                
                overall_html = """<table style="width:100%; border-collapse: collapse; text-align: center; margin-top: 10px;"><tr style="background-color: #31333F; color: white; font-weight: bold;"><th style="padding: 12px; border: 1px solid #ddd;">Metric (Rate/Min)</th><th style="padding: 12px; border: 1px solid #ddd;">Full Season Practice Avg</th><th style="padding: 12px; border: 1px solid #ddd;">Full Season Match Avg</th><th style="padding: 12px; border: 1px solid #ddd;">Intensity Gap (%)</th></tr>"""
                for m in calc_cols:
                    p_rate = s_p_avg[m] / s_p_avg['Duration'] if s_p_avg['Duration'] > 0 else 0
                    m_rate = s_m_avg[m] / s_m_avg['Duration'] if s_m_avg['Duration'] > 0 else 0
                    overall_html += f"""<tr><td style="padding: 10px; border: 1px solid #ddd;"><b>{m}</b></td><td style="padding: 10px; border: 1px solid #ddd;">{p_rate:.2f}</td><td style="padding: 10px; border: 1px solid #ddd;">{m_rate:.2f}</td><td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">{(((m_rate - p_rate) / p_rate * 100) if p_rate > 0 else 0):+.1f}%</td></tr>"""
                st.markdown(overall_html + "</table>", unsafe_allow_html=True)

        # ==========================================
        # --- TAB CLAUSE 5: MATCH SUMMARY ----------
        # ==========================================
        elif st.session_state.active_tab_state == "Match Summary":
            match_t6 = match_master.copy()
            custom_colors = ['#4895DB', '#1F517F', '#515154', '#A52A2A', '#008080', '#6A1B9A', '#2E7D32']
    
            if st.session_state.is_printing:
                if st.button("Back to Editor", key="back_editor_btn_t6"):
                    st.session_state.is_printing = False
                    st.rerun()
            else:
                st.markdown('<div class="print-hide">', unsafe_allow_html=True)
                if st.button("Prepare PDF for Printing", key="prep_print_btn_t6"):
                    st.session_state.is_printing = True
                    st.rerun()
                match_list_t = match_t6.sort_values(['Date', 'Sheet_Order'])['Session_Name'].unique().tolist()
                if "matches_state" not in st.session_state: st.session_state.matches_state = match_list_t[-3:] if len(match_list_t) >= 3 else match_list_t
                st.session_state.matches_state = st.multiselect("Select Matches", match_list_t, default=st.session_state.matches_state, key="ms_select_t6")
                st.session_state.pos_state = st.selectbox("Filter by Position", ["All Positions"] + sorted(list(match_t6['Position'].unique())), key="pos_select_t6")
                st.markdown('</div>', unsafe_allow_html=True)

            if st.session_state.is_printing: st.markdown('<script>window.print();</script>', unsafe_allow_html=True)
            selected_matches = st.session_state.get("matches_state", [])
            pos_filter_t = st.session_state.get("pos_state", "All Positions")

            if selected_matches:
                m_map = {m: custom_colors[idx % len(custom_colors)] for idx, m in enumerate(selected_matches)}
                st.markdown('<div class="section-header">Athlete Match Performance Breakdown</div>', unsafe_allow_html=True)
                tourney_df = match_t6[match_t6['Session_Name'].isin(selected_matches)].sort_values(['Date', 'Sheet_Order'])
                if pos_filter_t != "All Positions": tourney_df = tourney_df[tourney_df['Position'] == pos_filter_t]

                for name in sorted(tourney_df['Name'].unique()):
                    ad = tourney_df[tourney_df['Name'] == name]
                    try: correct_photo = df_master[df_master['Name'] == name]['PhotoURL'].iloc[0]
                    except: correct_photo = "https://www.w3schools.com/howto/img_avatar.png"
            
                    st.markdown(f'<div class="player-row-container"><div class="player-divider"></div>', unsafe_allow_html=True)
                    side_cols = st.columns([1.5, 2])
                    with side_cols[0]:
                        card_start = f"""<div style="display:flex; align-items:center; gap:12px; padding:10px; background:#f8f9fa; border-bottom:2px solid #515154;"><img src="{correct_photo}" class="gallery-photo" style="width:65px; height:65px;"><div><p style="margin:0; font-weight:900; color:#1D1D1F; font-size:18px;">{name}</p><p style="margin:0; color:#4895DB; font-weight:700; font-size:16px;">{ad['Position'].iloc[0]}</p></div></div><div style="padding:5px;"><table class="scout-table" style="margin-bottom:0;"><thead><tr><th>Match</th><th>Jumps</th><th>Load</th><th>Efforts</th></tr></thead><tbody>"""
                        for _, r in ad.iterrows():
                            card_start += f"<tr><td style='font-weight:700; font-size:11px;'>{r['Session_Name']}</td><td>{int(r['Total Jumps'])}</td><td>{r['Player Load']:.0f}</td><td>{r['Explosive Efforts']:.0f}</td></tr>"
                        card_start += f"<tr style='background:#4895DB; color:white; font-weight:900;'><td>TOTAL</td><td>{int(ad['Total Jumps'].sum())}</td><td>{ad['Player Load'].sum():.0f}</td><td>{ad['Explosive Efforts'].sum():.0f}</td></tr></tbody></table></div>"
                        st.markdown(card_start, unsafe_allow_html=True)
            
                    with side_cols[1]:
                        fig_ath = make_subplots(specs=[[{"secondary_y": True}]])
                        for _, r in ad.iterrows():
                            fig_ath.add_trace(go.Bar(name=r['Session_Name'], x=['Total Jumps', 'Explosive Efforts'], y=[r['Total Jumps'], r['Explosive Efforts']], marker_color=m_map[r['Session_Name']], offsetgroup=r['Session_Name']), secondary_y=False)
                            fig_ath.add_trace(go.Bar(name=f"Load ({r['Session_Name']})", x=['Player Load'], y=[r['Player Load']], marker=dict(color=m_map[r['Session_Name']], opacity=0.3), showlegend=False, offsetgroup=r['Session_Name']), secondary_y=True)
                        fig_ath.update_layout(barmode='group', height=260, margin=dict(l=10, r=10, t=10, b=80), template="simple_white", font=dict(color="#333333", size=10), legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5), yaxis=dict(showgrid=False, title="Jumps / Efforts"), yaxis2=dict(showgrid=False, title="Player Load", overlaying='y', side='right'))
                        st.plotly_chart(fig_ath, use_container_width=True, config=LOCKED_CONFIG, key=f"match_breakdown_{name}")
                    st.markdown('</div>', unsafe_allow_html=True)

        # ==========================================
        # --- TAB CLAUSE 6: POSITION ANALYSIS ------
        # ==========================================
        elif st.session_state.active_tab_state == "Position Analysis":
            df_t7 = df_master.copy()
            st.markdown('<div class="section-header">Positional Performance Trends</div>', unsafe_allow_html=True)
            pos_filter_an = st.selectbox("Select Position to Analyze", sorted([p for p in df_t7['Position'].unique() if p != "N/A"]), key="pos_an_filt_main_t7")
            
            max_wk = df_t7['Week'].max()
            rec_4 = list(range(max(0, int(max_wk) - 3), int(max_wk) + 1))
            tr_df = df_t7[(df_t7['Week'].isin(rec_4)) & (df_t7['Position'] == pos_filter_an)]
            players_in_pos = sorted(tr_df['Name'].unique())
            
            if players_in_pos:
                tr_metrics = ["Player Load", "Estimated Distance (y)", "Explosive Efforts", "Total Jumps"]
                pos_weekly_sums = tr_df.groupby(['Week', 'Name'])[tr_metrics].sum().reset_index()
                pos_avg_weekly_total = pos_weekly_sums[tr_metrics].max()

                for name in players_in_pos:
                    p_data = tr_df[tr_df['Name'] == name]
                    p_weekly_sums = p_data.groupby('Week')[tr_metrics].sum().reset_index()
                    p_avg_weekly_total = p_weekly_sums[tr_metrics].max()

                    c_card1, c_card2 = st.columns([1.5, 3], gap="large")
                    with c_card1:
                        st.markdown(f"""<div class="player-row-container" style="padding: 20px; border: 1px solid #E5E5E7; border-radius:15px; background:white; margin-bottom: 0px;"><div style="text-align:center; padding:15px; background:#f8f9fa; border-bottom:2px solid #515154; border-radius: 12px;"><div style="width:90px; height:90px; border-radius:50%; background-color: white; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 3px solid #4895DB; margin: 0 auto 10px auto;"><img src="{p_data["PhotoURL"].iloc[0]}" style="width:100%; height:100%; object-fit: contain;"></div><p style="margin:0; font-weight:900; color:#1D1D1F; font-size:18px;">{name}</p><p style="margin:0; font-size:12px; color:grey;">Weekly Max Volume</p></div><table class="scout-table" style="width:100%; margin-top:15px;"><thead><tr><th>Metric</th><th>Athlete Max</th><th>Pos. Max Total</th></tr></thead><tbody><tr><td style="font-weight:700;">Player Load</td><td>{p_avg_weekly_total['Player Load']:.0f}</td><td>{pos_avg_weekly_total['Player Load']:.0f}</td></tr><tr><td style="font-weight:700;">Est. Dist (y)</td><td>{p_avg_weekly_total['Estimated Distance (y)']:.0f}</td><td>{pos_avg_weekly_total['Estimated Distance (y)']:.0f}</td></tr><tr><td style="font-weight:700;">Explosive</td><td>{p_avg_weekly_total['Explosive Efforts']:.0f}</td><td>{pos_avg_weekly_total['Explosive Efforts']:.0f}</td></tr><tr><td style="font-weight:700;">Total Jumps</td><td>{p_avg_weekly_total['Total Jumps']:.0f}</td><td>{pos_avg_weekly_total['Total Jumps']:.0f}</td></tr></tbody></table></div>""", unsafe_allow_html=True)

                    with c_card2:
                        st.write("<div style='height: 25px;'></div>", unsafe_allow_html=True)
                        t_cols = st.columns(2) 
                        for i, m in enumerate(tr_metrics):
                            with t_cols[i % 2]:
                                fig_t = go.Figure()
                                p_t = p_data.groupby('Week')[m].sum().reset_index()
                                fig_t.add_trace(go.Scatter(x=p_t['Week'], y=p_t[m], name="Athlete", line=dict(color='#4895DB', width=4), mode='lines+markers'))
                                g_t = tr_df.groupby(['Week', 'Name'])[m].sum().reset_index().groupby('Week')[m].max().reset_index()
                                fig_t.add_trace(go.Scatter(x=g_t['Week'], y=g_t[m], name="Pos. Max", line=dict(color='#1F517F', dash='dash', width=2), mode='lines'))
                                
                                fig_t.update_layout(
                                    title=dict(
                                        text=f"<b>Weekly Trend: {m.split(' (')[0]}</b>", 
                                        font=dict(size=12), 
                                        x=0.5,
                                        y=0.95
                                    ), 
                                    xaxis=dict(
                                        dtick=1, 
                                        showgrid=False, 
                                        title="Week"
                                    ), 
                                    yaxis=dict(
                                        showgrid=True, 
                                        gridcolor='#F5F5F7', 
                                        rangemode='tozero',
                                        title=m
                                    ), 
                                    height=270, 
                                    margin=dict(l=20, r=20, t=50, b=65), 
                                    showlegend=True, 
                                    legend=dict(
                                        orientation="h", 
                                        y=-0.4, 
                                        x=0.5, 
                                        xanchor="center"
                                    ), 
                                    template="simple_white"
                                )
                                st.plotly_chart(fig_t, use_container_width=True, config=LOCKED_CONFIG, key=f"trend_{name}_{m}_t7")
                    st.write("<div style='height: 30px;'></div>", unsafe_allow_html=True)

        # ==========================================
        # --- TAB CLAUSE 7: PHASE ANALYSIS ---------
        # ==========================================
        elif st.session_state.active_tab_state == "Phase Analysis":
            st.markdown('<div class="section-header">Work Index Matrix & Drill Utilization</div>', unsafe_allow_html=True)
            if phase_master is not None and not phase_master.empty:
                working_matrix = phase_master.copy()
                for col in ['Position', 'Name', 'Phase']:
                    if col in working_matrix.columns: working_matrix[col] = working_matrix[col].astype(str).str.strip()
                if 'Phase' in working_matrix.columns: working_matrix['Phase'] = working_matrix['Phase'].replace(phase_map)

                time_col = 'Duration'
                index_metrics = ['Player Load', 'Total Jumps', 'Explosive Efforts']
                working_matrix[time_col] = pd.to_numeric(working_matrix[time_col], errors='coerce').fillna(0)
                session_summary = working_matrix.groupby(['Date', 'Phase']).agg({time_col: 'max', **{m: 'mean' for m in index_metrics}}).reset_index()
                master_averages = session_summary.groupby('Phase').agg({time_col: 'mean', **{m: 'mean' for m in index_metrics}}).to_dict('index')

                f_col1, f_col2, f_col3, f_col4 = st.columns(4)
                with f_col1:
                    view_mode_t8 = st.radio("Group By", ["Position", "Individual"], horizontal=True, key="wi_view_t8")
                    metric_mode = st.radio("Data Mode", ["Work Index (per minute)", "Total Volume"], horizontal=True, key="wi_mode_t8")
                with f_col2:
                    if view_mode_t8 == "Position":
                        sel_sub_filter = st.selectbox("Select Position", ["All Positions"] + sorted([p for p in working_matrix['Position'].unique() if p not in ["nan", "N/A"]]), key="wi_sub_pos_t8")
                    else:
                        sel_sub_filter = st.selectbox("Select Player", ["All Players"] + sorted(working_matrix['Name'].unique()), key="wi_sub_ath_t8")
                with f_col3: sel_phase = st.selectbox("Select Drill/Phase", ["All Phases"] + sorted(working_matrix['Phase'].unique().tolist()), key="wi_phase_filter_t8")
                with f_col4: sel_date = st.selectbox("Select Date", ["Season Avg"] + sorted([d.strftime('%Y-%m-%d') for d in working_matrix['Date'].dropna().unique()], reverse=True), key="wi_volume_date_t8")

                filtered_df = working_matrix.copy()
                if view_mode_t8 == "Position" and sel_sub_filter != "All Positions": filtered_df = filtered_df[filtered_df['Position'] == sel_sub_filter]
                elif view_mode_t8 == "Individual" and sel_sub_filter != "All Players": filtered_df = filtered_df[filtered_df['Name'] == sel_sub_filter]
                if sel_phase != "All Phases": filtered_df = filtered_df[filtered_df['Phase'] == sel_phase]
                display_df = filtered_df[filtered_df['Date'] == pd.to_datetime(sel_date)].copy() if sel_date != "Season Avg" else filtered_df.copy()

                group_keys = ['Position', 'Phase'] if view_mode_t8 == "Position" else ['Name', 'Position', 'Phase']
                matrix_df = display_df.groupby(group_keys).agg({**{m: 'mean' for m in index_metrics}, time_col: 'mean'}).reset_index()

                if sel_date == "Season Avg":
                    for idx, row in matrix_df.iterrows():
                        if row['Phase'] in master_averages: matrix_df.at[idx, time_col] = master_averages[row['Phase']][time_col]

                h_load, h_jumps, h_expl = ("Total Load", "Total Jumps", "Total Efforts") if metric_mode == "Total Volume" else ("Player Load/Min", "Jumps/Min", "Explosive Efforts/Min")
                fmt = "{:.0f}" if metric_mode == "Total Volume" else "{:.2f}"

                st.markdown(f"### {metric_mode}")
                sort_col = 'Position' if view_mode_t8 == "Position" else 'Name'
                matrix_df = matrix_df.sort_values([sort_col, 'Phase'])

                matrix_html = f"""<table class="scout-table"><tr style="background-color: #31333F; color: white; font-weight: bold;"><th style="padding: 12px; border: 1px solid #ddd;">{sort_col}</th><th style="padding: 12px; border: 1px solid #ddd;">Phase</th><th style="padding: 12px; border: 1px solid #ddd;">Mins</th><th style="padding: 12px; border: 1px solid #ddd;">{h_load}</th><th style="padding: 12px; border: 1px solid #ddd;">{h_jumps}</th><th style="padding: 12px; border: 1px solid #ddd;">{h_expl}</th></tr>"""
                for _, row in matrix_df.iterrows():
                    d_mins = row[time_col]
                    matrix_html += f"""<tr><td style="padding: 10px; border: 1px solid #ddd;">{row[sort_col]}</td><td style="padding: 10px; border: 1px solid #ddd;">{row['Phase']}</td><td style="padding: 10px; border: 1px solid #ddd;">{d_mins:.1f}</td><td style="padding: 10px; border: 1px solid #ddd;">{fmt.format(row['Player Load'] if metric_mode == "Total Volume" else (row['Player Load'] / d_mins if d_mins > 0 else 0))}</td><td style="padding: 10px; border: 1px solid #ddd;">{fmt.format(row['Total Jumps'] if metric_mode == "Total Volume" else (row['Total Jumps'] / d_mins if d_mins > 0 else 0))}</td><td style="padding: 10px; border: 1px solid #ddd;">{fmt.format(row['Explosive Efforts'] if metric_mode == "Total Volume" else (row['Explosive Efforts'] / d_mins if d_mins > 0 else 0))}</td></tr>"""
                st.markdown(matrix_html + "</table>", unsafe_allow_html=True)
                
                st.markdown("### Drill Frequency (Season Total)")
                drill_stats = phase_master.copy()
                drill_stats['Phase'] = drill_stats['Phase'].replace(phase_map)
                freq_html = """<table class="scout-table"><tr style="background-color: #f0f2f6; font-weight: bold;"><th style="padding: 10px; border: 1px solid #ddd;">Drill/Phase</th><th style="padding: 10px; border: 1px solid #ddd;">Season Frequency</th></tr>"""
                for _, row in drill_stats.groupby('Phase')['Number of Times'].sum().reset_index().sort_values('Number of Times', ascending=False).iterrows():
                    freq_html += f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>{row['Phase']}</td><td style='padding: 8px; border: 1px solid #ddd;'>{row['Number of Times']:.0f}</td></tr>"
                st.markdown(freq_html + "</table>", unsafe_allow_html=True)

        # ==========================================
        # --- TAB CLAUSE 8: PRACTICE PLANNER -------
        # ==========================================
        elif st.session_state.active_tab_state == "Practice Planner":
            st.markdown('<div class="section-header">Practice Phase Analysis & Planner</div>', unsafe_allow_html=True)
            if phase_master is not None and not phase_master.empty:
                working_planner = phase_master.copy()
                time_col = 'Duration' 
                
                if time_col not in working_planner.columns:
                    st.error(f"Column '{time_col}' not found.")
                else:
                    working_planner['Phase'] = working_planner['Phase'].replace(phase_map)
                    working_planner = working_planner[working_planner[time_col] > 0].dropna(subset=[time_col])
                    plan_metrics = ['Player Load', 'Total Jumps', 'Explosive Efforts', 'Estimated Distance (y)']
                    for m in plan_metrics: working_planner[f'{m}_Rate'] = working_planner[m] / working_planner[time_col]

                    s_col1, s_col2 = st.columns(2)
                    with s_col1: plan_level = st.radio("Select Planning Level", ["Team Overall", "By Position", "By Athlete"], horizontal=True, key="planner_level_refined_t9")
                    
                    if plan_level == "Team Overall":
                        planner_target_df = working_planner.copy()
                        display_label = "Team Overall"
                    elif plan_level == "By Position":
                        with s_col2: pos_choice = st.selectbox("Select Position", sorted([p for p in working_planner['Position'].unique() if pd.notna(p)]), key="planner_pos_refined_t9")
                        planner_target_df = working_planner[working_planner['Position'] == pos_choice]
                        display_label = f"Position: {pos_choice}"
                    else:
                        with s_col2: ath_choice = st.selectbox("Select Athlete", sorted(working_planner['Name'].unique()), key="planner_ath_refined_t9")
                        planner_target_df = working_planner[working_planner['Name'] == ath_choice]
                        display_label = f"Athlete: {ath_choice}"

                    selected_build = st.multiselect(f"Select Drills for {display_label}", sorted(planner_target_df['Phase'].unique()), key="planner_multi_refined_t9")
                    if selected_build:
                        build_stats = planner_target_df.groupby('Phase').agg({time_col: 'mean'}).reset_index()
                        st.write("Set planned drill durations (minutes):")
                        dur_cols = st.columns(min(len(selected_build), 4))
                        durations = {}
                        for idx, phase in enumerate(selected_build):
                            with dur_cols[idx % 4]:
                                avg_t = build_stats[build_stats['Phase'] == phase][time_col].iloc[0]
                                durations[phase] = st.number_input(f"{phase}", value=float(round(avg_t, 0)), step=1.0, key=f"dur_ref_{phase}_t9")

                        if plan_level != "Team Overall":
                            t_build = planner_target_df.groupby('Phase')[[f'{m}_Rate' for m in plan_metrics]].mean().reset_index().set_index('Phase').loc[selected_build].reset_index()
                            m1, m2, m3, m4, m5 = st.columns(5)
                            m1.metric("Total Time", f"{sum(durations.values()):.0f} min")
                            m2.metric("Proj. Load", f"{sum(durations[p] * t_build[t_build['Phase'] == p]['Player Load_Rate'].iloc[0] for p in selected_build):.1f}")
                            m3.metric("Proj. Jumps", f"{int(sum(durations[p] * t_build[t_build['Phase'] == p]['Total Jumps_Rate'].iloc[0] for p in selected_build))}")
                            m4.metric("Proj. Efforts", f"{int(sum(durations[p] * t_build[t_build['Phase'] == p]['Explosive Efforts_Rate'].iloc[0] for p in selected_build))}")
                            m5.metric("Proj. Dist (y)", f"{int(sum(durations[p] * t_build[t_build['Phase'] == p]['Estimated Distance (y)_Rate'].iloc[0] for p in selected_build))}")

                        if plan_level != "By Athlete":
                            st.markdown(f"#### Individual Athlete Projections")
                            ath_rates = planner_target_df.groupby(['Name', 'Phase'])[[f'{m}_Rate' for m in plan_metrics]].mean().reset_index()
                            ath_projections = []
                            for athlete in sorted(planner_target_df['Name'].unique()):
                                a_data = ath_rates[ath_rates['Name'] == athlete]
                                a_totals = {m: 0.0 for m in plan_metrics}
                                for phase in selected_build:
                                    p_rate = a_data[a_data['Phase'] == phase]
                                    if not p_rate.empty:
                                        for m in plan_metrics: a_totals[m] += durations[phase] * p_rate[f'{m}_Rate'].iloc[0]
                                if sum(a_totals.values()) > 0:
                                    ath_projections.append({'Athlete': athlete, 'Proj. Load': round(a_totals['Player Load'], 1), 'Proj. Jumps': int(a_totals['Total Jumps']), 'Proj. Efforts': int(a_totals['Explosive Efforts']), 'Proj. Dist (y)': int(a_totals['Estimated Distance (y)'])})
                            if ath_projections: st.dataframe(pd.DataFrame(ath_projections).sort_values('Proj. Load', ascending=False), use_container_width=True, hide_index=True)

                        st.markdown("#### Practice Intensity Flow (Rate per Minute)")
                        g_build = planner_target_df.groupby('Phase')[[f'{m}_Rate' for m in plan_metrics]].mean().reset_index().set_index('Phase').loc[selected_build].reset_index()
                        fig_flow = make_subplots(specs=[[{"secondary_y": True}]])
                        colors = {'Player Load': '#515154', 'Total Jumps': '#1F517F', 'Explosive Efforts': '#A52A2A', 'Estimated Distance (y)': '#4895DB'}
                        for m in plan_metrics:
                            is_distance = (m == 'Estimated Distance (y)')
                            fig_flow.add_trace(go.Scatter(x=g_build['Phase'], y=g_build[f'{m}_Rate'], name=f"{m} (Right Axis)" if is_distance else m, mode='lines+markers', line=dict(color={m: colors[m] for m in plan_metrics}[m], width=3, shape='spline'), marker=dict(size=8)), secondary_y=is_distance)
                        fig_flow.update_layout(height=450, template="simple_white", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5), margin=dict(l=10, r=10, t=50, b=10), xaxis_title="Practice Phase")
                        fig_flow.update_yaxes(title_text="Load / Jumps / Efforts", secondary_y=False)
                        fig_flow.update_yaxes(title_text="Yards per Minute", secondary_y=True, showgrid=False)
                        st.plotly_chart(fig_flow, use_container_width=True, config=LOCKED_CONFIG, key="planner_flow_chart_t9")

    except Exception as e:
        st.error(f"Sync Error: {e}")
