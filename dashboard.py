# ============================================
# FACTORY GUARDIAN - Multi-Machine Dashboard
# ============================================
# Version 4.0 - Multiple machines + Fleet overview
# ============================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os
from groq import Groq


# ============================================
# HELPER: Get API keys
# ============================================
def get_secret(key_name):
    try:
        return st.secrets[key_name]
    except Exception:
        pass
    try:
        from dotenv import load_dotenv
        load_dotenv()
        value = os.getenv(key_name)
        if value:
            return value
    except Exception:
        pass
    return None


# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="Factory Guardian - Predictive Maintenance",
    page_icon="🏭",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A5F;
        text-align: center;
        padding: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: gray;
        margin-bottom: 1rem;
    }
    .machine-card-critical {
        background: linear-gradient(135deg, #ff4444, #cc0000);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .machine-card-warning {
        background: linear-gradient(135deg, #ffaa00, #ff8800);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .machine-card-normal {
        background: linear-gradient(135deg, #00C851, #007E33);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================
# DATA FUNCTIONS
# ============================================
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
        baseline_avg = baseline[col].mean()
        current_avg = current[col].mean()
        if baseline_avg > 0:
            change = abs(current_avg - baseline_avg) / baseline_avg
            score = max(0, 100 - (change * 500))
        else:
            score = 100
        scores.append(score)

    baseline_pressure = baseline['pressure_bar'].mean()
    current_pressure = current['pressure_bar'].mean()
    if baseline_pressure > 0:
        pressure_change = abs(current_pressure - baseline_pressure) / baseline_pressure
        pressure_score = max(0, 100 - (pressure_change * 500))
    else:
        pressure_score = 100
    scores.append(pressure_score)

    return round(sum(scores) / len(scores), 1)


def get_alert_level(health_score):
    if health_score < 40:
        return "CRITICAL", "🔴", "critical"
    elif health_score < 70:
        return "WARNING", "🟡", "warning"
    else:
        return "NORMAL", "🟢", "normal"


def get_z_scores(machine_data):
    baseline = machine_data.head(max(5, len(machine_data) // 4))
    current = machine_data.tail(max(3, len(machine_data) // 6))

    z_scores = {}
    for col in ['vibration_g', 'temperature_c', 'pressure_bar', 'power_kw']:
        b_mean = baseline[col].mean()
        b_std = baseline[col].std()
        c_mean = current[col].mean()

        z = (c_mean - b_mean) / b_std if b_std > 0 else 0
        change_pct = ((c_mean - b_mean) / b_mean) * 100 if b_mean > 0 else 0

        z_scores[col] = {
            'baseline': round(b_mean, 2),
            'current': round(c_mean, 2),
            'z_score': round(z, 1),
            'change_pct': round(change_pct, 1),
            'is_anomaly': abs(z) > 2
        }
    return z_scores


def get_ai_analysis(machine_data):
    api_key = get_secret('GROQ_API_KEY')
    if not api_key:
        return "ERROR: GROQ_API_KEY not found. Add it in Settings → Secrets on Streamlit Cloud, or in .env file locally.\n\nGet your free key at: https://console.groq.com/"

    client = Groq(api_key=api_key)

    data_text = f"""
Machine: {machine_data['machine_id'].iloc[0]}
Type: {machine_data['machine_type'].iloc[0]}

Latest readings (current state):
{machine_data.tail(8).to_string(index=False)}

First readings (healthy baseline):
{machine_data.head(5).to_string(index=False)}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are an expert predictive maintenance engineer for Indian foundries and sugar mills."
            },
            {
                "role": "user",
                "content": f"""Analyze this machine sensor data:

{data_text}

Give a concise report with:
1. Status: CRITICAL / WARNING / NORMAL
2. Predicted failure timeframe with confidence %
3. Top 3 concerns with exact numbers
4. Top 3 recommended actions
5. Estimated savings in Indian Rupees (₹)
6. One paragraph simple explanation

Be specific. Use numbers."""
            }
        ],
        temperature=0.3,
        max_tokens=1000
    )

    return response.choices[0].message.content


# ============================================
# MAIN APP
# ============================================

# Header
st.markdown('<div class="main-header">🏭 Factory Guardian</div>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Multi-Machine Predictive Maintenance Dashboard</p>', unsafe_allow_html=True)

# Sidebar
st.sidebar.title("⚙️ Settings")
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader("Upload Sensor Data (CSV)", type="csv")

if uploaded_file:
    data = load_data(uploaded_file)
else:
    try:
        data = load_data("sensor_data.csv")
        st.sidebar.success("✅ Using default data")
    except FileNotFoundError:
        st.error("❌ No data found. Upload a CSV file.")
        st.stop()

# Get all machines
machines = data['machine_id'].unique()
st.sidebar.markdown(f"### 📊 {len(machines)} Machines Found")

# API Status
api_key = get_secret('GROQ_API_KEY')
if api_key:
    st.sidebar.success("🤖 AI: Connected")
else:
    st.sidebar.error("🤖 AI: Add GROQ_API_KEY")

st.sidebar.markdown("---")

# ============================================
# PAGE NAVIGATION
# ============================================
page = st.sidebar.radio(
    "📄 Select View",
    ["🏠 Fleet Overview", "🔍 Machine Detail", "🤖 AI Analysis", "💰 Savings Report"]
)

# ============================================
# PAGE 1: FLEET OVERVIEW
# ============================================
if page == "🏠 Fleet Overview":

    st.markdown("### 🏠 Fleet Overview — All Machines at a Glance")
    st.markdown("---")

    # Create columns based on number of machines
    cols = st.columns(len(machines))

    fleet_data = []

    for i, machine_id in enumerate(machines):
        machine_data = data[data['machine_id'] == machine_id]
        machine_type = machine_data['machine_type'].iloc[0]
        health = calculate_health_score(machine_data)
        level, icon, css_class = get_alert_level(health)

        fleet_data.append({
            'machine_id': machine_id,
            'machine_type': machine_type,
            'health': health,
            'level': level,
            'icon': icon
        })

        with cols[i]:
            st.markdown(f"""
            <div class="machine-card-{css_class}">
                <h3>{icon} {machine_id}</h3>
                <p>{machine_type}</p>
                <h2>{health}/100</h2>
                <p><strong>{level}</strong></p>
            </div>
            """, unsafe_allow_html=True)

    # Fleet Summary Table
    st.markdown("### 📋 Fleet Summary Table")

    fleet_table = []
    for machine_id in machines:
        machine_data = data[data['machine_id'] == machine_id]
        machine_type = machine_data['machine_type'].iloc[0]
        health = calculate_health_score(machine_data)
        level, icon, _ = get_alert_level(health)
        z_scores = get_z_scores(machine_data)

        anomaly_count = sum(1 for v in z_scores.values() if v['is_anomaly'])

        fleet_table.append({
            'Machine': f"{icon} {machine_id}",
            'Type': machine_type,
            'Health': f"{health}/100",
            'Status': level,
            'Anomalies': f"{anomaly_count}/4 parameters",
            'Vibration': f"{z_scores['vibration_g']['current']}g ({z_scores['vibration_g']['change_pct']:+.1f}%)",
            'Temperature': f"{z_scores['temperature_c']['current']}°C ({z_scores['temperature_c']['change_pct']:+.1f}%)",
            'Readings': len(machine_data)
        })

    fleet_df = pd.DataFrame(fleet_table)
    st.dataframe(fleet_df, use_container_width=True, hide_index=True)

    # Fleet Health Bar Chart
    st.markdown("### 📊 Health Score Comparison")

    fig_fleet = go.Figure()
    colors = []
    for item in fleet_data:
        if item['health'] < 40:
            colors.append('#ff4444')
        elif item['health'] < 70:
            colors.append('#ffaa00')
        else:
            colors.append('#00C851')

    fig_fleet.add_trace(go.Bar(
        x=[f"{d['machine_id']}\n({d['machine_type']})" for d in fleet_data],
        y=[d['health'] for d in fleet_data],
        marker_color=colors,
        text=[f"{d['health']}/100" for d in fleet_data],
        textposition='auto'
    ))

    fig_fleet.add_hline(y=40, line_dash="dash", line_color="red",
                        annotation_text="Critical Threshold")
    fig_fleet.add_hline(y=70, line_dash="dash", line_color="orange",
                        annotation_text="Warning Threshold")

    fig_fleet.update_layout(
        title="Machine Health Scores",
        yaxis_title="Health Score (0-100)",
        yaxis_range=[0, 110],
        height=400,
        template="plotly_white"
    )
    st.plotly_chart(fig_fleet, use_container_width=True)

    # Alert Summary
    critical_count = sum(1 for d in fleet_data if d['level'] == 'CRITICAL')
    warning_count = sum(1 for d in fleet_data if d['level'] == 'WARNING')
    normal_count = sum(1 for d in fleet_data if d['level'] == 'NORMAL')

    st.markdown("### ⚡ Alert Summary")
    acol1, acol2, acol3 = st.columns(3)
    with acol1:
        st.metric("🔴 Critical", critical_count)
    with acol2:
        st.metric("🟡 Warning", warning_count)
    with acol3:
        st.metric("🟢 Normal", normal_count)


# ============================================
# PAGE 2: MACHINE DETAIL
# ============================================
elif page == "🔍 Machine Detail":

    st.markdown("### 🔍 Machine Detail View")

    # Machine selector
    selected_machine = st.selectbox(
        "Select Machine",
        machines,
        format_func=lambda x: f"{x} ({data[data['machine_id']==x]['machine_type'].iloc[0]})"
    )

    machine_data = data[data['machine_id'] == selected_machine]
    machine_type = machine_data['machine_type'].iloc[0]
    health = calculate_health_score(machine_data)
    level, icon, _ = get_alert_level(health)
    z_scores = get_z_scores(machine_data)

    # Metrics Row
    st.markdown("---")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🏥 Health", f"{health}/100",
                   delta=f"{health - 85:.0f}", delta_color="inverse")
    with col2:
        vib = z_scores['vibration_g']
        st.metric("📳 Vibration", f"{vib['current']}g",
                   delta=f"{vib['change_pct']:+.1f}%", delta_color="inverse")
    with col3:
        temp = z_scores['temperature_c']
        st.metric("🌡️ Temp", f"{temp['current']}°C",
                   delta=f"{temp['change_pct']:+.1f}%", delta_color="inverse")
    with col4:
        press = z_scores['pressure_bar']
        st.metric("💨 Pressure", f"{press['current']} bar",
                   delta=f"{press['change_pct']:+.1f}%", delta_color="normal")
    with col5:
        power = z_scores['power_kw']
        st.metric("⚡ Power", f"{power['current']} kW",
                   delta=f"{power['change_pct']:+.1f}%", delta_color="inverse")

    # Alert Banner
    if level == "CRITICAL":
        st.error(f"{icon} **CRITICAL — {selected_machine} ({machine_type})** | Health: {health}/100 | Immediate action required!")
    elif level == "WARNING":
        st.warning(f"{icon} **WARNING — {selected_machine} ({machine_type})** | Health: {health}/100 | Schedule maintenance soon.")
    else:
        st.success(f"{icon} **NORMAL — {selected_machine} ({machine_type})** | Health: {health}/100 | All parameters nominal.")

    # Trend Charts
    st.markdown("### 📈 Sensor Trends")

    tab1, tab2, tab3, tab4 = st.tabs(["📳 Vibration", "🌡️ Temperature", "💨 Pressure", "⚡ Power"])

    chart_configs = [
        (tab1, 'vibration_g', 'Vibration (g-force)', '#ff6b6b', 'Vibration Trend'),
        (tab2, 'temperature_c', 'Temperature (°C)', '#ffa502', 'Temperature Trend'),
        (tab3, 'pressure_bar', 'Pressure (bar)', '#1e90ff', 'Pressure Trend'),
        (tab4, 'power_kw', 'Power (kW)', '#2ed573', 'Power Consumption Trend'),
    ]

    for tab, col, ylabel, color, title in chart_configs:
        with tab:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=machine_data['timestamp'],
                y=machine_data[col],
                mode='lines+markers',
                line=dict(color=color, width=3),
                marker=dict(size=6)
            ))
            baseline_val = machine_data[col].head(5).mean()
            fig.add_hline(y=baseline_val, line_dash="dash", line_color="green",
                          annotation_text=f"Baseline: {baseline_val:.2f}")
            fig.update_layout(title=title, yaxis_title=ylabel,
                              height=400, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    # Z-Score Table
    st.markdown("### 📊 Anomaly Detection")

    z_table = []
    for col, values in z_scores.items():
        status = "🔴 ANOMALY" if values['is_anomaly'] else "🟢 Normal"
        z_table.append({
            'Parameter': col.replace('_', ' ').title(),
            'Baseline': values['baseline'],
            'Current': values['current'],
            'Change': f"{values['change_pct']:+.1f}%",
            'Z-Score': values['z_score'],
            'Status': status
        })

    st.dataframe(pd.DataFrame(z_table), use_container_width=True, hide_index=True)

    # Correlation
    st.markdown("### 🔗 Vibration vs Temperature")
    fig_corr = go.Figure()
    fig_corr.add_trace(go.Scatter(
        x=machine_data['vibration_g'], y=machine_data['temperature_c'],
        mode='markers',
        marker=dict(size=10, color=list(range(len(machine_data))),
                    colorscale='RdYlGn_r', showscale=True,
                    colorbar=dict(title="Day")),
        text=[f"Day {i+1}" for i in range(len(machine_data))],
        hovertemplate="Vibration: %{x}g<br>Temp: %{y}°C<br>%{text}"
    ))
    fig_corr.update_layout(xaxis_title="Vibration (g)", yaxis_title="Temperature (°C)",
                           height=400, template="plotly_white")
    st.plotly_chart(fig_corr, use_container_width=True)


# ============================================
# PAGE 3: AI ANALYSIS
# ============================================
elif page == "🤖 AI Analysis":

    st.markdown("### 🤖 AI Expert Analysis")

    selected_machine = st.selectbox(
        "Select Machine to Analyze",
        machines,
        format_func=lambda x: f"{x} ({data[data['machine_id']==x]['machine_type'].iloc[0]})"
    )

    machine_data = data[data['machine_id'] == selected_machine]

    # Show quick stats first
    health = calculate_health_score(machine_data)
    level, icon, _ = get_alert_level(health)
    st.info(f"{icon} **{selected_machine}** — Health: {health}/100 — Status: {level}")

    if st.button("🔍 Run AI Analysis", type="primary", use_container_width=True):
        api_key = get_secret('GROQ_API_KEY')

        if not api_key:
            st.error("❌ GROQ_API_KEY not found. Add it in Streamlit Secrets or .env file.\n\nFree key: https://console.groq.com/")
        else:
            with st.spinner(f"🤖 Analyzing {selected_machine}... (5-15 seconds)"):
                try:
                    analysis = get_ai_analysis(machine_data)
                    st.markdown("#### 📋 Analysis Result:")
                    st.markdown(analysis)
                    st.success(f"✅ Completed at {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

                    if 'analyses' not in st.session_state:
                        st.session_state['analyses'] = {}
                    st.session_state['analyses'][selected_machine] = {
                        'text': analysis,
                        'time': datetime.now().strftime('%d %b %Y, %I:%M %p')
                    }
                except Exception as e:
                    st.error(f"❌ Failed: {str(e)}")

    # Analyze ALL machines at once
    st.markdown("---")
    st.markdown("### 🏭 Analyze ALL Machines")

    if st.button("🔍 Run Fleet Analysis (All Machines)", use_container_width=True):
        api_key = get_secret('GROQ_API_KEY')
        if not api_key:
            st.error("❌ Add GROQ_API_KEY first.")
        else:
            for machine_id in machines:
                m_data = data[data['machine_id'] == machine_id]
                m_type = m_data['machine_type'].iloc[0]
                m_health = calculate_health_score(m_data)
                m_level, m_icon, _ = get_alert_level(m_health)

                with st.expander(f"{m_icon} {machine_id} ({m_type}) — {m_level} — {m_health}/100"):
                    with st.spinner(f"Analyzing {machine_id}..."):
                        try:
                            result = get_ai_analysis(m_data)
                            st.markdown(result)
                        except Exception as e:
                            st.error(f"Failed: {e}")
                    import time
                    time.sleep(2)  # Respect rate limits

    # Show saved analyses
    if 'analyses' in st.session_state and st.session_state['analyses']:
        st.markdown("---")
        st.markdown("### 📋 Previous Analyses")
        for mid, info in st.session_state['analyses'].items():
            with st.expander(f"{mid} — {info['time']}"):
                st.markdown(info['text'])


# ============================================
# PAGE 4: SAVINGS REPORT
# ============================================
elif page == "💰 Savings Report":

    st.markdown("### 💰 Savings Calculator & ROI Report")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        downtime_cost = st.number_input("Daily Downtime Cost (₹)", value=50000, step=5000)
        repair_unplanned = st.number_input("Unplanned Repair Cost (₹)", value=200000, step=10000)
        incidents_year = st.number_input("Breakdowns Per Year", value=8, step=1)
    with col2:
        repair_planned = st.number_input("Planned Repair Cost (₹)", value=80000, step=10000)
        downtime_days = st.number_input("Avg Downtime Days per Breakdown", value=4, step=1)
        subscription = st.number_input("Factory Guardian Monthly Cost (₹)", value=15000, step=5000)

    st.markdown("---")

    prevented = int(incidents_year * 0.7)  # We prevent ~70%

    cost_without = (downtime_cost * downtime_days + repair_unplanned) * incidents_year
    cost_with = (repair_planned * prevented) + (downtime_cost * 1 * prevented) + (subscription * 12)
    cost_remaining = (downtime_cost * downtime_days + repair_unplanned) * (incidents_year - prevented)
    total_with = cost_with + cost_remaining

    savings = cost_without - total_with
    roi = (savings / (subscription * 12)) * 100

    st.markdown("### 📊 Annual Comparison")

    comp_col1, comp_col2, comp_col3 = st.columns(3)
    with comp_col1:
        st.metric("❌ Cost WITHOUT Guardian", f"₹{cost_without:,.0f}")
    with comp_col2:
        st.metric("✅ Cost WITH Guardian", f"₹{total_with:,.0f}")
    with comp_col3:
        st.metric("💰 Annual Savings", f"₹{savings:,.0f}",
                   delta=f"{roi:.0f}% ROI")

    st.markdown("---")

    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.markdown("#### ❌ Without Factory Guardian")
        st.write(f"• Breakdowns per year: **{incidents_year}**")
        st.write(f"• Avg downtime: **{downtime_days} days each**")
        st.write(f"• Lost production: **₹{downtime_cost * downtime_days * incidents_year:,.0f}**")
        st.write(f"• Emergency repairs: **₹{repair_unplanned * incidents_year:,.0f}**")
        st.write(f"• **Total: ₹{cost_without:,.0f}**")

    with dcol2:
        st.markdown("#### ✅ With Factory Guardian")
        st.write(f"• Breakdowns prevented: **{prevented}/{incidents_year}**")
        st.write(f"• Planned repairs: **₹{repair_planned * prevented:,.0f}**")
        st.write(f"• Remaining breakdowns: **{incidents_year - prevented}**")
        st.write(f"• Guardian subscription: **₹{subscription * 12:,.0f}/year**")
        st.write(f"• **Total: ₹{total_with:,.0f}**")

    # ROI Chart
    fig_roi = go.Figure()
    fig_roi.add_trace(go.Bar(
        x=['Without Guardian', 'With Guardian', 'Savings'],
        y=[cost_without, total_with, savings],
        marker_color=['#ff4444', '#00C851', '#1e90ff'],
        text=[f"₹{v:,.0f}" for v in [cost_without, total_with, savings]],
        textposition='auto'
    ))
    fig_roi.update_layout(title="Annual Cost Comparison",
                          yaxis_title="Cost (₹)", height=400,
                          template="plotly_white")
    st.plotly_chart(fig_roi, use_container_width=True)

    # Payback period
    monthly_savings = savings / 12
    payback_months = (subscription * 12) / savings * 12 if savings > 0 else 0
    st.metric("📅 Payback Period", f"{payback_months:.1f} months",
              delta="Investment recovered")


# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 1rem;'>
    🏭 Factory Guardian v4.0 | Multi-Machine Predictive Maintenance AI<br>
    Powered by Groq AI | Built for Indian Manufacturers | © 2025
</div>
""", unsafe_allow_html=True)