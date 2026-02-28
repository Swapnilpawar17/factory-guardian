# ============================================
# FACTORY GUARDIAN - Auto Email Report
# ============================================
# Sends beautiful HTML email with machine status
# Run daily: python email_report.py
# ============================================

import os
import smtplib
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

load_dotenv()


def calculate_health(machine_data):
    """Calculate health score for a machine"""
    baseline = machine_data.head(max(5, len(machine_data) // 4))
    current = machine_data.tail(max(3, len(machine_data) // 6))
    scores = []

    for col in ['vibration_g', 'temperature_c', 'power_kw']:
        b_avg = baseline[col].mean()
        c_avg = current[col].mean()
        if b_avg > 0:
            change = abs(c_avg - b_avg) / b_avg
            scores.append(max(0, 100 - (change * 500)))
        else:
            scores.append(100)

    b_press = baseline['pressure_bar'].mean()
    c_press = current['pressure_bar'].mean()
    if b_press > 0:
        p_change = abs(c_press - b_press) / b_press
        scores.append(max(0, 100 - (p_change * 500)))
    else:
        scores.append(100)

    return round(sum(scores) / len(scores), 1)


def get_status_emoji(health):
    if health < 40:
        return "🔴", "CRITICAL", "#ff4444"
    elif health < 70:
        return "🟡", "WARNING", "#ffaa00"
    else:
        return "🟢", "NORMAL", "#00C851"


def get_ai_summary(data):
    """Get brief AI summary of fleet status"""
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return "AI analysis unavailable - add GROQ_API_KEY to .env"

    client = Groq(api_key=api_key)

    machines = data['machine_id'].unique()
    summary = "FLEET STATUS:\n"

    for mid in machines:
        m_data = data[data['machine_id'] == mid]
        health = calculate_health(m_data)
        _, status, _ = get_status_emoji(health)
        latest = m_data.iloc[-1]
        summary += f"\n{mid} ({m_data['machine_type'].iloc[0]}): Health {health}/100 - {status}"
        summary += f"\n  Vibration: {latest['vibration_g']}g, Temp: {latest['temperature_c']}°C"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a maintenance engineer. Give a brief daily summary."},
            {"role": "user", "content": f"""Give a 3-4 sentence daily maintenance summary for this factory fleet. 
Mention any machines needing attention and one key recommendation.

{summary}"""}
        ],
        temperature=0.3,
        max_tokens=300
    )
    return response.choices[0].message.content


def build_email_html(data):
    """Build beautiful HTML email"""
    machines = data['machine_id'].unique()
    now = datetime.now().strftime('%d %B %Y, %I:%M %p')

    # Get AI summary
    print("🤖 Getting AI summary...")
    ai_summary = get_ai_summary(data)

    # Build machine rows
    machine_rows = ""
    critical_count = 0
    warning_count = 0
    normal_count = 0

    for mid in machines:
        m_data = data[data['machine_id'] == mid]
        m_type = m_data['machine_type'].iloc[0]
        health = calculate_health(m_data)
        emoji, status, color = get_status_emoji(health)
        latest = m_data.iloc[-1]

        if status == "CRITICAL":
            critical_count += 1
        elif status == "WARNING":
            warning_count += 1
        else:
            normal_count += 1

        machine_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">
                <strong>{mid}</strong><br>
                <span style="color: gray; font-size: 12px;">{m_type}</span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">
                <span style="background: {color}; color: white; padding: 4px 12px; 
                border-radius: 20px; font-weight: bold;">{health}/100</span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">
                <span style="color: {color}; font-weight: bold;">{status}</span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">
                {latest['vibration_g']}g
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">
                {latest['temperature_c']}°C
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">
                {latest['pressure_bar']} bar
            </td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; margin: 0;">
        <div style="max-width: 700px; margin: 0 auto; background: white; border-radius: 10px; 
                    overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1E3A5F, #2d5a8e); color: white; 
                        padding: 30px; text-align: center;">
                <h1 style="margin: 0;">🏭 Factory Guardian</h1>
                <p style="margin: 5px 0 0; opacity: 0.8;">Daily Maintenance Report</p>
                <p style="margin: 5px 0 0; font-size: 14px;">{now}</p>
            </div>
            
            <!-- Alert Summary -->
            <div style="display: flex; justify-content: center; padding: 20px; gap: 20px; 
                        text-align: center;">
                <div style="background: #fff0f0; padding: 15px 25px; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: bold; color: #ff4444;">{critical_count}</div>
                    <div style="color: gray; font-size: 12px;">🔴 Critical</div>
                </div>
                <div style="background: #fff8e0; padding: 15px 25px; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: bold; color: #ffaa00;">{warning_count}</div>
                    <div style="color: gray; font-size: 12px;">🟡 Warning</div>
                </div>
                <div style="background: #e8f5e9; padding: 15px 25px; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: bold; color: #00C851;">{normal_count}</div>
                    <div style="color: gray; font-size: 12px;">🟢 Normal</div>
                </div>
            </div>

            <!-- AI Summary -->
            <div style="margin: 0 20px 20px; padding: 15px; background: #f0f4ff; 
                        border-left: 4px solid #1E3A5F; border-radius: 4px;">
                <strong>🤖 AI Summary:</strong><br>
                <span style="color: #333;">{ai_summary}</span>
            </div>
            
            <!-- Machine Table -->
            <div style="padding: 0 20px 20px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f8f9fa;">
                            <th style="padding: 12px; text-align: left;">Machine</th>
                            <th style="padding: 12px; text-align: center;">Health</th>
                            <th style="padding: 12px; text-align: center;">Status</th>
                            <th style="padding: 12px; text-align: center;">Vibration</th>
                            <th style="padding: 12px; text-align: center;">Temp</th>
                            <th style="padding: 12px; text-align: center;">Pressure</th>
                        </tr>
                    </thead>
                    <tbody>
                        {machine_rows}
                    </tbody>
                </table>
            </div>
            
            <!-- Dashboard Link -->
            <div style="text-align: center; padding: 20px;">
                <a href="https://factory-guardian.streamlit.app" 
                   style="background: #1E3A5F; color: white; padding: 12px 30px; 
                          border-radius: 5px; text-decoration: none; font-weight: bold;">
                    📊 Open Live Dashboard
                </a>
            </div>
            
            <!-- Footer -->
            <div style="background: #f8f9fa; padding: 15px; text-align: center; 
                        color: gray; font-size: 12px;">
                Factory Guardian v4.0 | Predictive Maintenance AI<br>
                This is an automated daily report.
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_email(to_email, html_content):
    """Send email via Gmail SMTP"""
    email_address = os.getenv('EMAIL_ADDRESS')
    email_password = os.getenv('EMAIL_PASSWORD')

    if not email_address or not email_password:
        print("❌ Email credentials not found in .env")
        print("   Add EMAIL_ADDRESS and EMAIL_PASSWORD")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🏭 Factory Guardian Daily Report — {datetime.now().strftime('%d %b %Y')}"
    msg['From'] = email_address
    msg['To'] = to_email

    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_address, email_password)
        server.sendmail(email_address, to_email, msg.as_string())
        server.quit()
        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False


def main():
    print()
    print("=" * 50)
    print("  🏭 FACTORY GUARDIAN — Email Report")
    print("=" * 50)
    print()

    # Load data
    print("📂 Loading sensor data...")
    data = pd.read_csv("sensor_data.csv")
    print(f"✅ Loaded {len(data)} readings, {data['machine_id'].nunique()} machines")

    # Build email
    print("📧 Building email report...")
    html = build_email_html(data)

    # Save HTML locally (for preview)
    with open("daily_report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("📄 Report saved to: daily_report.html (open in browser to preview)")

    # Send email
    print()
    recipient = input("📧 Enter recipient email (or press Enter to skip): ").strip()

    if recipient:
        send_email(recipient, html)
    else:
        print("⏭️  Skipped sending. Open daily_report.html to preview the report.")

    print()
    print("✅ Done!")


if __name__ == "__main__":
    main()