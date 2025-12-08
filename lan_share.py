from flask import Flask, render_template, request, redirect, url_for, send_file
import subprocess
import re
import qrcode
import io
import threading
import webbrowser
import os
import sys
import socket

APP_PORT = 5000  # Flask app port

# ✅ Base path for templates (PyInstaller + normal)
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS  # type: ignore[attr-defined]
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))


# ✅ Kill any process already using our Flask port
def kill_existing_by_port(port: int):
    try:
        result = subprocess.check_output(
            f'netstat -ano | findstr :{port}',
            shell=True,
            encoding="utf-8",
            errors="ignore",
        )

        for line in result.splitlines():
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[-1]
                if pid.isdigit():
                    subprocess.call(f"taskkill /PID {pid} /F", shell=True)
    except subprocess.CalledProcessError:
        # No process on that port
        pass


# ✅ Get Local IPv4
def get_ipv4_from_ipconfig() -> str:
    result = subprocess.check_output("ipconfig", encoding="utf-8", errors="ignore")
    matches = re.findall(r"IPv4 Address[^\:]*:\s*([\d\.]+)", result)
    return matches[0] if matches else "127.0.0.1"


# ✅ Try to read XAMPP Apache port from httpd.conf
def get_xampp_port_from_config() -> int | None:
    possible_roots = [
        r"C:\xampp",
        r"D:\xampp",
        r"E:\xampp",
        os.environ.get("XAMPP_HOME", r"C:\xampp"),
    ]

    for root in possible_roots:
        if not root:
            continue
        httpd_path = os.path.join(root, "apache", "conf", "httpd.conf")
        if os.path.exists(httpd_path):
            try:
                with open(httpd_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                # Match lines like: Listen 80   or   Listen 0.0.0.0:8080
                m = re.search(r"^\s*Listen\s+(?:[\d\.]*:)?(\d+)", content, re.MULTILINE)
                if m:
                    return int(m.group(1))
            except Exception:
                pass
    return None


# ✅ Fallback: guess by probing common ports
def get_xampp_port_by_scan() -> int:
    common_ports = [80, 8080, 8081, 8000, 8888]
    for port in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result == 0:
                return port
        except Exception:
            pass
    return 80  # ultimate fallback


# ✅ Final: decide XAMPP port
def get_xampp_port() -> int:
    port = get_xampp_port_from_config()
    if port:
        return port
    return get_xampp_port_by_scan()


# ✅ Build URL for QR + input field
def build_full_url() -> str:
    ip = get_ipv4_from_ipconfig()
    port = get_xampp_port()

    # Always HTTP; only hide port when 80
    if port == 80:
        return f"http://{ip}"
    else:
        return f"http://{ip}:{port}"


@app.route("/")
def index():
    ip_address = get_ipv4_from_ipconfig()
    url = build_full_url()
    return render_template("index.html", ip=ip_address, url=url)


@app.route("/qrcode.png")
def qrcode_png():
    full_url = build_full_url()
    qr = qrcode.make(full_url)

    img_io = io.BytesIO()
    qr.save(img_io, "PNG")
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")


@app.route("/refresh")
def refresh_qr():
    return redirect(url_for("index"))


@app.route("/shutdown", methods=["POST"])
def shutdown():
    shutdown_func = request.environ.get("werkzeug.server.shutdown")
    if shutdown_func:
        shutdown_func()
    threading.Timer(1.0, lambda: os._exit(0)).start()
    return "Shutting down..."


def open_browser():
    webbrowser.open(f"http://127.0.0.1:{APP_PORT}")


if __name__ == "__main__":
    # make sure Flask port is free
    kill_existing_by_port(APP_PORT)

    threading.Timer(1.0, open_browser).start()
    app.run(debug=False, port=APP_PORT)
