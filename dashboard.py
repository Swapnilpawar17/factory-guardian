# ============================================
# FACTORY GUARDIAN - Visual Dashboard
# ============================================
# Version 3.0 - Uses FREE Groq AI
# Works on both local computer AND Streamlit Cloud
# ============================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os
from groq import Groq

# ============================================
# HELPER: Get API keys (works locally AND on cloud)
# ============================================
def get_secret(key_name):
    """
    Gets secret keys from either:
    - Streamlit Cloud secrets (when deployed)
    - .env file (when running on your computer)
    """
    # First try Streamlit Cloud secrets
    try:
        return st.secrets[key_name]
    except Exception:
        pass

    # Then try .env file (local development)
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
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="Factory Guardian - Predictive Maintenance",
    page_icon="🏭",
    layout="wide"
)

# ============================================
# CUSTOM STYLING
# ============================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A5F;
        text-align: center;
        padding: 1rem;
    }
    .sub-header {
        text-align: center;
        color: gray;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)


# ============================================
# LOAD DATA
# ============================================
@st.cache_data
def load_data(file):
    """Load sensor data from CSV file"""
    data = pd.read_csv(file)
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    return data


def calculate_health_score(data):
    """
    Calculate a simple health score 0-100.
    100 = perfect health, 0 = about to fail
    """
    baseline = data.head(10)
    current = data.tail(3)

    scores = []

    for col in ['vibration_g', 'temperature_c', 'power_kw']:
        baseline_avg = baseline[col].mean()
        current_avg = current[col].mean()
        change = abs(current_avg - baseline_avg) / baseline_avg
        score = max(0, 100 - (change * 500))
        scores.append(score)

    # Pressure is inverse (decrease is bad)
    baseline_pressure = baseline['pressure_bar'].mean()
    current_pressure = current['pressure_bar'].mean()
    pressure_change = abs(current_pressure - baseline_pressure) / baseline_pressure
    pressure_score = max(0, 100 - (pressure_change * 500))
    scores.append(pressure_score)

    return round(sum(scores) / len(scores), 1)


def get_alert_level(health_score):
    """Determine alert level based on health score"""
    if health_score < 40:
        return "CRITICAL", "🔴"
    elif health_score < 70:
        return "WARNING", "🟡"
    else:
        return "NORMAL", "🟢"


def get_ai_analysis(data):
    """Get AI analysis using FREE Groq API"""
    api_key = get_secret('GROQ_API_KEY')

    if not api_key:
        return "ERROR: GROQ_API_KEY not found. Please add it to your Streamlit Secrets or .env file.\n\nGet your free key at: https://console.groq.com/"

    client = Groq(api_key=api_key)

    data_text = f"""
Machine: {data['machine_id'].iloc[0]}
Type: {data['machine_type'].iloc[0]}

Latest readings (current state):
{data.tail(10).to_string(index=False)}

First readings (healthy baseline):
{data.head(5).to_string(index=False)}
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
                "content": f"""Analyze this machine sensor data and give a clear report:

{data_text}

Include:
1. Overall status (CRITICAL / WARNING / NORMAL)
2. When failure is predicted (with confidence percentage)
3. Top 3 concerns with exact numbers
4. Top 3 recommended actions in priority order
5. Estimated cost savings in Indian Rupees
6. Simple explanation a factory owner can understand

