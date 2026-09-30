# OneFake - Cellular Modem Configuration Service

A web-based configuration tool for cellular modem testing and identity management on Raspberry Pi.

**OneFake** provides a streamlined interface for managing cellular modem identity, enabling authorized testing on private networks.

## Features

- **Dashboard**: Real-time modem status, signal quality, and network info
- **Setup**: One-click QMI configuration with NetworkManager integration
- **Identity**: IMEI/IMSI/ICCID viewer with IMEI change/restore capability
- **Power Control**: Radio on/off, module reset, and full shutdown
- **Signaling Capture**: 60-second RRC capture (live/QMDL modes)
- **Operation Logs**: Audit trail with network timestamps
- **Troubleshooting**: Interactive diagnostic guide
- **Help**: AT command reference

## Quick Start

### Prerequisites

- Raspberry Pi 4/5 with Debian 12+ (64-bit)
- Waveshare RM520N-GL 5G HAT with external 5V/3A power
- Cellular connection established

### Installation

```bash
# 1. Install dependencies
sudo apt-get update
sudo apt-get install -y modemmanager libqmi-utils python3-serial python3-venv sqlite3

# 2. Download application
mkdir -p ~/cellular-app && cd ~/cellular-app
# Clone or extract application files here

# 3. Setup Python environment
python3 -m venv .venv
.venv/bin/pip install flask pyserial gunicorn

# 4. Create data directories
sudo mkdir -p /var/lib/cellular-config /var/lib/cellular-captures
sudo chown $USER:$USER /var/lib/cellular-config /var/lib/cellular-captures

# 5. Install systemd service
# (See INSTALLATION_GUIDE.md for complete service file)
sudo systemctl enable --now cellular-config

# 6. Access web UI
# Open browser: http://<pi-ip>:8080
```

## Usage

### Web UI

Navigate to `http://<pi-ip>:8080` for the web interface.

### API

```bash
# Get modem status
curl http://localhost:8080/api/status

# Change IMEI (random)
curl -X POST http://localhost:8080/api/identity/change -d "action=random"

# Turn radio off
curl -X POST http://localhost:8080/api/power/off

# Start RRC capture
curl -X POST http://localhost:8080/api/capture/start -d "duration=60&mode=live"
```

## Documentation

- **[Installation Guide](INSTALLATION_GUIDE.md)**: Complete installation instructions
- **[Deployment Status](DEPLOYMENT_STATUS.md)**: Current deployment information
- **[Hardware Reference](../pi-cellular-tool/CLAUDE.md)**: Hardware setup and AT commands

## Project Structure

```
pi-cellular-webapp/
├── app/
│   ├── api/              # API endpoints (modem, power, identity, capture, setup)
│   ├── utils/            # Utilities (AT commands, mmcli parser, time sync)
│   ├── templates/        # HTML templates
│   ├── static/           # CSS and JavaScript
│   ├── main.py           # Flask application
│   └── config.py         # Configuration
├── k8s/                  # Kubernetes manifests
├── scripts/              # Utility scripts
├── Dockerfile            # Container image
├── requirements.txt      # Python dependencies
└── cellular-config.service  # systemd unit file
```

## Configuration

Environment variables (set in systemd service or container):

| Variable | Default | Description |
|----------|---------|-------------|
| `AT_PORT` | `/dev/ttyUSB2` | Modem AT command port |
| `CONFIG_DIR` | `/var/lib/cellular-config` | Configuration data directory |
| `CAPTURES_DIR` | `/var/lib/cellular-captures` | Capture files directory |
| `CAPTURE_RETENTION_DAYS` | `7` | Days to keep capture files |
| `LOG_RETENTION_DAYS` | `15` | Days to keep audit logs |

## Hardware Requirements

### Waveshare RM520N-GL 5G HAT

- **Module**: Quectel RM520N-GL (Qualcomm X62)
- **Bands**: 5G n1-n79, LTE B1-B66
- **Speed**: Up to 2.4 Gbps downlink (5G SA)
- **Power**: 5V/3A external power supply **required**
- **Ports**: USB 3.0, 2x SIM slots, GNSS

### Serial Ports

| Device | Purpose |
|--------|---------|
| `/dev/ttyUSB0` | DIAG (QXDM) |
| `/dev/ttyUSB1` | NMEA (GNSS) |
| `/dev/ttyUSB2` | **AT commands** |
| `/dev/ttyUSB3` | Modem data |

## Resource Usage

| Metric | Value |
|--------|-------|
| Memory | ~100MB (2 workers) |
| CPU | <5% idle |
| Disk | <50MB application |
| Startup | ~2 seconds |

## Security

**Current**: 
- No authentication (LAN only)
- No TLS (HTTP only)
- Runs as non-root user

**Production recommendations**:
- Add reverse proxy with TLS (nginx)
- Enable firewall (ufw)
- Add basic authentication

## Troubleshooting

### Service won't start

```bash
# Check logs
journalctl -u cellular-config -xe

# Verify ModemManager
systemctl status ModemManager

# Check port availability
sudo lsof -i :8080
```

### Modem not detected

```bash
# Check USB
lsusb | grep Quectel

# Check serial ports
ls -la /dev/ttyUSB*

# Restart ModemManager
sudo systemctl restart ModemManager
```

### No network connection

```bash
# Check registration
mmcli -m any | grep state

# Verify APN
nmcli connection show cellular

# Reactivate
sudo nmcli connection up cellular
```

## License

Internal use only.

## Support

- **Issues**: Check `/troubleshooting` page in web UI
- **Logs**: `journalctl -u cellular-config -f`
- **Hardware Manual**: [Quectel AT Commands](https://files.waveshare.com/upload/8/8a/Quectel_RG520N%26RG52xF%26RG530F%26RM520N%26RM530N_Series_AT_Commands_Manual_V1.0.0_Preliminary_20220812.pdf)

---

**Version**: 1.0.0  
**Last Updated**: 2026-09-30
