# -*- coding: utf-8 -*-
import sys, json, os, random, time, base64, math
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import requests
from io import BytesIO

try:
    from PIL import Image
    USE_PIL = True
except ImportError:
    USE_PIL = False

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

try:
    import undetected_chromedriver as uc
    USE_UC = True
except ImportError:
    USE_UC = False

CONFIG_FILE = "ozon_config.json"
DEFAULT_CONFIG = {
    "theme": "dark",
    "url": "https://profit.ozon.ru/cabinet/tasks",
    "delays": {"min_between_actions": 1.0, "max_between_actions": 2.5},
    "antibot": {"random_mouse_movement": True, "user_agent_rotation": True},
    "analyzer_api_key": "",
    "max_requests": 100,
    "analyzer_model": "gpt-4o"
}
CATEGORIES = ["Модерация товаров", "Разметка данных", "Сбор информации", "Полевые задания", "Смешанная разметка"]

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in data: data[k] = v
            return data
    else:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def create_icon(name, color="#ffffff", size=24):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color)); pen.setWidth(2); pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen); painter.setBrush(Qt.NoBrush)
    if name == "dashboard":
        w = size//2-2; h = size//2-2
        painter.drawRoundedRect(2,2,w,h,2,2); painter.drawRoundedRect(size-w-2,2,w,h,2,2)
        painter.drawRoundedRect(2,size-h-2,w,h,2,2); painter.drawRoundedRect(size-w-2,size-h-2,w,h,2,2)
    elif name == "settings":
        center=size/2; outer_r=size*0.38; inner_r=outer_r*0.65; tooth_h=outer_r*0.22
        painter.save(); painter.translate(center,center)
        for i in range(8):
            painter.rotate(45)
            path=QPainterPath()
            path.moveTo(-tooth_h/2,-outer_r-tooth_h); path.lineTo(tooth_h/2,-outer_r-tooth_h)
            path.lineTo(tooth_h*0.7,-outer_r); path.lineTo(-tooth_h*0.7,-outer_r); path.closeSubpath()
            painter.drawPath(path)
        painter.restore()
        painter.setBrush(QColor(color)); painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(center-outer_r), int(center-outer_r), int(outer_r*2), int(outer_r*2))
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.drawEllipse(int(center-inner_r), int(center-inner_r), int(inner_r*2), int(inner_r*2))
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setBrush(QColor(color))
        painter.drawEllipse(int(center-inner_r*0.3), int(center-inner_r*0.3), int(inner_r*0.6), int(inner_r*0.6))
    elif name == "play":
        path=QPainterPath(); path.moveTo(6,4); path.lineTo(20,12); path.lineTo(6,20); path.closeSubpath()
        painter.setBrush(QColor(color)); painter.setPen(Qt.NoPen); painter.drawPath(path)
    elif name == "stop":
        painter.setBrush(QColor(color)); painter.setPen(Qt.NoPen); painter.drawRoundedRect(4,4,size-8,size-8,3,3)
    elif name == "pause":
        painter.setBrush(QColor(color)); painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(5,4,5,size-8,2,2); painter.drawRoundedRect(size-10,4,5,size-8,2,2)
    elif name == "user":
        painter.drawEllipse(int(size/2-4),3,8,8)
        path=QPainterPath(); path.moveTo(4,size-3); path.lineTo(4,size-6)
        path.quadTo(size/2,size-10,size-4,size-6); path.lineTo(size-4,size-3); path.closeSubpath()
        painter.drawPath(path)
    elif name == "qwixxa":
        grad=QLinearGradient(0,0,size,size); grad.setColorAt(0,QColor("#00b4ff")); grad.setColorAt(1,QColor("#005bff"))
        painter.setBrush(grad); painter.setPen(Qt.NoPen); painter.drawRoundedRect(0,0,size,size,size/5,size/5)
        pen=QPen(QColor("white"), size//8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen); painter.setBrush(Qt.NoBrush)
        margin=size//5; painter.drawEllipse(margin,margin,size-2*margin,size-2*margin)
        painter.drawLine(int(size*0.55),int(size*0.55),size-margin,size-margin)
        painter.setBrush(QColor("white")); painter.drawEllipse(int(size*0.75),int(size*0.75),int(size//8),int(size//8))
    elif name == "sun":
        cx=size/2; cy=size/2; r=size*0.22
        glow=QRadialGradient(cx,cy,r*2); glow.setColorAt(0,QColor(255,200,50,180)); glow.setColorAt(1,QColor(255,200,50,0))
        painter.setPen(Qt.NoPen); painter.setBrush(glow); painter.drawEllipse(int(cx-r*2),int(cy-r*2),int(r*4),int(r*4))
        painter.setPen(QPen(QColor(color),3,Qt.SolidLine,Qt.RoundCap)); painter.setBrush(Qt.NoBrush)
        for i in range(8):
            a=i*math.pi/4; sx=cx+math.cos(a)*(r+2); sy=cy+math.sin(a)*(r+2); ex=cx+math.cos(a)*(r+size*0.3); ey=cy+math.sin(a)*(r+size*0.3)
            painter.drawLine(int(sx),int(sy),int(ex),int(ey))
        cgrad=QLinearGradient(cx-r,cy-r,cx+r,cy+r); cgrad.setColorAt(0,QColor(255,220,80)); cgrad.setColorAt(1,QColor(255,160,30))
        painter.setBrush(cgrad); painter.setPen(Qt.NoPen); painter.drawEllipse(int(cx-r),int(cy-r),int(r*2),int(r*2))
        painter.setBrush(QColor(255,255,255,100)); painter.drawEllipse(int(cx-r/2-2),int(cy-r/2-2),int(r/1.5),int(r/1.5))
    elif name == "moon":
        cx=size*0.45; cy=size/2; r=size*0.3
        glow=QRadialGradient(cx,cy,r*1.8); glow.setColorAt(0,QColor(200,200,255,100)); glow.setColorAt(1,QColor(200,200,255,0))
        painter.setPen(Qt.NoPen); painter.setBrush(glow); painter.drawEllipse(int(cx-r*1.8),int(cy-r*1.8),int(r*3.6),int(r*3.6))
        path=QPainterPath(); path.moveTo(cx+r/2,cy-r*0.8); path.arcTo(QRectF(cx-r,cy-r,r*2,r*2),90,180); path.arcTo(QRectF(cx-r*0.7,cy-r*0.7,r*1.4,r*1.4),270,-180); path.closeSubpath()
        base=QColor(color); painter.setBrush(base); painter.setPen(QPen(base.lighter(140),1)); painter.drawPath(path)
        painter.setBrush(base); painter.setPen(Qt.NoPen)
        s1=QPainterPath(); s1.moveTo(size*0.8,size*0.25); s1.lineTo(size*0.82,size*0.3); s1.lineTo(size*0.87,size*0.32); s1.lineTo(size*0.82,size*0.34); s1.lineTo(size*0.8,size*0.4); s1.lineTo(size*0.78,size*0.34); s1.lineTo(size*0.73,size*0.32); s1.lineTo(size*0.78,size*0.3); s1.closeSubpath(); painter.drawPath(s1)
        s2=QPainterPath(); s2.moveTo(size*0.25,size*0.7); s2.lineTo(size*0.27,size*0.74); s2.lineTo(size*0.31,size*0.76); s2.lineTo(size*0.27,size*0.78); s2.lineTo(size*0.25,size*0.82); s2.lineTo(size*0.23,size*0.78); s2.lineTo(size*0.19,size*0.76); s2.lineTo(size*0.23,size*0.74); s2.closeSubpath(); painter.drawPath(s2)
    elif name == "minus": painter.drawLine(5,int(size/2),size-5,int(size/2))
    elif name == "square": painter.drawRoundedRect(5,5,size-10,size-10,3,3)
    elif name == "close": painter.drawLine(5,5,size-5,size-5); painter.drawLine(size-5,5,5,size-5)
    painter.end()
    return QIcon(pixmap)

def ask_analyzer(api_key, text_prompt, image_bytes=None, model="gpt-4o", retries=3):
    if not api_key:
        return "ОШИБКА_КЛЮЧА"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    content = [{"type": "text", "text": text_prompt}]
    if image_bytes:
        try:
            if USE_PIL:
                img = Image.open(BytesIO(image_bytes)).convert("RGB")
                buf = BytesIO(); img.save(buf, format="JPEG"); image_bytes = buf.getvalue()
            b64 = base64.b64encode(image_bytes).decode('utf-8')
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        except:
            pass
    payload = {"model": model, "messages": [{"role": "user", "content": content}], "max_tokens": 300, "temperature": 0.1}
    for attempt in range(retries):
        try:
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if resp.status_code != 200:
                if model != "gpt-4o-mini":
                    return ask_analyzer(api_key, text_prompt, image_bytes, "gpt-4o-mini", retries)
                return f"ОШИБКА_АНАЛИЗАТОРА: {resp.status_code}"
            return resp.json()['choices'][0]['message']['content'].strip()
        except:
            if attempt == retries-1:
                return "ОШИБКА_СЕТИ"
            time.sleep(3)
    return "ОШИБКА_АНАЛИЗАТОРА"

class OzonBot(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.driver = None
        self.running = False
        self.paused = False
        self.api_key = config.get("analyzer_api_key", "")
        self.total_requests = 0
        self.max_requests = config.get("max_requests", 100)
        self.analyzer_model = config.get("analyzer_model", "gpt-4o")

    def setup_driver(self):
        profile = os.path.join(os.path.expanduser("~"), "OzonBotProfile")
        self.driver = None
        if USE_UC:
            try:
                opts = uc.ChromeOptions()
                opts.add_argument(f"--user-data-dir={profile}")
                opts.add_argument("--profile-directory=Default")
                opts.add_argument("--no-first-run")
                opts.add_argument("--no-default-browser-check")
                self.driver = uc.Chrome(options=opts)
                self.log_signal.emit("🚀 Антидетект включён")
            except:
                self.driver = None
        if self.driver is None:
            opts = Options()
            opts.add_argument("--start-maximized")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument("--disable-infobars")
            opts.add_argument("--no-sandbox")
            opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            opts.add_experimental_option("useAutomationExtension", False)
            opts.add_argument(f"--user-data-dir={profile}")
            opts.add_argument("--profile-directory=Default")
            self.driver = webdriver.Chrome(options=opts)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.get(self.config["url"])
        time.sleep(5)

    def check_window_alive(self):
        try:
            _ = self.driver.current_url
            return True
        except WebDriverException:
            self.log_signal.emit("🚨 Окно закрыто! Перезапуск...")
            try:
                self.driver.quit()
            except:
                pass
            self.setup_driver()
            return False

    def human_delay(self):
        time.sleep(random.uniform(self.config["delays"]["min_between_actions"],
                                   self.config["delays"]["max_between_actions"]))

    def random_mouse_move(self):
        if self.config["antibot"]["random_mouse_movement"]:
            try:
                import pyautogui
                x, y = random.randint(100, 800), random.randint(100, 600)
                pyautogui.moveTo(x + random.randint(-30, 30), y + random.randint(-30, 30),
                                 duration=random.uniform(0.2, 0.8))
                time.sleep(0.1)
                pyautogui.moveTo(x, y, duration=random.uniform(0.1, 0.3))
            except:
                pass

    def switch_to_latest_tab(self):
        try:
            handles = self.driver.window_handles
            if handles:
                self.driver.switch_to.window(handles[-1])
                time.sleep(1)
                return True
        except:
            pass
        return False

    def find_and_click_next(self, timeout=15):
        if not self.check_window_alive():
            return False
        xpaths = [
            "//span[contains(text(), 'Далее')]",
            "//a[contains(text(), 'Далее')]",
            "//div[contains(text(), 'Далее')]",
            "//span[contains(text(), 'Дальше')]",
            "//button[contains(text(), 'Далее')]",
            "//div[contains(@class, 'next')]//span",
            "//div[contains(@class, 'next')]//a"
        ]
        for xp in xpaths:
            try:
                el = WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xp)))
                self.random_mouse_move()
                try:
                    el.click()
                except:
                    self.driver.execute_script("arguments[0].click();", el)
                self.human_delay()
                return True
            except:
                continue
        return False

    def get_page_text(self):
        try:
            if not self.check_window_alive():
                return ""
            return self.driver.find_element(By.TAG_NAME, "body").text
        except:
            return ""

    def get_main_image_bytes(self):
        try:
            if not self.check_window_alive():
                return None
            imgs = self.driver.find_elements(By.TAG_NAME, "img")
            main_img, max_area = None, 0
            for img in imgs:
                try:
                    src = img.get_attribute("src")
                    if src and src.startswith("http"):
                        w, h = img.size['width'], img.size['height']
                        if w > 100 and h > 100 and w * h > max_area:
                            max_area = w * h
                            main_img = img
                except:
                    continue
            if main_img:
                src = main_img.get_attribute("src")
                data = requests.get(src, timeout=5).content
                if len(data) > 1000:
                    return data
        except:
            pass
        return None

    def get_options(self):
        opts = []
        try:
            if not self.check_window_alive():
                return opts
            for label in self.driver.find_elements(By.XPATH, "//label"):
                txt = label.text.strip()
                if txt and len(txt) > 3:
                    opts.append(txt)
        except:
            pass
        return opts

    def get_task_type(self):
        txt = self.get_page_text().lower()
        if "какой атрибут заполнен неверно" in txt or "нельзя продавать" in txt:
            return "moderation"
        if "найти" in txt and "товар" in txt:
            return "search"
        if "сравни" in txt or "валидац" in txt:
            return "validation"
        if "размет" in txt or "классифицируй" in txt:
            return "markup"
        if "полевое" in txt or "фотограф" in txt:
            return "field"
        return "general"

    def get_full_task_text(self):
        try:
            if not self.check_window_alive():
                return ""
            return self.driver.find_element(By.TAG_NAME, "body").text[:4000]
        except:
            return ""

    def get_answer_by_keywords(self, full_text, options):
        txt = full_text.lower()
        forbidden = ["бонг", "кальян", "вейп", "электронная сигарета", "снюс", "никотин",
                     "наркотик", "психотроп", "марихуана", "гашиш", "кокаин", "героин",
                     "оружие", "боеприпас", "взрывчатка", "кастет", "нож-бабочка",
                     "алкоголь", "табак", "сигареты", "этиловый спирт",
                     "порнограф", "18+", "учебные патроны", "нитрит натрия"]
        for kw in forbidden:
            if kw in txt:
                for i, opt in enumerate(options):
                    if "нельзя продавать" in opt.lower() or "недопустимый товар" in opt.lower():
                        return i
                for i, opt in enumerate(options):
                    if "неверную группу" in opt.lower():
                        return i
        if ("бонг" in txt or "кальян" in txt or "вейп" in txt or "трубка" in txt) and \
           ("аптек" in txt or "одежд" in txt or "электроник" in txt):
            for i, opt in enumerate(options):
                if "неверную группу" in opt.lower() or "неверная группа" in opt.lower():
                    return i
        if "фото" in txt and "назван" in txt:
            for i, opt in enumerate(options):
                if "противоречит" in opt.lower():
                    return i
        if "нет бренда" in txt and ("бренд" in txt or "назван" in txt):
            for i, opt in enumerate(options):
                if "другом бренде" in opt.lower() or "о другом бренде" in opt.lower():
                    return i
        if "18+" in txt or "взрослый" in txt:
            for i, opt in enumerate(options):
                if "18" in opt.lower() or "ограниченной категории" in opt.lower():
                    return i
        return -1

    def solve_task(self):
        if not self.api_key:
            return False
        if self.total_requests >= self.max_requests:
            self.log_signal.emit(f"🛑 Лимит {self.max_requests} запросов достигнут. Остановка.")
            self.running = False
            return True

        task_type = self.get_task_type()
        if task_type == "field":
            self.log_signal.emit("🚫 Полевое задание, пропускаю.")
            return True

        full_text = self.get_full_task_text()
        img_bytes = self.get_main_image_bytes()
        if len(full_text) < 100 and not img_bytes:
            self.log_signal.emit("⚠️ Пустое задание, пропускаю.")
            return True

        options = self.get_options()
        fixed = self.get_answer_by_keywords(full_text, options)
        if fixed != -1:
            labels = self.driver.find_elements(By.XPATH, "//label")
            if fixed < len(labels):
                self.driver.execute_script("arguments[0].click();", labels[fixed])
                self.log_signal.emit(f"✅ Выбор по правилам: {options[fixed]}")
                time.sleep(3)
                self.find_and_click_next()
                return True

        base_prompt = (
            "Ты проходишь строгий экзамен на платформе Ozon Profit. "
            "Отвечай ТОЛЬКО номером варианта и ничем больше!\n"
            "Текст задания:\n" + full_text + "\n\n"
        )
        if options:
            base_prompt += "Варианты ответа:\n"
            for i, opt in enumerate(options):
                base_prompt += f"{i+1}. {opt}\n"
            base_prompt += (
                "\nТы - официальный модератор Ozon. Строго соблюдай правила:\n"
                "- Товары из запрещённого списка (бонги, вейпы, алкоголь, оружие, наркотики, порнография, патроны) -> 'Товар нельзя продавать на Ozon'.\n"
                "- Бонг/кальян в категории «Аптека» или «Одежда» -> 'Товар загружен в неверную группу товаров'.\n"
                "- Фото не соответствует названию -> 'Информация в карточке товара противоречит друг другу'.\n"
                "- В названии есть бренд, а в поле «Бренд» указано «Нет бренда» -> 'В описании и/или названии информация о другом бренде'.\n"
                "- Товар 18+ без маркировки -> 'В карточке товара не указан признак «18+»'.\n"
                "- Неверная категория для опасных товаров -> 'Информация в карточке товара нарушает принципы честной конкуренции'.\n"
                "- Если всё верно -> 'Все атрибуты заполнены верно'.\n"
                "ОТВЕЧАЙ ТОЛЬКО ЦИФРОЙ."
            )

        self.total_requests += 1
        self.log_signal.emit(f"📊 Запросы: {self.total_requests}/{self.max_requests}")
        answer = ask_analyzer(self.api_key, base_prompt, img_bytes, self.analyzer_model)

        if answer and "ОШИБКА" not in answer and "не могу" not in answer.lower():
            self.log_signal.emit(f"🧠 Ответ анализатора: {answer}")
            digits = [int(s) for s in answer.split() if s.isdigit()]
            if digits and 0 < digits[0] <= len(options):
                idx = digits[0] - 1
                labels = self.driver.find_elements(By.XPATH, "//label")
                if idx < len(labels):
                    self.driver.execute_script("arguments[0].click();", labels[idx])
                    self.log_signal.emit(f"👉 Клик №{digits[0]}")
                    time.sleep(3)
                    self.find_and_click_next()
                    return True
            for idx, opt in enumerate(options):
                if opt.lower() in answer.lower():
                    labels = self.driver.find_elements(By.XPATH, "//label")
                    if idx < len(labels):
                        self.driver.execute_script("arguments[0].click();", labels[idx])
                        self.log_signal.emit(f"👉 Клик: {opt}")
                        time.sleep(3)
                        self.find_and_click_next()
                        return True

        if "не могу" in answer.lower() or "ОШИБКА" in answer:
            for idx, opt in enumerate(options):
                if "все атрибуты" in opt.lower():
                    labels = self.driver.find_elements(By.XPATH, "//label")
                    if idx < len(labels):
                        self.driver.execute_script("arguments[0].click();", labels[idx])
                        self.log_signal.emit("⚠️ Фолбэк: Все атрибуты верно")
                        time.sleep(3)
                        self.find_and_click_next()
                        return True

        if self.find_and_click_next():
            return True
        return False

    def navigate_to_category(self):
        body = self.get_page_text()
        if "/cabinet/tasks" not in self.driver.current_url:
            self.driver.get(self.config["url"])
            time.sleep(5)
        for cat in CATEGORIES:
            if cat in body:
                try:
                    xp = f"//*[contains(text(), '{cat}')]/ancestor::div[contains(@class, 'task')]//button[contains(text(), 'Начать задания')]"
                    btn = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, xp)))
                    self.log_signal.emit(f"🚀 Заходим: {cat}")
                    self.random_mouse_move()
                    btn.click()
                    time.sleep(5)
                    return True
                except:
                    continue
        return False

    def auto_submit_or_skip(self):
        return self.solve_task() or self.find_and_click_next()

    def run(self):
        self.running = True
        try:
            self.setup_driver()
        except Exception as e:
            self.log_signal.emit(f"❌ Ошибка запуска: {e}")
            self.running = False
            return
        self.log_signal.emit("🚀 Бот запущен")

        while self.running:
            if self.paused:
                time.sleep(1)
                continue
            if self.total_requests >= self.max_requests:
                self.log_signal.emit("🛑 Лимит запросов! Остановка.")
                break
            try:
                if not self.check_window_alive():
                    time.sleep(5)
                    continue
                self.switch_to_latest_tab()
                body = self.get_page_text().lower()
                if "403" in body or "request failed" in body or "доступ ограничен" in body:
                    self.log_signal.emit("🚨 Ошибка 403! Обновляю...")
                    self.driver.refresh()
                    time.sleep(10)
                    continue
                if "нет соединения" in body or "выключите vpn" in body:
                    self.log_signal.emit("🚨 Защита! Отключите VPN.")
                    time.sleep(60)
                    continue
                if self.auto_submit_or_skip():
                    continue
                if "/cabinet/tasks" in self.driver.current_url:
                    if self.navigate_to_category():
                        continue
                    else:
                        self.log_signal.emit("⏳ Нет доступных заданий, жду...")
                        time.sleep(30)
                        self.driver.refresh()
                        continue
                self.driver.get(self.config["url"])
                time.sleep(5)
            except Exception as e:
                self.log_signal.emit(f"⚠️ Ошибка: {e}")
                time.sleep(10)
        self.stop()

    def stop(self):
        self.running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.log_signal.emit("🛑 Бот остановлен")

class ParticleBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.color_start = QColor(15, 23, 42)
        self.color_end = QColor(30, 27, 75)
        self.particle_color = QColor(255, 255, 255, 60)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(30)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setMouseTracking(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.generate_particles(80)

    def generate_particles(self, count):
        self.particles.clear()
        w, h = max(1, self.width()), max(1, self.height())
        for _ in range(count):
            self.particles.append({
                'x': random.randint(0, w),
                'y': random.randint(0, h),
                'vx': random.uniform(-0.8, 0.8),
                'vy': random.uniform(-0.8, 0.8),
                'r': random.randint(2, 6),
                'alpha': random.randint(30, 100)
            })

    def resizeEvent(self, e):
        self.generate_particles(len(self.particles))
        super().resizeEvent(e)

    def set_theme(self, start, end, particle):
        self.color_start, self.color_end, self.particle_color = start, end, particle
        for p in self.particles:
            p['alpha'] = random.randint(30, 100)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, self.color_start)
        grad.setColorAt(1, self.color_end)
        p.fillRect(self.rect(), grad)
        w, h = self.width(), self.height()
        for pt in self.particles:
            pt['x'] += pt['vx']
            pt['y'] += pt['vy']
            if pt['x'] < 0 or pt['x'] > w:
                pt['vx'] = -pt['vx']
                pt['x'] = max(0, min(w, pt['x']))
            if pt['y'] < 0 or pt['y'] > h:
                pt['vy'] = -pt['vy']
                pt['y'] = max(0, min(h, pt['y']))
            color = QColor(self.particle_color)
            color.setAlpha(pt['alpha'])
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(pt['x'], pt['y']), pt['r'], pt['r'])

class ModernCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 25))
        self.setGraphicsEffect(shadow)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.bot = OzonBot(self.config)
        self.bot.log_signal.connect(self.log_text)
        self.bot.status_signal.connect(self.update_status)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(create_icon("qwixxa"))
        app.setStyle("Fusion")

        self.background = ParticleBackground(self)
        self.setCentralWidget(self.background)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("ContentWidget")
        self.content_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self.background)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.content_widget)

        self.initUI()
        self.apply_styles()
        self.show()

        self._resizing = False
        self._resize_direction = None
        self._resize_start_pos = QPoint()
        self._resize_start_geometry = QRect()
        self._edge_tolerance = 8

        if self.config.get("analyzer_api_key"):
            QTimer.singleShot(1000, self.start_bot)

    def initUI(self):
        self.setWindowTitle("OZON PROFIT • @idqwixxa")
        self.setGeometry(100, 100, 1050, 750)
        self.setMinimumSize(950, 700)

        main = QVBoxLayout(self.content_widget)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        self.title_bar = QWidget()
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setFixedHeight(40)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(15, 0, 10, 0)
        title_layout.setSpacing(10)
        title_layout.addStretch()

        self.min_btn = QPushButton()
        self.min_btn.setObjectName("WindowBtn")
        self.min_btn.setIcon(create_icon("minus", color="#94a3b8", size=18))
        self.min_btn.clicked.connect(self.showMinimized)

        self.max_btn = QPushButton()
        self.max_btn.setObjectName("WindowBtn")
        self.max_btn.setIcon(create_icon("square", color="#94a3b8", size=18))
        self.max_btn.clicked.connect(self.toggle_maximize)

        self.close_btn = QPushButton()
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setIcon(create_icon("close", color="#94a3b8", size=18))
        self.close_btn.clicked.connect(self.close)

        title_layout.addWidget(self.min_btn)
        title_layout.addWidget(self.max_btn)
        title_layout.addWidget(self.close_btn)
        main.addWidget(self.title_bar)

        content_area = QWidget()
        content_area.setObjectName("ContentArea")
        content_area.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 30)
        sidebar_layout.setSpacing(8)

        logo_icon = QLabel()
        logo_icon.setPixmap(create_icon("qwixxa", size=32).pixmap(32, 32))
        logo_text = QLabel("Ozon Profit")
        logo_text.setObjectName("Logo")
        logo_layout = QHBoxLayout()
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(3)
        logo_layout.addWidget(logo_icon)
        logo_layout.addSpacing(3)
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        sidebar_layout.addLayout(logo_layout)
        sidebar_layout.addSpacing(30)

        self.nav_dash = QPushButton(" Управление")
        self.nav_dash.setIcon(create_icon("dashboard"))
        self.nav_dash.setObjectName("NavBtn")
        self.nav_dash.setCheckable(True)
        self.nav_dash.setAutoExclusive(True)
        self.nav_dash.clicked.connect(lambda: self.switch_page(0))

        self.nav_settings = QPushButton(" Настройки")
        self.nav_settings.setIcon(create_icon("settings"))
        self.nav_settings.setObjectName("NavBtn")
        self.nav_settings.setCheckable(True)
        self.nav_settings.setAutoExclusive(True)
        self.nav_settings.clicked.connect(lambda: self.switch_page(1))

        sidebar_layout.addWidget(self.nav_dash)
        sidebar_layout.addWidget(self.nav_settings)
        sidebar_layout.addStretch()

        user_icon = QLabel()
        user_icon.setPixmap(create_icon("user", color="#94a3b8", size=20).pixmap(20, 20))
        user_lbl = QLabel("@idqwixxa")
        user_lbl.setObjectName("UserLabel")
        user_layout = QHBoxLayout()
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(3)
        user_layout.addWidget(user_icon)
        user_layout.addSpacing(3)
        user_layout.addWidget(user_lbl)
        user_layout.addStretch()
        sidebar_layout.addLayout(user_layout)

        ver_lbl = QLabel("v2.0 (AI)")
        ver_lbl.setObjectName("VersionLabel")
        sidebar_layout.addWidget(ver_lbl)

        content_layout.addWidget(sidebar)

        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: transparent;")
        content_layout.addWidget(self.content_stack)

        page_dash = QWidget()
        page_dash.setStyleSheet("background: transparent;")
        dash_layout = QVBoxLayout(page_dash)
        dash_layout.setContentsMargins(40, 40, 40, 40)
        dash_layout.setSpacing(20)

        status_card = ModernCard()
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(25, 25, 25, 25)
        self.status_label = QLabel("● Статус: Остановлен")
        self.status_label.setObjectName("BigStatusLabel")
        status_layout.addWidget(self.status_label)
        dash_layout.addWidget(status_card)

        btn_card = ModernCard()
        btn_layout = QHBoxLayout(btn_card)
        btn_layout.setContentsMargins(25, 25, 25, 25)
        btn_layout.setSpacing(15)

        self.start_btn = QPushButton(" Запустить")
        self.start_btn.setIcon(create_icon("play", color="white"))
        self.start_btn.setObjectName("PrimaryBtn")
        self.start_btn.clicked.connect(self.start_bot)

        self.stop_btn = QPushButton(" Остановить")
        self.stop_btn.setIcon(create_icon("stop", color="white"))
        self.stop_btn.setObjectName("DangerBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_bot)

        self.pause_btn = QPushButton(" Пауза")
        self.pause_btn.setIcon(create_icon("pause", color="white"))
        self.pause_btn.setObjectName("SecondaryBtn")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_bot)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addStretch()
        dash_layout.addWidget(btn_card)

        log_card = ModernCard()
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(25, 25, 25, 25)
        log_title = QLabel("Логи")
        log_title.setObjectName("CardTitle")
        log_layout.addWidget(log_title)
        self.log_textbox = QTextEdit()
        self.log_textbox.setReadOnly(True)
        self.log_textbox.setObjectName("LogText")
        log_layout.addWidget(self.log_textbox)
        dash_layout.addWidget(log_card)

        self.content_stack.addWidget(page_dash)

        page_settings = QWidget()
        page_settings.setStyleSheet("background: transparent;")
        settings_layout = QVBoxLayout(page_settings)
        settings_layout.setContentsMargins(40, 40, 40, 40)
        settings_layout.setSpacing(20)

        set_card = ModernCard()
        set_card_layout = QVBoxLayout(set_card)
        set_card_layout.setContentsMargins(25, 25, 25, 25)
        set_title = QLabel("Настройки")
        set_title.setObjectName("CardTitle")
        set_card_layout.addWidget(set_title)

        theme_layout = QHBoxLayout()
        theme_layout.setSpacing(10)
        self.theme_btn = QPushButton(" Переключить тему")
        self.theme_btn.setObjectName("ThemeBtn")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        theme_layout.addWidget(self.theme_btn)
        theme_layout.addStretch()
        set_card_layout.addLayout(theme_layout)

        form = QFormLayout()
        form.setSpacing(15)

        self.url_edit = QLineEdit(self.config["url"])
        self.url_edit.setObjectName("InputField")
        form.addRow("Главная страница:", self.url_edit)

        self.api_edit = QLineEdit(self.config.get("analyzer_api_key", ""))
        self.api_edit.setObjectName("InputField")
        self.api_edit.setPlaceholderText("sk-...")
        form.addRow("Ключ анализатора:", self.api_edit)

        self.model_edit = QLineEdit(self.config.get("analyzer_model", "gpt-4o"))
        self.model_edit.setObjectName("InputField")
        form.addRow("Модель анализатора:", self.model_edit)

        self.max_req_edit = QLineEdit(str(self.config.get("max_requests", 100)))
        self.max_req_edit.setObjectName("InputField")
        form.addRow("Макс. запросов:", self.max_req_edit)

        self.delay_min = QLineEdit(str(self.config["delays"]["min_between_actions"]))
        self.delay_min.setObjectName("InputField")
        form.addRow("Мин. задержка:", self.delay_min)

        self.delay_max = QLineEdit(str(self.config["delays"]["max_between_actions"]))
        self.delay_max.setObjectName("InputField")
        form.addRow("Макс. задержка:", self.delay_max)

        self.antibot_check = QCheckBox("Эмулировать движения мыши")
        self.antibot_check.setChecked(True)
        form.addRow("Антибот:", self.antibot_check)

        set_card_layout.addLayout(form)

        save_btn = QPushButton(" Сохранить")
        save_btn.setIcon(create_icon("settings", color="white"))
        save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self.save_settings)
        set_card_layout.addWidget(save_btn)

        settings_layout.addWidget(set_card)
        settings_layout.addStretch()
        self.content_stack.addWidget(page_settings)

        main.addWidget(content_area)

        self.nav_dash.setChecked(True)
        self.update_theme_icon()
        self.m_drag = False
        self.m_DragPosition = QPoint()
        self.update_background_theme()

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setIcon(create_icon("square", color="#94a3b8", size=18))
        else:
            self.showMaximized()
            self.max_btn.setIcon(create_icon("restore", color="#94a3b8", size=18))

    def switch_page(self, idx):
        self.content_stack.setCurrentIndex(idx)
        self.nav_dash.setChecked(idx == 0)
        self.nav_settings.setChecked(idx == 1)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._resize_direction = self._get_resize_direction(e.pos())
            if self._resize_direction:
                self._resizing = True
                self._resize_start_pos = e.globalPos()
                self._resize_start_geometry = self.geometry()
                e.accept()
                return
            self.m_drag = True
            self.m_DragPosition = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if not self._resizing:
            self._set_cursor_for_direction(self._get_resize_direction(e.pos()))
        if self._resizing:
            delta = e.globalPos() - self._resize_start_pos
            geo = self._resize_start_geometry
            new = QRect(geo)
            if self._resize_direction == 'right':
                new.setWidth(max(self.minimumWidth(), geo.width() + delta.x()))
            elif self._resize_direction == 'left':
                x = geo.x() + delta.x()
                w = geo.width() - delta.x()
                if w >= self.minimumWidth():
                    new.setX(x)
                    new.setWidth(w)
            elif self._resize_direction == 'bottom':
                new.setHeight(max(self.minimumHeight(), geo.height() + delta.y()))
            elif self._resize_direction == 'top':
                y = geo.y() + delta.y()
                h = geo.height() - delta.y()
                if h >= self.minimumHeight():
                    new.setY(y)
                    new.setHeight(h)
            elif self._resize_direction == 'tl':
                x = geo.x() + delta.x()
                y = geo.y() + delta.y()
                w = geo.width() - delta.x()
                h = geo.height() - delta.y()
                if w >= self.minimumWidth() and h >= self.minimumHeight():
                    new.setX(x); new.setY(y)
                    new.setWidth(w); new.setHeight(h)
            elif self._resize_direction == 'tr':
                y = geo.y() + delta.y()
                w = geo.width() + delta.x()
                h = geo.height() - delta.y()
                if w >= self.minimumWidth() and h >= self.minimumHeight():
                    new.setY(y)
                    new.setWidth(w); new.setHeight(h)
            elif self._resize_direction == 'bl':
                x = geo.x() + delta.x()
                w = geo.width() - delta.x()
                h = geo.height() + delta.y()
                if w >= self.minimumWidth() and h >= self.minimumHeight():
                    new.setX(x)
                    new.setWidth(w); new.setHeight(h)
            elif self._resize_direction == 'br':
                w = geo.width() + delta.x()
                h = geo.height() + delta.y()
                if w >= self.minimumWidth() and h >= self.minimumHeight():
                    new.setWidth(w); new.setHeight(h)
            self.setGeometry(new)
            e.accept()
            return
        if self.m_drag and e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self.m_DragPosition)
            e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.m_drag = False
            if self._resizing:
                self._resizing = False
                self._resize_direction = None
                self.setCursor(Qt.ArrowCursor)
                e.accept()

    def _get_resize_direction(self, pos):
        rect = self.rect()
        tol = self._edge_tolerance
        l = pos.x() < tol
        r = pos.x() > rect.width() - tol
        t = pos.y() < tol
        b = pos.y() > rect.height() - tol
        if l and t: return 'tl'
        if r and t: return 'tr'
        if l and b: return 'bl'
        if r and b: return 'br'
        if l: return 'left'
        if r: return 'right'
        if t: return 'top'
        if b: return 'bottom'
        return None

    def _set_cursor_for_direction(self, d):
        if d in ('tl', 'br'):
            self.setCursor(Qt.SizeFDiagCursor)
        elif d in ('tr', 'bl'):
            self.setCursor(Qt.SizeBDiagCursor)
        elif d in ('left', 'right'):
            self.setCursor(Qt.SizeHorCursor)
        elif d in ('top', 'bottom'):
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def update_theme_icon(self):
        if self.config["theme"] == "dark":
            self.theme_btn.setIcon(create_icon("sun", color="white"))
        else:
            self.theme_btn.setIcon(create_icon("moon", color="#1e293b"))

    def toggle_theme(self):
        self.config["theme"] = "light" if self.config["theme"] == "dark" else "dark"
        save_config(self.config)
        self.apply_styles()
        self.update_theme_icon()
        self.update_background_theme()

    def update_background_theme(self):
        if self.config["theme"] == "dark":
            start, end, particle = QColor(15, 23, 42), QColor(30, 27, 75), QColor(255, 255, 255, 60)
        else:
            start, end, particle = QColor(248, 250, 252), QColor(226, 232, 240), QColor(30, 41, 59, 50)
        self.background.set_theme(start, end, particle)

    def apply_styles(self):
        if self.config["theme"] == "dark":
            bg, side, card, text, muted, input_bg, border = "#0f172a","#1e293b","#1e293b","#f8fafc","#94a3b8","#0f172a","#334155"
            primary, primary_h, primary_active = "#3b82f6","#2563eb","#1d4ed8"
            danger, danger_h, sec, sec_h = "#ef4444","#dc2626","#6b7280","#4b5563"
            log_bg, nav_text, btn_text = "#0f172a","#ffffff","#ffffff"
        else:
            bg, side, card, text, muted, input_bg, border = "#f8fafc","#ffffff","#ffffff","#1e293b","#64748b","#ffffff","#e2e8f0"
            primary, primary_h, primary_active = "#1e40af","#1e3a8a","#1e3a8a"
            danger, danger_h, sec, sec_h = "#b91c1c","#991b1b","#4b5563","#374151"
            log_bg, nav_text, btn_text = "#f8fafc","#ffffff","#ffffff"

        style = f"""
        QMainWindow {{ background-color: {bg}; }}
        QWidget#MainBg {{ background-color: {bg}; }}
        QLabel {{ color: {text}; }}
        #TitleBar {{ background-color: transparent; border-bottom: 1px solid {border}; }}
        #WindowBtn {{ background: transparent; border: none; padding: 6px; border-radius: 8px; }}
        #WindowBtn:hover {{ background-color: rgba(0,0,0,0.1); }}
        #CloseBtn {{ background: transparent; border: none; padding: 6px; border-radius: 8px; }}
        #CloseBtn:hover {{ background-color: {danger}; }}
        #Sidebar {{ background-color: {side}; border-right: 1px solid {border}; }}
        #Logo {{ font-size: 16px; font-weight: 900; color: {text}; }}

        #NavBtn {{
            background: {primary};
            color: {nav_text};
            border: none;
            text-align: left;
            padding: 12px 15px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
        }}
        #NavBtn:hover {{ background: {primary_h}; }}
        #NavBtn:checked {{ background: {primary_active}; }}

        #UserLabel {{ color: {text}; font-weight: bold; }}
        #VersionLabel {{ color: {muted}; font-size: 11px; }}
        #Card {{ background-color: {card}; border-radius: 16px; border: 1px solid {border}; }}
        #BigStatusLabel {{ font-size: 20px; font-weight: bold; color: {text}; }}
        #CardTitle {{ font-size: 15px; font-weight: bold; color: {text}; margin-bottom: 10px; }}

        QPushButton {{
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            text-align: left;
            color: {btn_text};
        }}
        #PrimaryBtn {{ background: {primary}; }}
        #PrimaryBtn:hover {{ background: {primary_h}; }}
        #PrimaryBtn:disabled {{ background: {sec}; color: {muted}; }}
        #DangerBtn {{ background: {danger}; }}
        #DangerBtn:hover {{ background: {danger_h}; }}
        #DangerBtn:disabled {{ background: {sec}; color: {muted}; }}
        #SecondaryBtn {{ background: {sec}; }}
        #SecondaryBtn:hover {{ background: {sec_h}; }}
        #SecondaryBtn:disabled {{ background: {sec}; color: {muted}; }}

        #ThemeBtn {{
            background: {primary};
            color: {btn_text};
            padding: 10px 16px;
        }}
        #ThemeBtn:hover {{ background: {primary_h}; }}

        #InputField {{
            background: {input_bg};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            color: {text};
        }}
        #InputField:focus {{ border: 2px solid {primary}; }}
        #LogText {{
            background: {log_bg};
            border: 1px solid {border};
            border-radius: 8px;
            font-family: Consolas;
            font-size: 12px;
            color: {text};
            padding: 10px;
        }}
        QCheckBox {{ color: {text}; }}
        QCheckBox::indicator {{
            width: 18px; height: 18px;
            border: 1px solid {border};
            background: {input_bg};
        }}
        QCheckBox::indicator:checked {{ background: {primary}; }}
        """
        self.setStyleSheet(style)

    def start_bot(self):
        if not self.bot.running:
            self.bot.api_key = self.config.get("analyzer_api_key", "")
            self.bot.max_requests = int(self.config.get("max_requests", 100))
            self.bot.analyzer_model = self.config.get("analyzer_model", "gpt-4o")
            self.bot.start()
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.pause_btn.setEnabled(True)
            self.update_status("Запущен")

    def stop_bot(self):
        self.bot.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.update_status("Остановлен")

    def pause_bot(self):
        if self.bot.running:
            self.bot.paused = not self.bot.paused
            self.pause_btn.setText(" Продолжить" if self.bot.paused else " Пауза")
            self.update_status("На паузе" if self.bot.paused else "Запущен")

    def update_status(self, txt):
        self.status_label.setText(f"● Статус: {txt}")

    def log_text(self, txt):
        self.log_textbox.append(f"[{datetime.now().strftime('%H:%M:%S')}] {txt}")

    def save_settings(self):
        self.config["url"] = self.url_edit.text()
        self.config["analyzer_api_key"] = self.api_edit.text()
        self.config["analyzer_model"] = self.model_edit.text().strip() or "gpt-4o"
        try:
            self.config["delays"]["min_between_actions"] = float(self.delay_min.text())
            self.config["delays"]["max_between_actions"] = float(self.delay_max.text())
            self.config["max_requests"] = int(self.max_req_edit.text())
        except:
            pass
        self.config["antibot"]["random_mouse_movement"] = self.antibot_check.isChecked()
        save_config(self.config)
        self.bot.api_key = self.config["analyzer_api_key"]
        self.bot.max_requests = self.config.get("max_requests", 100)
        self.bot.analyzer_model = self.config.get("analyzer_model", "gpt-4o")
        self.log_text("✅ Настройки сохранены.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
