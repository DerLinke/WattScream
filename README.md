# `wattScream` – The Taskbar Power Monitor for GNOME & Cinnamon

**`wattScream`** is a lightweight, real-time power consumption monitor for GNOME Shell and Cinnamon desktop environments. It displays current power usage (in Watts) directly in your panel, along with the total energy consumed today or since the last system boot.

## 🚀 Features
- **Real-Time Panel Display:** Clean taskbar integration for both GNOME Shell and Cinnamon.
- **Dual Accumulators:** Displays current Wattage, total daily energy (Wh/kWh), and energy consumed since the last boot.
- **Robust Daemon:** A Python background daemon handles calculations, detects system reboots/sleep states, and writes clean state files.
- **Flexible Backends:** Easily fetch data from local hardware sensors (AMD/Intel CPU/GPU, battery) or external APIs (Shelly, Tasmota, MQTT, custom commands).
- **Auto-Setup:** Easily install and activate panel extensions/applets via `wattscream --setup`.

## 📦 Architecture
```
                                 ┌──────────────────┐
                                 │  Energy Source   │ (Hardware, API, CLI, ...)
                                 └────────┬─────────┘
                                          │ (polls)
                               ┌──────────▼──────────┐
                               │  wattscream daemon  │ (Calculates Wh, resets on boot/day change)
                               └──────────┬──────────┘
                                          │ (writes JSON)
                        ┌─────────────────┴─────────────────┐
                        ▼                                   ▼
          ┌──────────────────────────┐         ┌──────────────────────────┐
          │  GNOME Shell Extension   │         │     Cinnamon Applet      │
          │  (Reads JSON, updates)   │         │  (Reads JSON, updates)   │
          └──────────────────────────┘         └──────────────────────────┘
```

## 📦 Installation

### Repository (Planned)
```bash
sudo apt update
sudo apt install wattscream
```

### Manual Installation (Development)
```bash
git clone https://github.com/DerLinke/wattScream.git
cd wattScream
./wattscream --setup
```

## 🛠 System Dependencies
- Python 3.x
- GNOME Shell (v40+) or Cinnamon
- `rich` (Python CLI styling)

## 🤝 Contributing
Contributions are welcome! Please open an issue or PR to suggest improvements or add custom data source backends.

---
<p align="center">
  <img src="https://derlinke.github.io/logo.svg" width="300" alt="Logo"><br>
  <strong>DerLinke Software Zentrale</strong><br>
  <a href="https://derlinke.github.io/">Offizielle Webseite</a> | <a href="https://github.com/DerLinke/WattScream">GitHub Repository</a>
</p>
