# ============================================
# FACTORY GUARDIAN - Machine Failure Predictor
# ============================================
# Version 3.0 - Uses FREE Groq AI (fastest + reliable)
# No credit card needed. No daily limits.
# ============================================

import os
import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

# Load your secret API keys from .env file
load_dotenv()


def read_sensor_data(file_path):
    """
    Reads the CSV file containing sensor data.
    Think of this as: opening the patient's medical file.
    """
    print("📂 Reading sensor data...")

    # Read the CSV file
    data = pd.read_csv(file_path)

    # Show basic info
    print(f"✅ Loaded {len(data)} readings")
    print(f"📊 Machines found: {data['machine_id'].unique()}")
    print(f"📅 Date range: {data['timestamp'].iloc[0]} to {data['timestamp'].iloc[-1]}")
    print()

    return data


def calculate_basic_stats(data):
    """
    Calculates simple statistics that help detect problems.
    Like checking: is blood pressure higher than normal?
    """
    print("🔢 Calculating statistics...")

    stats = {}

    # Get the first 10 readings as "normal baseline"
    baseline = data.head(10)
    # Get the last 5 readings as "current state"
    current = data.tail(5)

    for column in ['vibration_g', 'temperature_c', 'pressure_bar', 'power_kw']:
        baseline_avg = baseline[column].mean()
        baseline_std = baseline[column].std()
        current_avg = current[column].mean()

        # Z-score: how far is current from normal?
        if baseline_std > 0:
            z_score = (current_avg - baseline_avg) / baseline_std
        else:
            z_score = 0

        change_percent = ((current_avg - baseline_avg) / baseline_avg) * 100

        stats[column] = {
            'baseline_avg': round(baseline_avg, 2),
            'current_avg': round(current_avg, 2),
            'z_score': round(z_score, 2),
            'change_percent': round(change_percent, 2)
        }

        # Print results
        status = "🔴 ANOMALY" if abs(z_score) > 2 else "🟢 Normal"
        print(f"  {column}:")
        print(f"    Baseline: {baseline_avg:.2f} → Current: {current_avg:.2f}")
        print(f"    Change: {change_percent:+.1f}% | Z-Score: {z_score:.1f} | {status}")

    print()
    return stats


def analyze_with_ai(data, stats):
    """
    Sends the data to Groq AI for expert analysis.
    Groq is FREE, FAST, and has no daily limits.
    """
    print("🤖 Sending to Groq AI for expert analysis...")
    print("   (This takes 5-15 seconds — Groq is the fastest)")
    print()

    # Get API key
    api_key = os.getenv('GROQ_API_KEY')

    if not api_key:
        print("❌ GROQ_API_KEY not found in .env file!")
        print("   Get your free key at: https://console.groq.com/")
        print("   Then add to .env: GROQ_API_KEY=gsk_your_key_here")
        return None

    # Create Groq client
    client = Groq(api_key=api_key)

    # Prepare data summary for AI
    data_summary = f"""
SENSOR DATA SUMMARY FOR ANALYSIS:
==================================

Machine: {data['machine_id'].iloc[0]}
Type: {data['machine_type'].iloc[0]}
Total Readings: {len(data)}
Date Range: {data['timestamp'].iloc[0]} to {data['timestamp'].iloc[-1]}

BASELINE READINGS (first 5 days - when machine was healthy):
{data.head(5).to_string(index=False)}

LATEST READINGS (last 5 days - current state):
{data.tail(5).to_string(index=False)}

STATISTICAL ANALYSIS:
"""
    for param, values in stats.items():
        data_summary += f"""
{param}:
  Baseline Average: {values['baseline_avg']}
  Current Average: {values['current_avg']}
  Change: {values['change_percent']}%
  Z-Score: {values['z_score']} {'(ANOMALY - way beyond normal!)' if abs(values['z_score']) > 2 else '(Normal)'}
"""

    # The AI prompt - this is the "brain" of our system
    prompt = f"""You are FACTORY GUARDIAN, an expert Predictive Maintenance AI for manufacturing plants (foundries, sugar mills) in Sangli, Maharashtra, India.

Analyze this sensor data and provide a failure prediction:

{data_summary}

Provide your analysis in this EXACT format:

==================================================
ALERT LEVEL: [CRITICAL / WARNING / NORMAL]
==================================================

MACHINE: [machine name and ID]

PREDICTED FAILURE: [when it will likely fail, with confidence percentage]

KEY INDICATORS:
- Vibration: [current value] (baseline was [value], change [X]%)
- Temperature: [current value] (baseline was [value], change [X]%)
- Pressure: [current value] (baseline was [value], change [X]%)
- Power Draw: [current value] (baseline was [value], change [X]%)

ROOT CAUSE: [most likely cause based on the pattern of ALL four parameters changing together]

RECOMMENDED ACTIONS (in priority order):
1. IMMEDIATE: [what to do RIGHT NOW]
2. WITHIN 4 HOURS: [second action]
3. WITHIN 24 HOURS: [third action]
4. THIS WEEK: [fourth action]

ESTIMATED SAVINGS:
- Cost if machine fails unexpectedly: Rs [amount] (repair + downtime)
- Cost if fixed now with planned maintenance: Rs [amount]
- NET SAVINGS: Rs [amount]

DETAILED EXPLANATION:
[2-3 paragraphs explaining in simple language that a factory owner can understand. Explain what the numbers mean, why this pattern is dangerous, what will happen if they ignore it, and what specifically is wearing out inside the machine. Use real-world analogies.]

SAFETY WARNING:
[Any risks to workers or surrounding equipment if this is ignored]
=================================================="""

    # Send to Groq AI
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are an expert predictive maintenance engineer with 20 years of experience in Indian foundries and sugar mills. You analyze sensor data to predict machine failures before they happen."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=2000
    )

    # Get the AI's analysis
    analysis = response.choices[0].message.content

    return analysis


