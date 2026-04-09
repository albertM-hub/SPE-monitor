# SPE Expert 1.3K-FA / 2K-FA — Python Monitor

Real-time monitoring and control of SPE Expert linear amplifiers via USB serial port.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)
![Amateur Radio](https://img.shields.io/badge/Ham%20Radio-ON5AM-orange)

---

## Features

- **Real-time display** — power output, SWR (ATU + antenna), PA voltage, current, temperature
- **Efficiency calculation** — consumed power, dissipated heat, PA efficiency (%)
- **Color-coded alerts** — SWR bar turns red above 1.6:1 (amplifier protection threshold)
- **Remote control** — OPERATE/STANDBY, TUNE, POWER level, INPUT, ANTENNA selection
- **Windows executable** — no Python installation required for end users
- **Station Master ready** — designed for integration as a widget

---

## Screenshots

> *Add your screenshot here — SPE Monitor running during FT8 transmission*

---

## Requirements

- SPE Expert 1.3K-FA or 2K-FA amplifier
- USB cable (standard, connected to amplifier rear USB port)
- FTDI driver installed (included in KTerm package from [linear-amplifier.com](http://www.linear-amplifier.com))
- Python 3.9+ with `pyserial` **or** use the Windows executable directly

```
pip install pyserial
```

---

## Usage

### Option A — Windows executable (no Python needed)

Download `SPE_Monitor.exe` from the `dist/` folder and run it.  
The application will auto-detect the correct COM port on first run.

> **Note:** Windows Defender may warn on first launch — this is normal for PyInstaller executables. Click *Run anyway*.

### Option B — Python script

```bash
python spe_monitor.py          # uses COM3 by default
python spe_monitor.py COM5     # specify your COM port
```

---

## Finding your COM port

1. Open **Device Manager** → Ports (COM & LPT)
2. Look for **USB Serial Port (COMx)** — that is the SPE amplifier
3. Ignore *FlexRadio Virtual Serial Port* entries if you also use a Flex SDR

> ⚠️ **KTerm must be closed** before running this monitor — only one USB client at a time.

---

## Protocol

This project implements the **SPE Application Programmer's Guide Rev. 1.1** protocol.

Communication parameters: `8N1`, up to `115200 baud` (auto-adapts).

The STATUS command (`0x90`) returns a 19-field CSV string containing all amplifier data:

| Field | Content |
|-------|---------|
| ID | Amplifier model (13K / 20K) |
| Mode | Standby / Operate |
| RX/TX | Current state |
| Band | Active band (160m … 4m) |
| TX Antenna | Selected antenna + ATU status |
| Power Level | LOW / MID / HIGH |
| Output Power | Watts |
| SWR ATU | VSWR before ATU |
| SWR Ant | VSWR at antenna |
| V PA | PA supply voltage |
| I PA | PA supply current |
| Temperature | Heatsink temperature (°C) |
| Warnings / Alarms | Status codes |

---

## Project Structure

```
SPE-monitor/
├── spe_expert.py      # Serial driver + protocol implementation
├── spe_monitor.py     # tkinter GUI — real-time monitor + control buttons
├── requirements.txt   # pyserial
├── dist/
│   └── SPE_Monitor.exe   # Windows standalone executable
└── README.md
```

---

## Control Buttons

| Button | Action |
|--------|--------|
| OPERATE | Toggle Standby ↔ Operate |
| TUNE | Start automatic ATU tuning |
| POWER | Cycle LOW → MID → HIGH |
| INPUT | Toggle Input 1 ↔ 2 |
| ANTENNE | Select next antenna |
| BACKLIGHT | Toggle display backlight |

---

## Tested Hardware

| Amplifier | Firmware | Status |
|-----------|----------|--------|
| SPE Expert 1.3K-FA | 161120_A | ✅ Tested |
| SPE Expert 2K-FA | — | ✅ Compatible (same protocol) |

---

## Author

**Albert — ON5AM**  
📡 [hamanalyst.org](https://hamanalyst.org)  
📍 Ans, Wallonie, Belgium — Grid JO20SP

---

## License

MIT — free to use, modify and distribute.  
SPE s.r.l. is not affiliated with this project.