Be specific with numbers. Keep it concise but actionable."""
            }
        ],
        temperature=0.3,
        max_tokens=1500
    )

    return response.choices[0].message.content


# ============================================
# MAIN DASHBOARD
# ============================================

# Header
st.markdown('<div class="main-header">🏭 Factory Guardian</div>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Predictive Maintenance Dashboard — Sangli Manufacturing</p>', unsafe_allow_html=True)

st.divider()

# File Upload or Use Default
st.sidebar.title("⚙️ Settings")
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader(
    "Upload Sensor Data (CSV)",
    type="csv",
    help="Upload a CSV with columns: timestamp, machine_id, machine_type, vibration_g, temperature_c, pressure_bar, power_kw, rpm"
)

if uploaded_file:
    data = load_data(uploaded_file)
else:
    try:
        data = load_data("sensor_data.csv")
        st.sidebar.success("✅ Using default sensor_data.csv")
    except FileNotFoundError:
        st.error("❌ No data file found. Please upload a CSV file using the sidebar.")
        st.stop()

# Sidebar Info
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Data Info")
st.sidebar.write(f"**Records:** {len(data)}")
st.sidebar.write(f"**Machines:** {data['machine_id'].nunique()}")
st.sidebar.write(f"**Date Range:**")
st.sidebar.write(f"  {data['timestamp'].min().strftime('%d %b %Y')}")
st.sidebar.write(f"  to {data['timestamp'].max().strftime('%d %b %Y')}")

# Check API key status
api_key = get_secret('GROQ_API_KEY')
if api_key:
    st.sidebar.markdown("---")
    st.sidebar.success("🤖 AI Engine: Connected")
else:
    st.sidebar.markdown("---")
    st.sidebar.error("🤖 AI Engine: Not Connected")
    st.sidebar.caption("Add GROQ_API_KEY to secrets")

# ============================================
# TOP METRICS ROW
# ============================================
health_score = calculate_health_score(data)
alert_level, alert_icon = get_alert_level(health_score)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🏥 Health Score",
        value=f"{health_score}/100",
        delta=f"{health_score - 85:.0f} from baseline",
        delta_color="inverse"
    )

with col2:
    current_vibration = data['vibration_g'].iloc[-1]
    baseline_vibration = data['vibration_g'].iloc[0]
    st.metric(
        label="📳 Vibration",
        value=f"{current_vibration}g",
        delta=f"{((current_vibration - baseline_vibration) / baseline_vibration) * 100:.1f}%",
        delta_color="inverse"
    )

with col3:
    current_temp = data['temperature_c'].iloc[-1]
    baseline_temp = data['temperature_c'].iloc[0]
    st.metric(
        label="🌡️ Temperature",
        value=f"{current_temp}°C",
        delta=f"{((current_temp - baseline_temp) / baseline_temp) * 100:.1f}%",
        delta_color="inverse"
    )

with col4:
    current_pressure = data['pressure_bar'].iloc[-1]
    baseline_pressure = data['pressure_bar'].iloc[0]
    st.metric(
        label="💨 Pressure",
        value=f"{current_pressure} bar",
        delta=f"{((current_pressure - baseline_pressure) / baseline_pressure) * 100:.1f}%",
        delta_color="normal"
    )

# ============================================
# ALERT BANNER
# ============================================
st.markdown("---")

if alert_level == "CRITICAL":
    st.error(f"""
    {alert_icon} **CRITICAL ALERT — {data['machine_id'].iloc[-1]} ({data['machine_type'].iloc[-1]})**

    Machine health score is **{health_score}/100**. Failure predicted within 48-72 hours.
    Immediate inspection required.
    """)
elif alert_level == "WARNING":
    st.warning(f"""
    {alert_icon} **WARNING — {data['machine_id'].iloc[-1]} ({data['machine_type'].iloc[-1]})**

    Machine health score is **{health_score}/100**. Degradation detected.
    Schedule maintenance within 24-48 hours.
    """)
else:
    st.success(f"""
    {alert_icon} **ALL NORMAL — {data['machine_id'].iloc[-1]} ({data['machine_type'].iloc[-1]})**

    Machine health score is **{health_score}/100**. All parameters within normal range.
    """)

# ============================================
# SENSOR TREND CHARTS
# ============================================
st.markdown("### 📈 Sensor Trends (30-Day)")

tab1, tab2, tab3, tab4 = st.tabs(["📳 Vibration", "🌡️ Temperature", "💨 Pressure", "⚡ Power"])

with tab1:
    fig_vib = go.Figure()
    fig_vib.add_trace(go.Scatter(
        x=data['timestamp'],
        y=data['vibration_g'],
        mode='lines+markers',
        name='Vibration',
        line=dict(color='#ff6b6b', width=3),
        marker=dict(size=6)
    ))
    baseline_vib = data['vibration_g'].head(10).mean()
    fig_vib.add_hline(
        y=baseline_vib,
        line_dash="dash",
        line_color="green",
        annotation_text=f"Baseline: {baseline_vib:.2f}g"
    )
    fig_vib.add_hline(
        y=2.0,
        line_dash="dash",
        line_color="red",
        annotation_text="Danger: 2.0g"
    )
    fig_vib.update_layout(
        title="Vibration Trend",
        yaxis_title="Vibration (g-force)",
        xaxis_title="Date",
        height=400,
        template="plotly_white"
    )
    st.plotly_chart(fig_vib, use_container_width=True)

with tab2:
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(
        x=data['timestamp'],
        y=data['temperature_c'],
        mode='lines+markers',
        name='Temperature',
        line=dict(color='#ffa502', width=3),
        marker=dict(size=6)
    ))
    baseline_temp_val = data['temperature_c'].head(10).mean()
    fig_temp.add_hline(
        y=baseline_temp_val,
        line_dash="dash",
        line_color="green",
        annotation_text=f"Baseline: {baseline_temp_val:.0f}°C"
    )
    fig_temp.update_layout(
        title="Temperature Trend",
        yaxis_title="Temperature (°C)",
        xaxis_title="Date",
        height=400,
        template="plotly_white"
    )
    st.plotly_chart(fig_temp, use_container_width=True)

with tab3:
    fig_press = go.Figure()
    fig_press.add_trace(go.Scatter(
        x=data['timestamp'],
        y=data['pressure_bar'],
        mode='lines+markers',
        name='Pressure',
        line=dict(color='#1e90ff', width=3),
        marker=dict(size=6)
    ))
    baseline_press = data['pressure_bar'].head(10).mean()
    fig_press.add_hline(
        y=baseline_press,
        line_dash="dash",
        line_color="green",
        annotation_text=f"Baseline: {baseline_press:.1f} bar"
    )
    fig_press.add_hline(
        y=1.2,
        line_dash="dash",
        line_color="red",
        annotation_text="Min Safe: 1.2 bar"
    )
    fig_press.update_layout(
        title="Pressure Trend",
        yaxis_title="Pressure (bar)",
        xaxis_title="Date",
        height=400,
        template="plotly_white"
    )
    st.plotly_chart(fig_press, use_container_width=True)

with tab4:
    fig_power = go.Figure()
    fig_power.add_trace(go.Scatter(
        x=data['timestamp'],
        y=data['power_kw'],
        mode='lines+markers',
        name='Power',
        line=dict(color='#2ed573', width=3),
        marker=dict(size=6)
    ))
    baseline_power = data['power_kw'].head(10).mean()
    fig_power.add_hline(
        y=baseline_power,
        line_dash="dash",
        line_color="green",
        annotation_text=f"Baseline: {baseline_power:.0f} kW"
    )
    fig_power.update_layout(
        title="Power Consumption Trend",
        yaxis_title="Power (kW)",
        xaxis_title="Date",
        height=400,
        template="plotly_white"
    )
    st.plotly_chart(fig_power, use_container_width=True)

# ============================================
# CORRELATION CHART
# ============================================
st.markdown("### 🔗 Parameter Correlations")
st.markdown("*When parameters move together, it confirms a real problem (not sensor noise)*")

fig_corr = go.Figure()
fig_corr.add_trace(go.Scatter(
    x=data['vibration_g'],
    y=data['temperature_c'],
    mode='markers',
    marker=dict(
        size=10,
        color=list(range(len(data))),
        colorscale='RdYlGn_r',
        showscale=True,
        colorbar=dict(title="Day")
    ),
    text=[f"Day {i + 1}" for i in range(len(data))],
    hovertemplate="Vibration: %{x}g<br>Temperature: %{y}°C<br>%{text}"
))
fig_corr.update_layout(
    title="Vibration vs Temperature (color = time progression)",
    xaxis_title="Vibration (g)",
    yaxis_title="Temperature (°C)",
    height=400,
    template="plotly_white"
)
st.plotly_chart(fig_corr, use_container_width=True)

# ============================================
# Z-SCORE TABLE
# ============================================
st.markdown("### 📊 Anomaly Detection (Z-Score Analysis)")
st.markdown("*Z-Score > 2 means the reading is abnormally different from baseline*")

baseline = data.head(10)
current = data.tail(3)

z_score_data = []
for col in ['vibration_g', 'temperature_c', 'pressure_bar', 'power_kw']:
    b_mean = baseline[col].mean()
    b_std = baseline[col].std()
    c_mean = current[col].mean()

    z = (c_mean - b_mean) / b_std if b_std > 0 else 0
    change_pct = ((c_mean - b_mean) / b_mean) * 100

    status = "🔴 ANOMALY" if abs(z) > 2 else "🟢 Normal"

    z_score_data.append({
        'Parameter': col.replace('_', ' ').title(),
        'Baseline Avg': round(b_mean, 2),
        'Current Avg': round(c_mean, 2),
        'Change %': f"{change_pct:+.1f}%",
        'Z-Score': round(z, 1),
        'Status': status
    })

z_df = pd.DataFrame(z_score_data)
st.dataframe(z_df, use_container_width=True, hide_index=True)

# ============================================
# AI ANALYSIS BUTTON
# ============================================
st.markdown("---")
st.markdown("### 🤖 AI Expert Analysis")

if st.button("🔍 Run AI Analysis", type="primary", use_container_width=True):
    api_key = get_secret('GROQ_API_KEY')

    if not api_key:
        st.error("""
        ❌ **GROQ_API_KEY not found!**

        **If running locally:**
        Add `GROQ_API_KEY=gsk_yourkey` to your `.env` file

        **If deployed on Streamlit Cloud:**
        1. Go to your app settings (3 dots menu → Settings)
        2. Click "Secrets" section
        3. Add: `GROQ_API_KEY = "gsk_yourkey"`
        4. Click Save and reboot app

        **Get your free key at:** https://console.groq.com/
        """)
    else:
        with st.spinner("🤖 AI is analyzing sensor patterns... (5-15 seconds)"):
            try:
                analysis = get_ai_analysis(data)
                st.markdown("#### 📋 Analysis Result:")
                st.markdown(analysis)

                st.session_state['last_analysis'] = analysis
                st.session_state['analysis_time'] = datetime.now().strftime("%d %b %Y, %I:%M %p")

                st.success(f"✅ Analysis completed at {st.session_state['analysis_time']}")

            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")
                st.info("💡 Check your GROQ_API_KEY and internet connection.")

# Show last analysis if exists
if 'last_analysis' in st.session_state:
    with st.expander(f"📋 Last Analysis ({st.session_state.get('analysis_time', 'Unknown')})"):
        st.markdown(st.session_state['last_analysis'])

# ============================================
# SAVINGS CALCULATOR
# ============================================
st.markdown("---")
st.markdown("### 💰 Savings Calculator")

col1, col2 = st.columns(2)

with col1:
    downtime_cost = st.number_input(
        "Daily Downtime Cost (₹)",
        value=50000,
        step=5000,
        help="How much does 1 day of machine downtime cost you?"
    )
    avg_repair_unplanned = st.number_input(
        "Avg Unplanned Repair Cost (₹)",
        value=200000,
        step=10000
    )

with col2:
    avg_repair_planned = st.number_input(
        "Avg Planned Repair Cost (₹)",
        value=80000,
        step=10000
    )
    avg_downtime_days = st.number_input(
        "Avg Unplanned Downtime (Days)",
        value=4,
        step=1
    )

unplanned_cost = (downtime_cost * avg_downtime_days) + avg_repair_unplanned
planned_cost = (downtime_cost * 1) + avg_repair_planned
savings_per_incident = unplanned_cost - planned_cost
annual_savings = savings_per_incident * 6

st.markdown("#### 📊 Projected Savings")

scol1, scol2, scol3 = st.columns(3)
with scol1:
    st.metric("Cost if Unplanned Failure", f"₹{unplanned_cost:,.0f}")
with scol2:
    st.metric("Cost if Planned Maintenance", f"₹{planned_cost:,.0f}")
with scol3:
    st.metric("Savings Per Incident", f"₹{savings_per_incident:,.0f}", delta=f"₹{savings_per_incident:,.0f} saved")

st.metric("🎯 Estimated Annual Savings (6 incidents)", f"₹{annual_savings:,.0f}")

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 1rem;'>
    🏭 Factory Guardian v3.0 | Predictive Maintenance AI | Powered by Groq<br>
    Built for Sangli Manufacturers | © 2025
</div>
""", unsafe_allow_html=True)