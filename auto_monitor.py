# ============================================
# FACTORY GUARDIAN - Automatic Monitor
# ============================================
# This script runs on a schedule and sends
# alerts when problems are detected.
# ============================================

import os
import time
import pandas as pd
import requests
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


def send_telegram(message):
    """Send message via Telegram"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("Telegram not configured")
        return
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Split long messages
    max_len = 4000
    chunks = [message[i:i+max_len] for i in range(0, len(message), max_len)]
    
    for chunk in chunks:
        try:
            requests.post(url, json={
                "chat_id": chat_id,
                "text": chunk
            })
        except Exception as e:
            print(f"Telegram error: {e}")


def check_machine(data):
    """Check if machine needs attention"""
    baseline = data.head(10)
    current = data.tail(3)
    
    alerts = []
    
    checks = {
        'vibration_g': {'direction': 'up', 'threshold': 2.0, 'name': 'Vibration'},
        'temperature_c': {'direction': 'up', 'threshold': 2.0, 'name': 'Temperature'},
        'pressure_bar': {'direction': 'down', 'threshold': -2.0, 'name': 'Pressure'},
        'power_kw': {'direction': 'up', 'threshold': 2.0, 'name': 'Power Draw'}
    }
    
    for col, config in checks.items():
        b_mean = baseline[col].mean()
        b_std = baseline[col].std()
        c_mean = current[col].mean()
        
        if b_std > 0:
            z_score = (c_mean - b_mean) / b_std
        else:
            z_score = 0
        
        if abs(z_score) > abs(config['threshold']):
            change_pct = ((c_mean - b_mean) / b_mean) * 100
            alerts.append({
                'parameter': config['name'],
                'baseline': round(b_mean, 2),
                'current': round(c_mean, 2),
                'z_score': round(z_score, 1),
                'change_percent': round(change_pct, 1)
            })
    
    return alerts


def run_monitoring_cycle():
    """Run one complete monitoring cycle"""
    print(f"\n{'='*50}")
    print(f"⏰ Monitoring cycle: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
    print(f"{'='*50}")
    
    # Load data
    try:
        data = pd.read_csv("sensor_data.csv")
        data['timestamp'] = pd.to_datetime(data['timestamp'])
    except FileNotFoundError:
        print("❌ sensor_data.csv not found")
        return
    
    # Check each machine
    machines = data['machine_id'].unique()
    
    for machine_id in machines:
        machine_data = data[data['machine_id'] == machine_id]
        machine_type = machine_data['machine_type'].iloc[0]
        
        print(f"\n🔍 Checking {machine_id} ({machine_type})...")
        
        alerts = check_machine(machine_data)
        
        if len(alerts) >= 3:
            # Multiple parameters off = CRITICAL
            level = "🔴 CRITICAL"
            urgency = "Immediate inspection required!"
        elif len(alerts) >= 1:
            level = "🟡 WARNING"
            urgency = "Schedule maintenance within 24 hours."
        else:
            level = "🟢 NORMAL"
            urgency = "All parameters nominal."
            print(f"  {level} - All good")
            continue
        
        # Build alert message
        message = f"""
{level} FACTORY GUARDIAN ALERT

🏭 Machine: {machine_id} ({machine_type})
⏰ Time: {datetime.now().strftime('%d %b %Y, %I:%M %p')}
📋 Status: {urgency}

Abnormal Parameters:
"""
        for alert in alerts:
            message += f"""
• {alert['parameter']}: {alert['current']} (was {alert['baseline']})
  Change: {alert['change_percent']:+.1f}% | Z-Score: {alert['z_score']}
"""
        
        message += f"\n🔧 Action: {urgency}"
        
        print(f"  {level}")
        for alert in alerts:
            print(f"    ⚠️ {alert['parameter']}: {alert['change_percent']:+.1f}%")
        
        # Send Telegram alert
        send_telegram(message)
        print(f"  📱 Alert sent to Telegram")
    
    print(f"\n✅ Cycle complete")


# ============================================
# MAIN LOOP
# ============================================
if __name__ == "__main__":
    print("🏭 Factory Guardian - Auto Monitor Started")
    print("📱 Alerts will be sent to Telegram")
    print("🔄 Checking every 2 hours (for testing: every 60 seconds)")
    print("   Press Ctrl+C to stop")
    print()
    
    # For TESTING: check every 60 seconds
    # For PRODUCTION: change to 7200 (2 hours)
    CHECK_INTERVAL = 60  # seconds
    
    while True:
        try:
            run_monitoring_cycle()
            print(f"\n⏳ Next check in {CHECK_INTERVAL} seconds...")
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            print("\n\n👋 Monitor stopped. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("   Retrying in 60 seconds...")
            time.sleep(60)