def send_telegram_alert(message):
    """
    Sends alert to your Telegram.
    Like getting an SMS from the doctor with results.
    """
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("⚠️  Telegram not configured. Skipping alert.")
        print("   To set up Telegram alerts:")
        print("   1. Search @BotFather on Telegram")
        print("   2. Create a bot and get the token")
        print("   3. Search @userinfobot to get your chat ID")
        print("   4. Add both to your .env file")
        return False

    # Telegram has a 4096 character limit - send in chunks
    max_length = 4000

    if len(message) <= max_length:
        chunks = [message]
    else:
        chunks = [message[i:i + max_length] for i in range(0, len(message), max_length)]

    success = True
    for i, chunk in enumerate(chunks):
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": chunk
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                if i == 0:
                    print("✅ Telegram alert sent successfully!")
            else:
                error_data = response.json()
                print(f"⚠️  Telegram error: {error_data.get('description', 'Unknown error')}")
                success = False
        except requests.exceptions.Timeout:
            print("⚠️  Telegram timeout. Check your internet connection.")
            success = False
        except Exception as e:
            print(f"⚠️  Could not send Telegram: {e}")
            success = False

    return success


def save_report(analysis, stats):
    """
    Saves the analysis to a text file.
    Like saving the doctor's report for records.
    """
    report_file = "analysis_report.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("  FACTORY GUARDIAN - ANALYSIS REPORT\n")
        f.write(f"  Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n")
        f.write("=" * 60 + "\n\n")

        f.write("AI ANALYSIS:\n")
        f.write("-" * 40 + "\n")
        f.write(analysis)
        f.write("\n\n")

        f.write("=" * 60 + "\n")
        f.write("  RAW STATISTICS\n")
        f.write("=" * 60 + "\n\n")
        for param, values in stats.items():
            f.write(f"{param}:\n")
            f.write(f"  Baseline: {values['baseline_avg']}\n")
            f.write(f"  Current:  {values['current_avg']}\n")
            f.write(f"  Change:   {values['change_percent']}%\n")
            f.write(f"  Z-Score:  {values['z_score']}\n\n")

    print(f"📄 Report saved to: {report_file}")


# ============================================
# MAIN PROGRAM - This runs everything
# ============================================

def main():
    print()
    print("=" * 50)
    print("  🏭 FACTORY GUARDIAN v3.0")
    print("  Predictive Maintenance AI (Groq Powered)")
    print("  FREE • FAST • RELIABLE")
    print("=" * 50)
    print()

    # Step 1: Read the data
    data = read_sensor_data("sensor_data.csv")

    # Step 2: Calculate statistics
    stats = calculate_basic_stats(data)

    # Step 3: AI Analysis
    try:
        analysis = analyze_with_ai(data, stats)

        if analysis is None:
            print("❌ Could not run AI analysis. Check instructions above.")
            return

        print("=" * 50)
        print("  🤖 AI ANALYSIS RESULT")
        print("=" * 50)
        print()
        print(analysis)
        print()

    except Exception as e:
        error_msg = str(e)
        print(f"❌ AI Analysis failed: {error_msg}")
        print()

        if "api_key" in error_msg.lower() or "auth" in error_msg.lower():
            print("🔧 FIX: Your Groq API key is invalid.")
            print("   1. Go to https://console.groq.com/keys")
            print("   2. Create a new API key")
            print("   3. Update GROQ_API_KEY in your .env file")
        elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
            print("🔧 FIX: Too many requests. Wait 30 seconds and try again.")
        elif "connection" in error_msg.lower():
            print("🔧 FIX: Check your internet connection.")
        else:
            print("🔧 General fix: Check internet + API key in .env file")

        return

    # Step 4: Save report
    save_report(analysis, stats)

    # Step 5: Send Telegram alert
    print()
    print("📱 Sending Telegram alert...")
    alert_message = f"🏭 FACTORY GUARDIAN ALERT\n\n{analysis}"
    send_telegram_alert(alert_message)

    print()
    print("=" * 50)
    print("  ✅ ANALYSIS COMPLETE!")
    print("  📄 Full report: analysis_report.txt")
    print("  📱 Telegram alert: check your phone")
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()