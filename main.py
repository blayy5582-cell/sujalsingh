from flask import Flask, render_template, request, jsonify
import threading
import time
import random
import pyperclip
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

app = Flask(__name__)
app.secret_key = "sujal_hawk_pr_2025"

state = {"running": False, "logs": [], "start_time": None}
cfg = {"sessionid": "", "gc_links": [], "message": "", "group_names": []}

driver = None
wait = None

def log(msg):
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    state["logs"].append(entry)
    if len(state["logs"]) > 500:
        state["logs"] = state["logs"][-500:]

def handle_notification_popup():
    try:
        not_now = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Not Now']")))
        not_now.click()
        log("Notification popup closed")
        time.sleep(1)
    except TimeoutException:
        pass

def send_message(link, message):
    driver.get(link)
    time.sleep(4 + random.uniform(0, 2))
    handle_notification_popup()
    try:
        box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox']")))
        pyperclip.copy(message)
        box.click()
        box.send_keys(Keys.CONTROL + "v")
        box.send_keys(Keys.ENTER)
        log("Message sent")
        time.sleep(2)
        return True
    except Exception as e:
        log(f"Message failed: {str(e)[:60]}")
        return False

def change_group_name(link, new_name):
    driver.get(link)
    time.sleep(4)
    handle_notification_popup()
    try:
        info = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "svg[aria-label='Conversation information']")))
        info.find_element(By.XPATH, "..").click()
        time.sleep(2)
        change = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[text()='Change']")))
        change.click()
        time.sleep(1)
        inp = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Group name']")))
        inp.send_keys(Keys.CONTROL + "a")
        inp.send_keys(Keys.DELETE)
        inp.send_keys(new_name)
        save = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[text()='Save']")))
        save.click()
        log(f"Group name changed → {new_name}")
        time.sleep(2)
        return True
    except Exception as e:
        log(f"Name change failed: {str(e)[:60]}")
        return False

def spammer():
    global driver, wait
    options = uc.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless=new")  # Headless for Render

    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    # Login
    driver.get("https://www.instagram.com/")
    time.sleep(3)
    driver.add_cookie({
        "name": "sessionid",
        "value": cfg["sessionid"],
        "domain": ".instagram.com",
        "path": "/",
    })
    driver.refresh()
    time.sleep(5)
    log("Logged in successfully")

    # Main loop
    cycle = 0
    while state["running"]:
        log(f"CYCLE {cycle + 1} START")
        for idx, link in enumerate(cfg["gc_links"], start=1):
            log(f"Opening GC {idx}")
            if send_message(link, cfg["message"]):
                new_name = cfg["group_names"][cycle % len(cfg["group_names"])]
                change_group_name(link, new_name)
        cycle += 1
        log(f"CYCLE {cycle} COMPLETE — Waiting 90s...")
        time.sleep(90)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    global state
    state["running"] = False
    time.sleep(1)
    state = {"running": True, "logs": [], "start_time": time.time()}

    cfg["sessionid"] = request.form["sessionid"].strip()
    cfg["gc_links"] = [x.strip() for x in request.form["gc_links"].split("\n") if x.strip()]
    cfg["message"] = request.form["message"].strip()
    cfg["group_names"] = [x.strip() for x in request.form["group_names"].split("\n") if x.strip()]

    if len(cfg["gc_links"]) > 5:
        cfg["gc_links"] = cfg["gc_links"][:5]  # Free tier limit
        log("Limited to 5 GCs for free tier")

    log("SPAMMER STARTED")
    threading.Thread(target=spammer, daemon=True).start()

    return jsonify({"ok": True})

@app.route("/stop")
def stop():
    state["running"] = False
    log("STOPPED BY USER")
    return jsonify({"ok": True})

@app.route("/status")
def status():
    uptime = "00:00:00"
    if state.get("start_time"):
        t = int(time.time() - state["start_time"])
        h, r = divmod(t, 3600)
        m, s = divmod(r, 60)
        uptime = f"{h:02d}:{m:02d}:{s:02d}"
    return jsonify({
        "running": state["running"],
        "uptime": uptime,
        "logs": state["logs"][-100:]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
