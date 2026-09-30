from app.utils.mmcli_parser import get_status, get_imei, get_imsi, get_iccid, get_signal_quality, get_operator


def get_modem_status():
    """Get comprehensive modem status for dashboard."""
    status = get_status()
    
    return {
        "imei": status.get("imei"),
        "imsi": status.get("imsi"),
        "iccid": status.get("iccid"),
        "operator": status.get("operator"),
        "signal": status.get("signal"),
        "rat": status.get("rat"),
        "state": status.get("state"),
        "ip": status.get("ip")
    }
