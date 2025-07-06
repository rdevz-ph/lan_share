from flask import Flask, render_template, request, redirect, url_for, send_file
import subprocess
import re
import qrcode
import io
import threading
import webbrowser
import os

app = Flask(__name__)

def get_ipv4_from_ipconfig():
    result = subprocess.check_output("ipconfig", encoding='utf-8')
    matches = re.findall(r"IPv4 Address[^\:]*:\s*([\d\.]+)", result)
    return matches[0] if matches else "Not found"

@app.route('/')
def index():
    ip_address = get_ipv4_from_ipconfig()
    url = f"http://{ip_address}"
    return render_template('index.html', ip=ip_address, url=url)

@app.route('/qrcode.png')
def qrcode_png():
    ip = get_ipv4_from_ipconfig()
    full_url = f"http://{ip}"
    qr = qrcode.make(full_url)

    img_io = io.BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/refresh')
def refresh_qr():
    return redirect(url_for('index'))

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func:
        shutdown_func()
    threading.Timer(1.0, lambda: os._exit(0)).start()
    return "Shutting down..."

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    threading.Timer(1.0, open_browser).start()
    app.run(debug=False, port=5000)
