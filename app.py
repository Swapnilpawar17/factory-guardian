# ============================================
# FACTORY GUARDIAN - Protected App with Login
# ============================================
# This wraps dashboard.py with authentication
# Deploy THIS file instead of dashboard.py
# ============================================

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# ============================================
# PAGE CONFIG (must be first Streamlit command)
# ============================================
st.set_page_config(
    page_title="Factory Guardian",
    page_icon="🏭",
    layout="wide"
)

# ============================================
# LOAD AUTH CONFIG
# ============================================
try:
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)
except FileNotFoundError:
    st.error("❌ config.yaml not found. Create it with user credentials.")
    st.stop()

# ============================================
# CREATE AUTHENTICATOR
# ============================================
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# ============================================
# LOGIN PAGE
# ============================================
name, authentication_status, username = authenticator.login(
    location='main',
    fields={
        'Form name': '🏭 Factory Guardian Login',
        'Username': 'Username',
        'Password': 'Password',
        'Login': 'Login'
    }
)

# ============================================
# HANDLE AUTH STATUS
# ============================================
if authentication_status == False:
    st.error('❌ Username or password is incorrect')
    st.markdown("---")
    st.markdown("""
    ### 🏭 Factory Guardian — Predictive Maintenance AI
    
    Predict machine failures **48-72 hours** before they happen.
    
    **Demo Credentials:**
    - Username: `admin`
    - Password: `admin123`
    
    ---
    
    **Features:**
    - 📊 Real-time machine health monitoring
    - 🤖 AI-powered failure prediction
    - 📱 Telegram & Email alerts
    - 💰 Savings calculator
    
    **Contact:** [Your Email/Phone]
    """)

