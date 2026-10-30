import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time

def setup_browser():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
    driver = uc.Chrome(options=options)
    return driver

def test():
    driver = setup_browser()
    url = "https://azulpelomundo.voeazul.com.br/flights/?origin=GRU&destination=AEP&date=2027-03-01"
    print(f"Acessando: {url}")
    driver.get(url)
    time.sleep(15)
    
    driver.save_screenshot("screenshot.png")
    with open("source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
        
    print("Salvo screenshot.png e source.html")
    driver.quit()

if __name__ == "__main__":
    test()
