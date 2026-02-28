# ============================================
# FACTORY GUARDIAN - Live Sensor Simulator
# ============================================
# Simulates real-time sensor data from 5 machines.
# Writes to sensor_data.csv every few seconds.
# In production, replace with real MQTT/Modbus data.
# ============================================

import pandas as pd
import numpy as np
import time
import os
from datetime import datetime, timedelta


class MachineSimulator:
    """Simulates sensor data for one machine"""

    def __init__(self, machine_id, machine_type, config):
        self.machine_id = machine_id
        self.machine_type = machine_type
        self.config = config

        # Current state
        self.vibration = config['vibration_base']
        self.temperature = config['temp_base']
        self.pressure = config['pressure_base']
        self.power = config['power_base']
        self.rpm = config['rpm_base']

        # Degradation state
        self.health = 100.0
        self.degradation_rate = config.get('degradation_rate', 0)

    def generate_reading(self):
        """Generate one sensor reading with realistic noise"""

        # Apply degradation
        if self.degradation_rate > 0:
            self.health = max(0, self.health - self.degradation_rate)
            degradation_factor = 1 + ((100 - self.health) / 100) * 0.8

            self.vibration = self.config['vibration_base'] * degradation_factor
            self.temperature = self.config['temp_base'] * (1 + ((100 - self.health) / 100) * 0.06)
            self.pressure = self.config['pressure_base'] * (1 - ((100 - self.health) / 100) * 0.25)
            self.power = self.config['power_base'] * degradation_factor * 0.95

        # Add random noise (±2%)
        noise = lambda val: val * (1 + np.random.normal(0, 0.02))

        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'machine_id': self.machine_id,
            'machine_type': self.machine_type,
            'vibration_g': round(noise(self.vibration), 3),
            'temperature_c': round(noise(self.temperature), 1),
            'pressure_bar': round(noise(self.pressure), 2),
            'power_kw': round(noise(self.power), 1),
            'rpm': round(noise(self.rpm), 0)
        }


def main():
    print()
    print("=" * 55)
    print("  🏭 FACTORY GUARDIAN — Live Sensor Simulator")
    print("  Generating realistic machine data every 10 seconds")
    print("  Press Ctrl+C to stop")
    print("=" * 55)
    print()

    # Define 5 machines with different behaviors
    machines = [
        MachineSimulator("FRN-001", "Induction Furnace", {
            'vibration_base': 1.20, 'temp_base': 1350,
            'pressure_base': 2.1, 'power_base': 280, 'rpm_base': 1200,
            'degradation_rate': 0.8  # 🔴 Rapidly degrading!
        }),
        MachineSimulator("FRN-002", "Induction Furnace", {
            'vibration_base': 1.15, 'temp_base': 1340,
            'pressure_base': 2.2, 'power_base': 275, 'rpm_base': 1180,
            'degradation_rate': 0.0  # 🟢 Healthy
        }),
        MachineSimulator("CRS-001", "Cane Crusher", {
            'vibration_base': 0.85, 'temp_base': 95,
            'pressure_base': 3.5, 'power_base': 450, 'rpm_base': 800,
            'degradation_rate': 0.3  # 🟡 Slow wear
        }),
        MachineSimulator("MLD-001", "Molding Machine", {
            'vibration_base': 0.72, 'temp_base': 180,
            'pressure_base': 4.0, 'power_base': 120, 'rpm_base': 600,
            'degradation_rate': 0.4  # 🟡 Moderate wear
        }),
        MachineSimulator("BLR-001", "Boiler", {
            'vibration_base': 0.45, 'temp_base': 320,
            'pressure_base': 8.5, 'power_base': 200, 'rpm_base': 1500,
            'degradation_rate': 0.0  # 🟢 Healthy
        }),
    ]

    csv_file = "sensor_data_live.csv"
    reading_count = 0

    # Create CSV with headers if doesn't exist
    if not os.path.exists(csv_file):
        headers = "timestamp,machine_id,machine_type,vibration_g,temperature_c,pressure_bar,power_kw,rpm\n"
        with open(csv_file, 'w') as f:
            f.write(headers)
        print(f"📄 Created {csv_file}")

    print(f"📊 Simulating {len(machines)} machines")
    print(f"💾 Writing to: {csv_file}")
    print(f"🔄 Interval: 10 seconds")
    print()

    while True:
        try:
            readings = []
            for machine in machines:
                reading = machine.generate_reading()
                readings.append(reading)

                # Status indicator
                health_pct = machine.health
                if health_pct < 40:
                    status = "🔴"
                elif health_pct < 70:
                    status = "🟡"
                else:
                    status = "🟢"

                print(f"  {status} {machine.machine_id}: "
                      f"Vib={reading['vibration_g']:.2f}g | "
                      f"Temp={reading['temperature_c']:.0f}°C | "
                      f"Press={reading['pressure_bar']:.1f}bar | "
                      f"Health={health_pct:.0f}%")

            # Append to CSV
            df = pd.DataFrame(readings)
            df.to_csv(csv_file, mode='a', header=False, index=False)

            reading_count += len(machines)
            now = datetime.now().strftime('%H:%M:%S')
            print(f"\n  ✅ {now} — {len(machines)} readings saved (Total: {reading_count})")
            print(f"  ⏳ Next reading in 10 seconds...\n")

            time.sleep(10)

        except KeyboardInterrupt:
            print(f"\n\n👋 Simulator stopped. Total readings: {reading_count}")
            print(f"📄 Data saved in: {csv_file}")
            break


if __name__ == "__main__":
    main()