elif authentication_status == None:
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h1>🏭 Factory Guardian</h1>
        <p style="color: gray; font-size: 1.2rem;">Predictive Maintenance AI for Indian Manufacturers</p>
        <p style="color: gray;">Login to access your dashboard</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        ### 📊 Monitor
        Real-time health scores for all your machines
        """)
    with col2:
        st.markdown("""
        ### 🤖 Predict
        AI predicts failures 48-72 hours in advance
        """)
    with col3:
        st.markdown("""
        ### 💰 Save
        Prevent ₹3-5 Lakh losses per incident
        """)

elif authentication_status:
    # ============================================
    # USER IS LOGGED IN — SHOW DASHBOARD
    # ============================================
    
    # Sidebar: user info + logout
    st.sidebar.markdown(f"### 👤 Welcome, {name}!")
    authenticator.logout('Logout', 'sidebar')
    st.sidebar.markdown("---")
    
    # ============================================
    # IMPORT AND RUN THE FULL DASHBOARD CODE
    # ============================================
    # Instead of duplicating code, we import the 
    # dashboard logic. But since Streamlit re-runs
    # the whole file, we include key parts here.
    
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import datetime
    import os
    from groq import Groq
    
    def get_secret(key_name):
        try:
            return st.secrets[key_name]
        except Exception:
            pass
        try:
            from dotenv import load_dotenv
            load_dotenv()
            return os.getenv(key_name)
        except Exception:
            pass
        return None

    @st.cache_data
    def load_data(file):
        data = pd.read_csv(file)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        return data

    def calculate_health_score(machine_data):
        baseline = machine_data.head(max(5, len(machine_data) // 4))
        current = machine_data.tail(max(3, len(machine_data) // 6))
        scores = []
        for col in ['vibration_g', 'temperature_c', 'power_kw']:
            b = baseline[col].mean()
            c = current[col].mean()
            change = abs(c - b) / b if b > 0 else 0
            scores.append(max(0, 100 - change * 500))
        b_p = baseline['pressure_bar'].mean()
        c_p = current['pressure_bar'].mean()
        p_change = abs(c_p - b_p) / b_p if b_p > 0 else 0
        scores.append(max(0, 100 - p_change * 500))
        return round(sum(scores) / len(scores), 1)

    def get_alert_level(health):
        if health < 40: return "CRITICAL", "🔴", "critical"
        elif health < 70: return "WARNING", "🟡", "warning"
        else: return "NORMAL", "🟢", "normal"

    # Load data
    uploaded = st.sidebar.file_uploader("Upload CSV", type="csv")
    if uploaded:
        data = load_data(uploaded)
    else:
        try:
            data = load_data("sensor_data.csv")
        except:
            st.error("No data file found.")
            st.stop()

    machines = data['machine_id'].unique()
    
    # Header
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem;">
        <h1>🏭 Factory Guardian</h1>
        <p style="color: gray;">Logged in as: {name} ({username})</p>
    </div>
    """, unsafe_allow_html=True)

    # Fleet Overview Cards
    st.markdown("### 🏠 Fleet Overview")
    cols = st.columns(len(machines))
    
    for i, mid in enumerate(machines):
        m_data = data[data['machine_id'] == mid]
        m_type = m_data['machine_type'].iloc[0]
        health = calculate_health_score(m_data)
        level, icon, css = get_alert_level(health)
        
        colors = {"critical": "#ff4444", "warning": "#ffaa00", "normal": "#00C851"}
        with cols[i]:
            st.markdown(f"""
            <div style="background: {colors[css]}; color: white; padding: 1rem; 
                        border-radius: 10px; text-align: center; margin: 0.25rem;">
                <h4>{icon} {mid}</h4>
                <p style="margin: 0; font-size: 0.8rem;">{m_type}</p>
                <h2 style="margin: 5px 0;">{health}</h2>
                <p style="margin: 0;"><strong>{level}</strong></p>
            </div>
            """, unsafe_allow_html=True)

    # Machine selector
    st.markdown("---")
    selected = st.selectbox("🔍 Select Machine for Details", machines,
                            format_func=lambda x: f"{x} ({data[data['machine_id']==x]['machine_type'].iloc[0]})")
    
    m_data = data[data['machine_id'] == selected]
    health = calculate_health_score(m_data)
    level, icon, _ = get_alert_level(health)

    if level == "CRITICAL":
        st.error(f"{icon} **CRITICAL** — {selected} — Health: {health}/100")
    elif level == "WARNING":
        st.warning(f"{icon} **WARNING** — {selected} — Health: {health}/100")
    else:
        st.success(f"{icon} **NORMAL** — {selected} — Health: {health}/100")

    # Charts
    tab1, tab2, tab3, tab4 = st.tabs(["📳 Vibration", "🌡️ Temperature", "💨 Pressure", "⚡ Power"])
    
    chart_info = [
        (tab1, 'vibration_g', '#ff6b6b', 'Vibration (g)'),
        (tab2, 'temperature_c', '#ffa502', 'Temperature (°C)'),
        (tab3, 'pressure_bar', '#1e90ff', 'Pressure (bar)'),
        (tab4, 'power_kw', '#2ed573', 'Power (kW)')
    ]
    
    for tab, col, color, label in chart_info:
        with tab:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=m_data['timestamp'], y=m_data[col],
                                     mode='lines+markers', line=dict(color=color, width=3)))
            baseline_val = m_data[col].head(5).mean()
            fig.add_hline(y=baseline_val, line_dash="dash", line_color="green",
                          annotation_text=f"Baseline: {baseline_val:.2f}")
            fig.update_layout(yaxis_title=label, height=350, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    # AI Analysis
    st.markdown("---")
    if st.button("🤖 Run AI Analysis", type="primary", use_container_width=True):
        api_key = get_secret('GROQ_API_KEY')
        if not api_key:
            st.error("Add GROQ_API_KEY to secrets")
        else:
            with st.spinner("Analyzing..."):
                try:
                    client = Groq(api_key=api_key)
                    resp = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Expert maintenance engineer for Indian factories."},
                            {"role": "user", "content": f"""Analyze this machine:
{m_data.tail(8).to_string(index=False)}
Baseline: {m_data.head(5).to_string(index=False)}
Give: status, prediction, 3 concerns, 3 actions, savings in ₹."""}
                        ],
                        temperature=0.3, max_tokens=1000
                    )
                    st.markdown(resp.choices[0].message.content)
                    st.success("✅ Analysis complete")
                except Exception as e:
                    st.error(f"Failed: {e}")