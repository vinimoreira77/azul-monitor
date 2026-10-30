import json
import os
import random
from datetime import datetime, timedelta
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# ====================== CONFIGURAÇÃO ======================
CONFIG_FILE = "data/config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    # Default fallback
    return {
        "origin": "GRU",
        "destination": "AEP",
        "start_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "end_date": (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    }

config = load_config()
ORIGIN = config["origin"]
DESTINATION = config["destination"]

start_date = datetime.strptime(config["start_date"], "%Y-%m-%d")
end_date = datetime.strptime(config["end_date"], "%Y-%m-%d")

DATES = []
current = start_date
while current <= end_date:
    DATES.append(current.strftime("%Y-%m-%d"))
    current += timedelta(days=1)

DATA_FILE = "data/flights.json"

# ====================== FUNÇÕES ======================

def load_previous_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_chrome_major_version():
    """Detecta a versão principal do Chrome instalado (evita quebrar quando o Chrome atualiza)."""
    try:
        import winreg
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(root, r"Software\Google\Chrome\BLBeacon") as key:
                    version, _ = winreg.QueryValueEx(key, "version")
                    return int(version.split(".")[0])
            except OSError:
                continue
    except ImportError:
        pass
    return None  # deixa o undetected_chromedriver detectar sozinho

def setup_browser():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--headless=new") # Removido porque o Akamai bloqueou de novo!
    options.add_argument("--window-size=1920,1080")
    
    # É melhor deixar o undetected_chromedriver gerenciar o User-Agent sozinho.
    # Se você forçar um User-Agent do Chrome 129 num Chrome 154, o Akamai bloqueia na hora.
    
    driver = uc.Chrome(options=options, version_main=get_chrome_major_version())
    
    # Entrar na página inicial primeiro para pegar cookies e passar no teste da Akamai
    print("\n[DEBUG] Entrando na home da Azul para validar a sessão (Anti-Bot)...", flush=True)
    try:
        driver.get("https://www.voeazul.com.br/")
        time.sleep(random.uniform(4, 7))
    except:
        pass
        
    return driver

def check_flights(driver, origin, destination, date):
    # O site da Azul mudou o formato da URL. A URL antiga levava para a tela inicial.
    # Esta nova URL (One Way - OW) vai direto para a tela de resultados.
    # O "1" significa 1 adulto.
    url = f"https://azulpelomundo.voeazul.com.br/flights/OW/{origin}/{destination}/-/-/{date}/-/1/0/0/0/0/ALL/F/ECONOMY/-/-/-/-/A/-?origin={origin}&destination={destination}&date={date}"
    print(f"\n[DEBUG] {date} - Acessando URL: {url}", flush=True)
    driver.get(url)
    
    if "Access Denied" in driver.page_source or "You don't have permission" in driver.page_source:
        print("\n[BLOQUEIO] Akamai bloqueou o acesso! (Access Denied). O robô foi rápido demais.", flush=True)
        return "BLOCKED"
    
    # Espera inteligente (Smart Wait): aguarda até os voos aparecerem na tela, limite de 15s.
    try:
        WebDriverWait(driver, 15).until(
            lambda d: d.find_elements(By.CLASS_NAME, "componentFlight") or \
                      d.find_elements(By.CSS_SELECTOR, "[class*='FlightWithConnectionLine']")
        )
    except:
        pass # Se der timeout, vai seguir e registrar 0 voos
        
    time.sleep(1) # Pausinha de segurança extra

    results = []

    try:
        flights = driver.find_elements(By.CLASS_NAME, "componentFlight")
        print(f"[{date}] -> {len(flights)} voos (componentFlight)", end=" | ")

        if len(flights) == 0:
            flights = driver.find_elements(By.CSS_SELECTOR, "[class*='FlightWithConnectionLine']")
            print(f"{len(flights)} FlightWithConnectionLine", end=" | ")

        if len(flights) == 0:
            driver.save_screenshot(f"debug_{date}.png")
            print("[Screenshot salvo]", end=" | ")

        for flight in flights:
            try:
                points_elem = flight.find_element(By.CSS_SELECTOR, ".labelValuePoints")
                points = int(points_elem.text.replace(".", "").replace(",", ""))
                
                dep_time = flight.find_element(By.CSS_SELECTOR, ".FlightGridDetailsContainer__departureContainer__departureTime").text
                arr_time = flight.find_element(By.CSS_SELECTOR, ".FlightGridDetailsContainer__arrivalContainer__arrivalTime").text
                
                # Extração Inteligente de Companhia Aérea
                airline = "Azul"
                flight_text = flight.text.upper()
                
                if "AEROLINEAS" in flight_text or "AEROLÍNEAS" in flight_text:
                    airline = "Aerolíneas Argentinas"
                elif "COPA" in flight_text:
                    airline = "Copa Airlines"
                elif "TAP " in flight_text:
                    airline = "TAP Portugal"
                elif "UNITED" in flight_text:
                    airline = "United Airlines"
                elif "JETBLUE" in flight_text:
                    airline = "JetBlue"
                else:
                    # Tenta pegar pela imagem (às vezes tem alt='Logo da Azul' ou 'Logo da Copa')
                    try:
                        img = flight.find_element(By.CSS_SELECTOR, "img")
                        alt_text = img.get_attribute("alt") or img.get_attribute("title")
                        if alt_text:
                            if "AEROL" in alt_text.upper(): airline = "Aerolíneas Argentinas"
                            elif "COPA" in alt_text.upper(): airline = "Copa Airlines"
                            elif "TAP" in alt_text.upper(): airline = "TAP Portugal"
                            elif "UNITED" in alt_text.upper(): airline = "United Airlines"
                            elif "AZUL" not in alt_text.upper(): airline = alt_text # Fallback se for uma terceira
                    except:
                        pass

                results.append({
                    "date": date,
                    "points": points,
                    "departure": dep_time,
                    "arrival": arr_time,
                    "airline": airline,
                    "timestamp": datetime.now().isoformat()
                })
            except:
                continue

    except Exception as e:
        print(f"Erro: {e}")

    if results:
        cheapest = min(results, key=lambda x: x["points"])
        return [cheapest]
    return []

def main():
    print(f"[{datetime.now()}] Iniciando varredura com undetected-chromedriver... (De {start_date.strftime('%Y-%m-%d')} até {end_date.strftime('%Y-%m-%d')} | {ORIGIN} -> {DESTINATION})\n")
    
    driver = setup_browser()
    current_data = load_previous_data()
    previous_data = current_data.copy()

    try:
        for i, date in enumerate(DATES, 1):
            if os.path.exists("data/abort.flag"):
                print("\n[ABORT] Sinal de interrupção recebido! Parando varredura.", flush=True)
                break
                
            print(f"\n[{i}/{len(DATES)}] {date}... ", end="", flush=True)
            
            # Delay humano para evitar bloqueio do Akamai (entre 5 e 10 segundos)
            if i > 1:
                delay = random.uniform(5, 10)
                print(f"(esperando {delay:.1f}s) ", end="", flush=True)
                time.sleep(delay)
                
            flights = check_flights(driver, ORIGIN, DESTINATION, date)
            
            if flights == "BLOCKED":
                print("\n[!] Pausando a varredura forçadamente pois fomos bloqueados. Tente novamente mais tarde.", flush=True)
                break

            if flights:
                f = flights[0]
                key = date
                current_data[key] = f

                prev_points = previous_data.get(key, {}).get("points")
                curr_points = f["points"]

                if prev_points and curr_points < prev_points:
                    print(f"[CAIU] {prev_points} -> {curr_points} pts ({f['departure']} - {f['airline']})")
                elif not prev_points:
                    print(f"[NOVO] {curr_points} pts ({f['departure']} - {f['airline']})")
                else:
                    print(f"{curr_points} pts ({f['airline']})")
                    
                # Salva os dados no arquivo na mesma hora para a Interface Web ler!
                save_data(current_data)
            else:
                print("sem voos")

    finally:
        driver.quit()
        save_data(current_data)
        print(f"\nFinalizado! Total de dias com voos: {len(current_data)}")

if __name__ == "__main__":
    main()