from flask import Flask, render_template, jsonify, request
import json
import os
import subprocess
import threading

app = Flask(__name__)
DATA_FILE = "data/flights.json"
LOG_FILE = "data/scraper.log"
CONFIG_FILE = "data/config.json"

scraper_status = "idle"
current_process = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/flights")
def get_flights():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except:
                data = {}
            # transform to a list for the UI
            flight_list = []
            for date, details in data.items():
                details["date"] = date
                flight_list.append(details)
            flight_list.sort(key=lambda x: x["date"])
            return jsonify({"raw": data, "list": flight_list})
    return jsonify({"raw": {}, "list": []})

@app.route("/api/status")
def get_status():
    global scraper_status
    return jsonify({"status": scraper_status})

@app.route("/api/logs")
def get_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
            return jsonify({"logs": f.read()})
    return jsonify({"logs": ""})

@app.route("/api/clear-logs", methods=["POST"])
def clear_logs():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            pass # Pode falhar se o arquivo estiver em uso intensivo
    return jsonify({"status": "cleared"})

@app.route("/api/clear-data", methods=["POST"])
def clear_data():
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    return jsonify({"status": "cleared"})

@app.route("/api/run", methods=["POST"])
def run_scraper():
    global scraper_status, current_process
    if scraper_status == "running":
        return jsonify({"status": "already running"})
        
    data = request.json
    if data:
        os.makedirs("data", exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
            
    if os.path.exists("data/abort.flag"):
        os.remove("data/abort.flag")
        
    # Limpa dados anteriores automaticamente
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
        
    # Limpa logs anteriores automaticamente
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")
        except:
            pass
        
    scraper_status = "running"
    
    executable = os.path.join(".venv", "Scripts", "python.exe")
    if not os.path.exists(executable):
        executable = "python" # fallback
        
    def run_job():
        global scraper_status, current_process
        os.makedirs("data", exist_ok=True)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        with open(LOG_FILE, "a", encoding="utf-8") as log_f:
            current_process = subprocess.Popen([executable, "scraper.py"], stdout=log_f, stderr=log_f, env=env)
            current_process.wait()
        scraper_status = "idle"
        current_process = None
        
    thread = threading.Thread(target=run_job)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "started"})

@app.route("/api/abort", methods=["POST"])
def abort_scraper():
    # Cria a flag de aborto para o scraper ler e parar sozinho
    with open("data/abort.flag", "w") as f:
        f.write("abort")
        
    return jsonify({"status": "abort_signal_sent"})

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
