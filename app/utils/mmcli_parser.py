import subprocess
import re
from typing import Dict, Optional
from app.config import TIMEOUT


def get_modem_info() -> Dict[str, str]:
    """
    Parse 'mmcli -m any -K' into dict.
    
    Returns:
        Dict of modem properties (e.g., {"modem.3gpp.imei": "123456789012345", ...})
    """
    try:
        result = subprocess.run(
            ["mmcli", "-m", "any", "-K"],
            capture_output=True, text=True, timeout=TIMEOUT
        )
        if result.returncode != 0:
            return {}
        
        info = {}
        for line in result.stdout.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip()] = value.strip()
        return info
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return {}


def get_imei() -> Optional[str]:
    """Get current IMEI from ModemManager."""
    return get_modem_info().get("modem.3gpp.imei")


def get_imsi() -> Optional[str]:
    """Get IMSI from SIM via ModemManager."""
    info = get_modem_info()
    sim_path = info.get("modem.generic.sim")
    if not sim_path:
        return None
    
    try:
        result = subprocess.run(
            ["mmcli", "-i", sim_path, "-K"],
            capture_output=True, text=True, timeout=TIMEOUT
        )
        for line in result.stdout.splitlines():
            if "sim.properties.imsi" in line:
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def get_iccid() -> Optional[str]:
    """Get ICCID from SIM via ModemManager."""
    info = get_modem_info()
    sim_path = info.get("modem.generic.sim")
    if not sim_path:
        return None
    
    try:
        result = subprocess.run(
            ["mmcli", "-i", sim_path, "-K"],
            capture_output=True, text=True, timeout=TIMEOUT
        )
        for line in result.stdout.splitlines():
            if "sim.properties.iccid" in line:
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def get_operator() -> Optional[str]:
    """Get operator name from ModemManager."""
    info = get_modem_info()
    return info.get("modem.3gpp.operator-name") or info.get("modem.3gpp.operator-code")


def get_signal_quality() -> Optional[int]:
    """Get signal quality percentage from ModemManager."""
    info = get_modem_info()
    signal_str = info.get("modem.generic.signal-quality.value")
    if signal_str:
        try:
            return int(signal_str.rstrip("%"))
        except ValueError:
            pass
    return None


def get_access_tech() -> Optional[str]:
    """Get access technology (5G/LTE/UMTS) from ModemManager."""
    info = get_modem_info()
    return info.get("modem.generic.access-technologies.value[1]") or info.get("modem.generic.access-technologies.current")


def get_state() -> Optional[str]:
    """Get modem state from ModemManager."""
    return get_modem_info().get("modem.generic.state")


def get_ip_address() -> Optional[str]:
    """Get IP address from wwan0 interface."""
    try:
        result = subprocess.run(
            ["ip", "-br", "addr", "show", "wwan0"],
            capture_output=True, text=True, timeout=5
        )
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)", result.stdout)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def get_status() -> Dict[str, Optional[str]]:
    """Get comprehensive modem status."""
    return {
        "imei": get_imei(),
        "imsi": get_imsi(),
        "iccid": get_iccid(),
        "operator": get_operator(),
        "signal": get_signal_quality(),
        "rat": get_access_tech(),
        "state": get_state(),
        "ip": get_ip_address()
    }
