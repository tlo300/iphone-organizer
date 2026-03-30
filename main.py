# main.py — Flask local server for iPhone home screen organizer
import logging
import webbrowser
from threading import Timer

from flask import Flask, jsonify, render_template, request

import device
import layout as layout_mod

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
app = Flask(__name__)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/status")
def api_status():
    """Check device connectivity and return basic info."""
    try:
        info = device.get_device_info()
        return jsonify({"ok": True, "device": info})
    except ConnectionError as e:
        return jsonify({"ok": False, "error": str(e)}), 503
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/layout")
def api_get_layout():
    """Read home screen layout from device."""
    try:
        raw = device.get_layout()
        apps = device.fetch_installed_apps()
        data = layout_mod.plist_to_json(raw)
        return jsonify({"ok": True, "layout": data, "apps": apps})
    except ConnectionError as e:
        return jsonify({"ok": False, "error": str(e)}), 503
    except Exception as e:
        logging.exception("Error reading layout")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/layout")
def api_set_layout():
    """Write a modified layout back to the device."""
    try:
        data = request.get_json(force=True)
        raw = layout_mod.json_to_plist(data)
        device.set_layout(raw)
        return jsonify({"ok": True})
    except ConnectionError as e:
        return jsonify({"ok": False, "error": str(e)}), 503
    except Exception as e:
        logging.exception("Error writing layout")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/icon/<path:bundle_id>")
def api_icon(bundle_id):
    """Return a base64-encoded PNG icon for a bundle ID."""
    b64 = device.get_icon_png_b64(bundle_id)
    if b64:
        return jsonify({"ok": True, "png_b64": b64})
    return jsonify({"ok": False}), 404


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    url = "http://127.0.0.1:5000"
    Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"\n  iPhone Organizer running at {url}\n")
    app.run(debug=False, port=5000)
