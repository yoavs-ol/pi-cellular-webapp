import subprocess
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict
from app.utils.at_command import send_at
from app.config import TIMEOUT




def sync_system_clock(allow_backward: bool = False) -> Dict:
    """
    Sync system clock from cellular network time (NITZ).
    
    Args:
        allow_backward: If True, allow moving clock backward (dangerous)
    
    Returns:
        {"success": bool, "message": str, "details": dict}
    """
    nitz = get_network_time()
    
    if nitz["source"] == "system_fallback":
        return {
            "success": False,
            "message": "Network time not available (modem not registered?)",
            "details": nitz
        }
    
    utc_time = nitz["utc_time"]
    current_time = datetime.now(timezone.utc)
    
    if utc_time < current_time and not allow_backward:
        drift = (current_time - utc_time).total_seconds()
        return {
            "success": False,
            "message": f"Skipping sync: clock would move backward {drift:.0f}s",
            "details": nitz
        }
    
    time_str = utc_time.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    try:
        subprocess.run(
            ["date", "-s", time_str],
            check=True, capture_output=True, text=True
        )
        
        logging.info(f"System clock synced to {time_str} (tz={nitz['tz_offset']})")
        
        return {
            "success": True,
            "message": f"System clock synced to {time_str} (tz={nitz['tz_offset']})",
            "details": nitz
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "message": f"Failed to set system clock: {e.stderr}",
            "details": nitz
        }


def get_network_time() -> Dict:
    """
    Get current time from cellular network (NITZ).
    
    Returns:
        {
            "network_time": datetime,  # Local time with timezone
            "utc_time": datetime,       # UTC
            "tz_offset": str,           # e.g., "+0300"
            "source": str               # "ModemManager" or "AT+QLTS"
        }
    """
    nitz = _get_nitz_from_mm()
    if nitz:
        return nitz
    
    nitz = _get_nitz_from_at()
    if nitz:
        return nitz
    
    return {
        "network_time": datetime.now(timezone.utc),
        "utc_time": datetime.now(timezone.utc),
        "tz_offset": "+0000",
        "source": "system_fallback"
    }


def _get_nitz_from_mm() -> Optional[Dict]:
    """Get NITZ from ModemManager network-timezone property."""
    try:
        result = subprocess.run(
            ["mmcli", "-m", "any", "-K"],
            capture_output=True, text=True, timeout=TIMEOUT
        )
        
        tz_str = None
        for line in result.stdout.splitlines():
            if "network-timezone" in line:
                tz_str = line.split(":", 1)[1].strip().strip('"')
                break
        
        if not tz_str or tz_str == "--":
            return None
        
        sign = 1 if tz_str[0] == '+' else -1
        hours = int(tz_str[1:3])
        minutes = int(tz_str[3:5]) if len(tz_str) > 3 else 0
        offset = timedelta(hours=sign * hours, minutes=sign * minutes)
        
        utc_now = datetime.now(timezone.utc)
        local_now = utc_now + offset
        
        return {
            "network_time": local_now,
            "utc_time": utc_now,
            "tz_offset": tz_str,
            "source": "ModemManager"
        }
    except Exception as e:
        logging.debug(f"MM NITZ failed: {e}")
        return None


def _get_nitz_from_at() -> Optional[Dict]:
    """Get NITZ via AT+QLTS (Quectel-specific)."""
    try:
        success, resp = send_at("AT+QLTS")
        if not success or "ERROR" in resp:
            return None
        
        match = re.search(r'"(\d{4}/\d{2}/\d{2},\d{2}:\d{2}:\d{2})([+-]\d{2}),(\d)"', resp)
        if not match:
            return None
        
        time_str, tz_offset, dst = match.groups()
        
        dt_str = time_str + tz_offset
        local_time = datetime.strptime(dt_str, "%Y/%m/%d,%H:%M:%S%z")
        
        return {
            "network_time": local_time,
            "utc_time": datetime.now(timezone.utc),
            "tz_offset": tz_offset,
            "source": "AT+QLTS"
        }
    except Exception as e:
        logging.debug(f"AT NITZ failed: {e}")
        return None
