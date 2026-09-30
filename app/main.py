from flask import Flask, render_template, jsonify, request, send_from_directory
import logging
from pathlib import Path
from app.api.modem import get_modem_status
from app.api.power import get_power_status, radio_on, radio_off, reset_modem, shutdown_modem
from app.api.identity import get_identity, change_imei, generate_random_imei, restore_imei
from app.api.capture import start_capture, list_captures, delete_capture
from app.api.setup import configure_qmi, update_apn_metric
from app.utils.time_sync import sync_system_clock, get_network_time
from app.utils.audit_log import get_audit_log
from app.utils.file_retention import run_cleanup
from app.config import CAPTURES_DIR

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if request.method == "POST":
        apn = request.form.get("apn", "pdn-1")
        metric = int(request.form.get("metric", 50))
        
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME", "connection", "show"],
            capture_output=True, text=True
        )
        
        if CON_NAME in result.stdout:
            result = update_apn_metric(apn, metric)
        else:
            result = configure_qmi(apn, metric)
        
        return jsonify(result)
    return render_template("setup.html")


@app.route("/identity", methods=["GET"])
def identity_page():
    return render_template("identity.html")


@app.route("/power", methods=["GET"])
def power_page():
    return render_template("power.html")


@app.route("/signaling", methods=["GET"])
def signaling_page():
    return render_template("signaling.html")


@app.route("/logs")
def logs_page():
    return render_template("logs.html")


@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/troubleshooting")
def troubleshooting_page():
    return render_template("troubleshooting.html")


@app.route("/api/status")
def api_status():
    return jsonify(get_modem_status())


@app.route("/api/identity")
def api_identity():
    return jsonify(get_identity())


@app.route("/api/identity/change", methods=["POST"])
def api_identity_change():
    action = request.form.get("action")
    
    if action == "random":
        new_imei = generate_random_imei()
        result = change_imei(new_imei)
    elif action == "set":
        new_imei = request.form.get("imei")
        if not new_imei:
            return jsonify({"success": False, "message": "IMEI required"})
        result = change_imei(new_imei)
    elif action == "restore":
        result = restore_imei()
    else:
        return jsonify({"success": False, "message": "Invalid action"})
    
    return jsonify(result)


@app.route("/api/power/<action>", methods=["POST"])
def api_power(action):
    if action == "on":
        result = radio_on()
    elif action == "off":
        result = radio_off()
    elif action == "reset":
        result = reset_modem()
    elif action == "shutdown":
        force = request.form.get("force", "false").lower() == "true"
        result = shutdown_modem(force=force)
    else:
        return jsonify({"success": False, "message": "Invalid action"})
    
    return jsonify(result)


@app.route("/api/capture/start", methods=["POST"])
def api_capture_start():
    duration = int(request.form.get("duration", 60))
    mode = request.form.get("mode", "live")
    result = start_capture(duration=duration, mode=mode)
    return jsonify(result)


@app.route("/api/captures")
def api_captures():
    return jsonify(list_captures())


@app.route("/api/captures/<filename>", methods=["DELETE"])
def api_capture_delete(filename):
    result = delete_capture(filename)
    return jsonify(result)


@app.route("/api/time")
def api_time():
    return jsonify(get_network_time())


@app.route("/api/time/sync", methods=["POST"])
def api_time_sync():
    allow_backward = request.form.get("allow_backward", "false").lower() == "true"
    result = sync_system_clock(allow_backward=allow_backward)
    return jsonify(result)


@app.route("/api/logs")
def api_logs():
    limit = int(request.args.get("limit", 100))
    return jsonify(get_audit_log(limit=limit))


@app.route("/api/cleanup", methods=["POST"])
def api_cleanup():
    result = run_cleanup()
    return jsonify(result)


@app.route("/downloads/<filename>")
def download_file(filename):
    captures_path = Path(CAPTURES_DIR)
    return send_from_directory(captures_path, filename, as_attachment=True)


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
