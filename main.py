import io, os, random, tempfile, json, time, csv, threading
from typing import Tuple
import requests
from PIL import Image, ImageDraw
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

SESSION = requests.Session()
ADAPTER = requests.adapters.HTTPAdapter(pool_connections=16, pool_maxsize=32, max_retries=2)
SESSION.mount("http://", ADAPTER); SESSION.mount("https://", ADAPTER)

SKINS = {
    "twemoji": {
        "rps": {
            "rock": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/270a.png",
            "paper": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/270b.png",
            "scissors": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/2702.png"
        },
        "rpsls": {
            "rock": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/270a.png",
            "paper": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/270b.png",
            "scissors": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/2702.png",
            "lizard": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f98e.png",
            "spock": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f596.png"
        }
    },
    "noto": {
        "rps": {
            "rock": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/128/emoji_u270a.png",
            "paper": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/128/emoji_u270b.png",
            "scissors": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/128/emoji_u2702.png"
        },
        "rpsls": {
            "rock": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/128/emoji_u270a.png",
            "paper": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/128/emoji_u270b.png",
            "scissors": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/128/emoji_u2702.png",
            "lizard": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/128/emoji_u1f98e.png",
            "spock": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/128/emoji_u1f596.png"
        }
    }
}

ASSETS_MISC = {
    "dice": {
        "1": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Alea_1.png/240px-Alea_1.png",
        "2": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Alea_2.png/240px-Alea_2.png",
        "3": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Alea_3.png/240px-Alea_3.png",
        "4": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Alea_4.png/240px-Alea_4.png",
        "5": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Alea_5.png/240px-Alea_5.png",
        "6": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/Alea_6.png/240px-Alea_6.png"
    }
}

ICON_SIZE = (72, 72)
CHOICE_SIZE = (120, 120)
DICE_SIZE = (160, 160)
SAVE_PATH = os.path.join(tempfile.gettempdir(), "gamesuite_arcade_state.json")

RPS_RULES = {"rock": ["scissors"], "scissors": ["paper"], "paper": ["rock"]}
RPSLS_RULES = {
    "rock": ["scissors", "lizard"],
    "paper": ["rock", "spock"],
    "scissors": ["paper", "lizard"],
    "lizard": ["spock", "paper"],
    "spock": ["scissors", "rock"]
}

NEON_THEMES = {
    "cyber": {"bg":"#0b0520","panel":"#140a3a","frame":"#2a1170","text":"#e9f5ff","accent":"#ff2ba6","button":"#00ffd5","button2":"#00b3ff"},
    "synth": {"bg":"#120a25","panel":"#1a0f33","frame":"#3a176b","text":"#ffeefc","accent":"#ff5cf0","button":"#ffc400","button2":"#ff8a00"}
}
NEON = dict(NEON_THEMES["cyber"])

def cache_key(url: str) -> str:
    return url.replace("://", "_").replace("/", "_").replace("?", "_").replace("=", "_").replace("&", "_")

def cache_path_for(url: str) -> str:
    return os.path.join(tempfile.gettempdir(), f"gamesuite_cache_{cache_key(url)}")

def cache_fetch(url: str, timeout: int = 10) -> bytes:
    p = cache_path_for(url)
    if os.path.exists(p) and os.path.getsize(p) > 0:
        with open(p, "rb") as f:
            return f.read()
    r = SESSION.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0","Accept":"*/*"}, allow_redirects=True)
    r.raise_for_status()
    with open(p, "wb") as f:
        f.write(r.content)
    return r.content

def load_pil(url: str) -> Image.Image:
    data = cache_fetch(url)
    return Image.open(io.BytesIO(data)).convert("RGBA")

def ctk_image_from_pil(pil: Image.Image, size: Tuple[int,int]) -> ctk.CTkImage:
    return ctk.CTkImage(light_image=pil, dark_image=pil, size=size)

def make_arcade_bg(w=1100,h=800,cell=32):
    img = Image.new("RGBA",(w,h),NEON["bg"])
    dr = ImageDraw.Draw(img)
    for y in range(h):
        t = y/max(1,h-1)
        r = int(int(NEON["bg"][1:3],16)*(1-t) + 20*t)
        g = int(int(NEON["bg"][3:5],16)*(1-t) + 15*t)
        b = int(int(NEON["bg"][5:7],16)*(1-t) + 110*t)
        dr.line([(0,y),(w,y)], fill=(r,g,b,255))
    grid = Image.new("RGBA",(w,h),(0,0,0,0))
    d2 = ImageDraw.Draw(grid)
    c1=(0,255,213,40); c2=(255,43,166,70)
    for x in range(0,w,cell):
        d2.line([(x,0),(x,h)], fill=c1, width=1)
    for y in range(0,h,cell):
        d2.line([(0,y),(w,y)], fill=c2, width=1)
    glow = Image.new("RGBA",(w,h),(0,0,0,0))
    d3 = ImageDraw.Draw(glow)
    d3.ellipse([w*0.3,-h*0.2,w*0.9,h*0.6], fill=(255,43,166,35))
    d3.ellipse([-w*0.2,h*0.3,w*0.5,h*1.1], fill=(0,179,255,35))
    out = Image.alpha_composite(img, glow)
    out = Image.alpha_composite(out, grid)
    return out

def make_overlay_rgba(w, h, a=32):
    return Image.new("RGBA", (w, h), (0, 0, 0, a))

def default_state():
    return {
        "stats": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
        "theme": "dark",
        "skin": "twemoji",
        "leaderboard": {"reaction_best_ms": None, "guess_best_attempts": None, "rps_series_wins": 0, "rpsls_series_wins": 0},
        "daily": {"date": None, "mode": "rps", "done": False, "result": None},
        "neon": "cyber"
    }

def load_state():
    if not os.path.exists(SAVE_PATH): return default_state()
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f: data = json.load(f)
        base = default_state()
        for k in base:
            if k not in data: data[k] = base[k]
        for k in base["leaderboard"]:
            if k not in data["leaderboard"]: data["leaderboard"][k] = base["leaderboard"][k]
        if "neon" not in data: data["neon"]="cyber"
        return data
    except:
        return default_state()

def save_state(st: dict):
    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as f: json.dump(st, f, ensure_ascii=False, indent=2)
    except:
        pass

class BaseSeries:
    def __init__(self):
        self.best_of = 1
        self.p_wins = 0
        self.b_wins = 0
    def set_best_of(self, n: int):
        self.best_of = n; self.p_wins = 0; self.b_wins = 0
    def record(self, outcome: str):
        if outcome == "win": self.p_wins += 1
        elif outcome == "lose": self.b_wins += 1
    def champion(self):
        need = (self.best_of + 1)//2
        if self.p_wins >= need: return "player"
        if self.b_wins >= need: return "bot"
        return None
    def reset_series(self):
        self.p_wins = 0; self.b_wins = 0

def decide(rules, you: str, bot: str) -> str:
    if you == bot: return "draw"
    return "win" if bot in rules[you] else "lose"

def style_title(lbl):
    try:
        f=ctk.CTkFont(family="Terminal", size=22, weight="bold")
    except:
        f=ctk.CTkFont(size=22, weight="bold")
    lbl.configure(font=f, text_color=NEON["text"])

def style_panel(frame):
    frame.configure(fg_color=NEON["panel"], border_color=NEON["frame"], border_width=2, corner_radius=12)

def style_button(btn):
    btn.configure(fg_color=NEON["button"], hover_color=NEON["button2"], text_color="#021018", corner_radius=12, border_color=NEON["accent"], border_width=2)

def glow_loop(widget, colors):
    i={"v":0}
    def tick():
        i["v"]=(i["v"]+1)%len(colors)
        try:
            widget.configure(fg_color=colors[i["v"]])
        except:
            pass
        widget.after(680,tick)
    tick()

class BaseGame(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        style_panel(self)
        self.history = ctk.CTkTextbox(self, width=360, height=140, fg_color="#0b0f2a", text_color=NEON["text"])
        self.result = ctk.CTkLabel(self, text="", text_color=NEON["text"], font=ctk.CTkFont(size=18, weight="bold"))
        self.score = {"you": 0, "bot": 0, "round": 0}
        self.gfx = {"you": ctk.CTkLabel(self, text=""), "bot": ctk.CTkLabel(self, text="")}
        self.fast_mode = ctk.BooleanVar(value=True)
        self.series = BaseSeries()
        self.series_var = ctk.StringVar(value="1")
    def add_history(self, line: str):
        self.history.configure(state="normal"); self.history.insert("end", line + "\n"); self.history.see("end"); self.history.configure(state="disabled")
    def series_box(self, parent):
        row = ctk.CTkFrame(parent); style_panel(row); row.pack(side="right", padx=6)
        ctk.CTkLabel(row, text="Best-of-N:", text_color=NEON["text"]).pack(side="left", padx=6)
        cb = ctk.CTkComboBox(row, values=["1","3","5","7"], variable=self.series_var, width=80, command=self._on_series, fg_color="#121639", button_color=NEON["accent"], border_color=NEON["frame"], border_width=2, text_color=NEON["text"])
        cb.pack(side="left", padx=6)
    def _on_series(self, v):
        try: self.series.set_best_of(int(v))
        except: self.series.set_best_of(1)
    def update_global_stats(self, outcome: str):
        s = self.app.data["stats"]; s["games"] += 1
        if outcome == "win": s["wins"] += 1
        elif outcome == "lose": s["losses"] += 1
        else: s["draws"] += 1
        save_state(self.app.data)
    def flash(self):
        try:
            self.configure(border_color=NEON["accent"])
            self.result.configure(text_color=NEON["accent"])
        except: pass
        def back():
            try:
                self.configure(border_color=NEON["frame"])
                self.result.configure(text_color=NEON["text"])
            except: pass
        self.after(180, back)

class GameRPS(BaseGame):
    def __init__(self, master, app_ref):
        super().__init__(master, app_ref)
        self.icons_small = {}
        self.icons_big = {}
        self.pil_small = {}
        self.pil_big = {}
        self._build()
        self._load_async()
    def _assets(self):
        skin = self.app.data.get("skin","twemoji"); return SKINS.get(skin, SKINS["twemoji"])["rps"]
    def _build(self):
        top = ctk.CTkFrame(self); style_panel(top); top.pack(fill="x", padx=12, pady=(12, 6))
        t = ctk.CTkLabel(top, text="Камень • Ножницы • Бумага"); style_title(t); t.pack(side="left", padx=10, pady=6)
        sw = ctk.CTkSwitch(top, text="Быстрый режим", variable=self.fast_mode, text_color=NEON["text"], fg_color=NEON["frame"], progress_color=NEON["accent"])
        sw.pack(side="left", padx=10)
        self.series_box(top)
        mid = ctk.CTkFrame(self); style_panel(mid); mid.pack(fill="x", padx=12, pady=6)
        left = ctk.CTkFrame(mid); style_panel(left); left.pack(side="left", expand=True, fill="both", padx=(0,6), pady=6)
        right = ctk.CTkFrame(mid); style_panel(right); right.pack(side="right", expand=True, fill="both", padx=(6,0), pady=6)
        ctk.CTkLabel(left, text="Ты", text_color=NEON["text"]).pack(pady=(8,0))
        self.gfx["you"].master = left; self.gfx["you"].pack(pady=8)
        ctk.CTkLabel(right, text="Бот", text_color=NEON["text"]).pack(pady=(8,0))
        self.gfx["bot"].master = right; self.gfx["bot"].pack(pady=8)
        self.result.pack(pady=6)
        bottom = ctk.CTkFrame(self); style_panel(bottom); bottom.pack(fill="x", padx=12, pady=(6,12))
        self.btns = {}
        for k, ttxt in [("rock","Камень"),("scissors","Ножницы"),("paper","Бумага")]:
            b = ctk.CTkButton(bottom, text=ttxt, command=lambda x=k: self.play(x), width=140)
            style_button(b); b.pack(side="left", padx=8, pady=8); glow_loop(b, [NEON["button"], NEON["button2"]])
            self.btns[k]=b
        self.history.pack(side="right", padx=(8,0), pady=8); self.history.configure(border_width=2, border_color=NEON["frame"])
    def _load_async(self):
        def job():
            try:
                for k,u in self._assets().items():
                    self.pil_small[k]=load_pil(u)
                    self.pil_big[k]=self.pil_small[k]
                self.after(0, self._apply_images)
            except Exception as ex:
                self.after(0, lambda ex=ex: self.result.configure(text=f"Ошибка загрузки: {ex}"))
        threading.Thread(target=job, daemon=True).start()
    def _apply_images(self):
        for k in self.pil_small:
            self.icons_small[k]=ctk_image_from_pil(self.pil_small[k], ICON_SIZE)
            self.icons_big[k]=ctk_image_from_pil(self.pil_big[k], CHOICE_SIZE)
        for k,b in self.btns.items():
            if k in self.icons_small: b.configure(image=self.icons_small[k], compound="left", text=f" {b.cget('text')}")
        if "rock" in self.icons_big: self.gfx["you"].configure(image=self.icons_big["rock"])
        if "paper" in self.icons_big: self.gfx["bot"].configure(image=self.icons_big["paper"])
    def play(self, your_choice: str):
        keys = list(self._assets().keys())
        bot_choice = random.choice(keys)
        if self.fast_mode.get():
            self._resolve(your_choice, bot_choice)
        else:
            for b in self.btns.values(): b.configure(state="disabled")
            self.result.configure(text="3… 2… 1…")
            def go():
                self._resolve(your_choice, bot_choice)
                for b in self.btns.values(): b.configure(state="normal")
            self.after(650, go)
    def _resolve(self, your_choice, bot_choice):
        if your_choice in self.icons_big: self.gfx["you"].configure(image=self.icons_big[your_choice])
        if bot_choice in self.icons_big: self.gfx["bot"].configure(image=self.icons_big[bot_choice])
        outcome = decide(RPS_RULES, your_choice, bot_choice)
        if outcome=="win": self.score["you"]+=1
        elif outcome=="lose": self.score["bot"]+=1
        self.score["round"]+=1
        self.result.configure(text={"win":"Победа 🎉","lose":"Поражение 😿","draw":"Ничья 😐"}[outcome]+f" • серия {self.series.p_wins}:{self.series.b_wins}/{self.series.best_of}")
        self.add_history(f"Раунд {self.score['round']}: {your_choice} vs {bot_choice} → {outcome}")
        self.update_global_stats(outcome)
        self.series.record(outcome)
        self.flash()
        champ = self.series.champion()
        if champ:
            self.add_history(f"Best-of-{self.series.best_of}: победил {'ты' if champ=='player' else 'бот'}")
            if self.app.data.get("daily",{}).get("date")==time.strftime("%Y%m%d") and not self.app.data["daily"].get("done"):
                self.app.data["daily"]["done"] = True
                self.app.data["daily"]["result"] = "win" if champ=="player" else "lose"
                save_state(self.app.data)
            if champ=="player": self.app.data["leaderboard"]["rps_series_wins"] += 1; save_state(self.app.data)
            self.series.reset_series()

class GameRPSLS(GameRPS):
    def _assets(self):
        skin = self.app.data.get("skin","twemoji"); return SKINS.get(skin, SKINS["twemoji"])["rpsls"]
    def _resolve(self, your_choice, bot_choice):
        if your_choice in self.icons_big: self.gfx["you"].configure(image=self.icons_big[your_choice])
        if bot_choice in self.icons_big: self.gfx["bot"].configure(image=self.icons_big[bot_choice])
        outcome = decide(RPSLS_RULES, your_choice, bot_choice)
        if outcome=="win": self.score["you"]+=1
        elif outcome=="lose": self.score["bot"]+=1
        self.score["round"]+=1
        self.result.configure(text={"win":"Победа 🎉","lose":"Поражение 😿","draw":"Ничья 😐"}[outcome]+f" • серия {self.series.p_wins}:{self.series.b_wins}/{self.series.best_of}")
        self.add_history(f"Раунд {self.score['round']}: {your_choice} vs {bot_choice} → {outcome}")
        self.update_global_stats(outcome)
        self.series.record(outcome)
        self.flash()
        champ = self.series.champion()
        if champ:
            self.add_history(f"Best-of-{self.series.best_of}: победил {'ты' if champ=='player' else 'бот'}")
            if champ=="player": self.app.data["leaderboard"]["rpsls_series_wins"] += 1; save_state(self.app.data)
            self.series.reset_series()

class GameDice(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        style_panel(self)
        self.img = {}
        self.pils = {}
        self.result = ctk.CTkLabel(self, text="", text_color=NEON["text"], font=ctk.CTkFont(size=18, weight="bold"))
        self.face = ctk.CTkLabel(self, text="")
        self.history = ctk.CTkTextbox(self, width=360, height=140, fg_color="#0b0f2a", text_color=NEON["text"])
        self._build()
        self._load_async()
    def _build(self):
        top = ctk.CTkFrame(self); style_panel(top); top.pack(fill="x", padx=12, pady=(12,6))
        t=ctk.CTkLabel(top, text="Кости d6"); style_title(t); t.pack(side="left", padx=10, pady=6)
        mid = ctk.CTkFrame(self); style_panel(mid); mid.pack(fill="x", padx=12, pady=6)
        self.face.master = mid; self.face.pack(side="left", expand=True, padx=6, pady=6)
        self.result.pack(pady=6)
        bottom = ctk.CTkFrame(self); style_panel(bottom); bottom.pack(fill="x", padx=12, pady=(6,12))
        roll = ctk.CTkButton(bottom, text="Бросить", command=self.roll, width=160); style_button(roll); glow_loop(roll,[NEON["button"],NEON["button2"]])
        roll.pack(side="left", padx=8, pady=8)
        self.history.pack(side="right", padx=(8,0), pady=8); self.history.configure(border_width=2, border_color=NEON["frame"])
    def _load_async(self):
        def job():
            try:
                for k,u in ASSETS_MISC["dice"].items():
                    self.pils[k]=load_pil(u)
                self.after(0, self._apply_images)
            except Exception as ex:
                self.after(0, lambda ex=ex: self.result.configure(text=f"Ошибка загрузки: {ex}"))
        threading.Thread(target=job, daemon=True).start()
    def _apply_images(self):
        for k,pil in self.pils.items():
            self.img[k]=ctk_image_from_pil(pil, DICE_SIZE)
        if "1" in self.img: self.face.configure(image=self.img["1"])
    def roll(self):
        self.result.configure(text="Катим…")
        def done():
            val = random.randint(1,6)
            if str(val) in self.img: self.face.configure(image=self.img[str(val)])
            self.result.configure(text=f"Выпало {val}")
            self.history.configure(state="normal"); self.history.insert("end", f"{val}\n"); self.history.see("end"); self.history.configure(state="disabled")
            self.app.data["stats"]["games"]+=1; save_state(self.app.data)
        self.after(420, done)

class GameReaction(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        style_panel(self)
        self.state = "idle"
        self.start_time = 0.0
        self.result = ctk.CTkLabel(self, text="Нажми «Старт», жди сигнал, и кликай как можно быстрее", text_color=NEON["text"])
        self.btn = ctk.CTkButton(self, text="Старт", command=self.start_test, width=200); style_button(self.btn); glow_loop(self.btn,[NEON["button"],NEON["button2"]])
        self.signal_lbl = ctk.CTkLabel(self, text="", text_color=NEON["accent"], font=ctk.CTkFont(size=18, weight="bold"))
        self.history = ctk.CTkTextbox(self, width=360, height=140, fg_color="#0b0f2a", text_color=NEON["text"])
        self._build()
    def _build(self):
        self.result.pack(pady=(20,8)); self.signal_lbl.pack(pady=6); self.btn.pack(pady=6); self.history.pack(pady=10); self.history.configure(border_width=2, border_color=NEON["frame"])
    def start_test(self):
        self.result.configure(text="Жди сигнал…"); self.signal_lbl.configure(text=""); self.btn.configure(state="disabled")
        delay = random.uniform(1.05, 2.4)
        def go():
            self.state = "ready"; self.signal_lbl.configure(text="ЖМИ!"); self.start_time = time.perf_counter(); self.btn.configure(text="Клик!", state="normal", command=self.stop_test)
        self.after(int(delay*1000), go)
    def stop_test(self):
        if self.state != "ready": return
        elapsed = round((time.perf_counter()-self.start_time)*1000, 1)
        self.result.configure(text=f"Реакция: {elapsed} мс")
        self.history.configure(state="normal"); self.history.insert("end", f"{elapsed} мс\n"); self.history.see("end"); self.history.configure(state="disabled")
        best = self.app.data["leaderboard"].get("reaction_best_ms")
        if best is None or elapsed < best: self.app.data["leaderboard"]["reaction_best_ms"] = elapsed
        self.app.data["stats"]["games"]+=1; save_state(self.app.data)
        self.btn.configure(text="Старт", command=self.start_test)

class GameGuess(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        style_panel(self)
        self.secret = random.randint(1,100)
        self.attempts = 0
        self.max_attempts = 7
        self.lbl = ctk.CTkLabel(self, text="Я загадал число 1..100. Попробуй угадать за 7 попыток.", text_color=NEON["text"])
        self.entry = ctk.CTkEntry(self, width=140, placeholder_text="Число", fg_color="#121639", border_color=NEON["frame"], border_width=2, text_color=NEON["text"])
        self.btn = ctk.CTkButton(self, text="Проверить", command=self.check); style_button(self.btn); glow_loop(self.btn,[NEON["button"],NEON["button2"]])
        self.res = ctk.CTkLabel(self, text="", text_color=NEON["text"], font=ctk.CTkFont(size=18, weight="bold"))
        self.history = ctk.CTkTextbox(self, width=360, height=140, fg_color="#0b0f2a", text_color=NEON["text"])
        self._build()
    def _build(self):
        self.lbl.pack(pady=(16,6)); row = ctk.CTkFrame(self); style_panel(row); row.pack(pady=6)
        self.entry.master = row; self.entry.pack(side="left", padx=6, pady=6)
        self.btn.master = row; self.btn.pack(side="left", padx=6, pady=6)
        self.res.pack(pady=6); self.history.pack(pady=8); self.history.configure(border_width=2, border_color=NEON["frame"])
    def reset_game(self):
        self.secret = random.randint(1,100); self.attempts = 0; self.entry.delete(0,"end"); self.res.configure(text="")
    def check(self):
        try: val = int(self.entry.get().strip())
        except: self.res.configure(text="Введи число"); return
        self.attempts += 1
        if val == self.secret:
            self.res.configure(text=f"Угадал за {self.attempts} попыток 🎯")
            best = self.app.data["leaderboard"].get("guess_best_attempts")
            if best is None or self.attempts < best: self.app.data["leaderboard"]["guess_best_attempts"] = self.attempts
            self.app.data["stats"]["games"]+=1; self.app.data["stats"]["wins"]+=1; save_state(self.app.data)
            self.reset_game(); return
        hint = "больше" if val < self.secret else "меньше"
        self.res.configure(text=f"Моё число {hint}")
        self.history.configure(state="normal"); self.history.insert("end", f"{val} → {hint}\n"); self.history.see("end"); self.history.configure(state="disabled")
        if self.attempts >= self.max_attempts:
            self.res.configure(text=f"Не угадал. Это было {self.secret}")
            self.app.data["stats"]["losses"]+=1; self.app.data["stats"]["games"]+=1; save_state(self.app.data)
            self.reset_game()

class Dashboard(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        style_panel(self)
        t = ctk.CTkLabel(self, text="GAME SUITE — ARCADE"); style_title(t); t.configure(text_color=NEON["accent"]); t.pack(pady=(16,6))
        p = ctk.CTkLabel(self, text="Мини-игры, неон и пиксельная атмосфера", text_color=NEON["text"])
        p.pack(pady=(0,12))
        self.cards = ctk.CTkFrame(self); style_panel(self.cards); self.cards.pack(padx=12, pady=12, fill="x")
        self._card("Камень/Ножницы/Бумага", lambda: self.app.show_page("rps"))
        self._card("RPSLS", lambda: self.app.show_page("rpsls"))
        self._card("Кости d6", lambda: self.app.show_page("dice"))
        self._card("Реакция", lambda: self.app.show_page("react"))
        self._card("Угадай число", lambda: self.app.show_page("guess"))
        self._card("Лидерборд", lambda: self.app.show_page("leaderboard"))
        self._card("Настройки", lambda: self.app.show_page("settings"))
        b = ctk.CTkButton(self, text="Дневной челлендж", command=self.daily_start); style_button(b); glow_loop(b,[NEON["button"],NEON["button2"]]); b.pack(pady=8)
    def _card(self, title, action):
        f = ctk.CTkFrame(self.cards); style_panel(f); f.pack(fill="x", pady=8, padx=8)
        ctk.CTkLabel(f, text=title, text_color=NEON["text"]).pack(side="left", padx=12, pady=12)
        b = ctk.CTkButton(f, text="Открыть", command=action, width=120); style_button(b); glow_loop(b,[NEON["button"],NEON["button2"]])
        b.pack(side="right", padx=12, pady=10)
    def daily_start(self):
        d = time.strftime("%Y%m%d")
        st = self.app.data["daily"]
        if st.get("date") != d:
            self.app.data["daily"] = {"date": d, "mode": "rps", "done": False, "result": None}
            save_state(self.app.data)
        random.seed(int(d))
        self.app.show_page("rps")
        page = self.app.pages["rps"]
        page.series.set_best_of(5)
        page.series_var.set("5")
        page.add_history(f"Дневной челлендж {d}: best-of-5")

class Leaderboard(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        style_panel(self)
        t=ctk.CTkLabel(self, text="Лидерборд"); style_title(t); t.pack(pady=(16,6))
        self.box = ctk.CTkTextbox(self, width=420, height=220, fg_color="#0b0f2a", text_color=NEON["text"]); self.box.pack(padx=12, pady=12)
        self.refresh()
    def refresh(self):
        lb = self.app.data["leaderboard"]
        self.box.configure(state="normal"); self.box.delete("1.0","end")
        r = lb.get("reaction_best_ms"); g = lb.get("guess_best_attempts")
        rs = lb.get("rps_series_wins",0); rls = lb.get("rpsls_series_wins",0)
        self.box.insert("end", f"Реакция — лучший результат: {('—' if r is None else str(r)+' мс')}\n")
        self.box.insert("end", f"Угадай число — минимум попыток: {('—' if g is None else g)}\n")
        self.box.insert("end", f"RPS — выигранных серий: {rs}\n")
        self.box.insert("end", f"RPSLS — выигранных серий: {rls}\n")
        self.box.configure(state="disabled")

class Settings(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        style_panel(self)
        t=ctk.CTkLabel(self, text="Настройки"); style_title(t); t.pack(pady=(16,6))
        row1 = ctk.CTkFrame(self); style_panel(row1); row1.pack(pady=6)
        ctk.CTkLabel(row1, text="Тема интерфейса", text_color=NEON["text"]).pack(side="left", padx=8)
        self.theme_var = ctk.StringVar(value=self.app.data.get("theme","dark"))
        ctk.CTkComboBox(row1, values=["dark","light","system"], variable=self.theme_var, command=self.on_theme, fg_color="#121639", button_color=NEON["accent"], border_color=NEON["frame"], border_width=2, text_color=NEON["text"]).pack(side="left", padx=8, pady=8)
        row2 = ctk.CTkFrame(self); style_panel(row2); row2.pack(pady=6)
        ctk.CTkLabel(row2, text="Скин эмодзи", text_color=NEON["text"]).pack(side="left", padx=8)
        self.skin_var = ctk.StringVar(value=self.app.data.get("skin","twemoji"))
        ctk.CTkComboBox(row2, values=list(SKINS.keys()), variable=self.skin_var, command=self.on_skin, fg_color="#121639", button_color=NEON["accent"], border_color=NEON["frame"], border_width=2, text_color=NEON["text"]).pack(side="left", padx=8, pady=8)
        row3 = ctk.CTkFrame(self); style_panel(row3); row3.pack(pady=6)
        ctk.CTkLabel(row3, text="Неоновая палитра", text_color=NEON["text"]).pack(side="left", padx=8)
        self.neo_var = ctk.StringVar(value=self.app.data.get("neon","cyber"))
        ctk.CTkComboBox(row3, values=list(NEON_THEMES.keys()), variable=self.neo_var, command=self.on_neon, fg_color="#121639", button_color=NEON["accent"], border_color=NEON["frame"], border_width=2, text_color=NEON["text"]).pack(side="left", padx=8, pady=8)
        self.info = ctk.CTkLabel(self, text="", text_color=NEON["text"]); self.info.pack(pady=6)
        b1=ctk.CTkButton(self, text="Экспорт CSV", command=self.export_csv); style_button(b1); glow_loop(b1,[NEON["button"],NEON["button2"]]); b1.pack(pady=6)
        b2=ctk.CTkButton(self, text="JSON-бэкап", command=self.export_json); style_button(b2); glow_loop(b2,[NEON["button2"],NEON["button"]]); b2.pack(pady=2)
    def on_theme(self, v):
        ctk.set_appearance_mode(v); self.app.data["theme"]=v; save_state(self.app.data)
    def on_skin(self, v):
        self.app.data["skin"]=v; save_state(self.app.data); self.app.reload_icons()
    def on_neon(self, v):
        self.app.data["neon"]=v; NEON.clear(); NEON.update(NEON_THEMES[v]); save_state(self.app.data); self.app.redraw_theme()
    def export_csv(self):
        p = os.path.join(tempfile.gettempdir(), "gamesuite_stats.csv")
        s = self.app.data["stats"]; lb = self.app.data["leaderboard"]
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["metric","value"])
            for k,v in s.items(): w.writerow([f"stats.{k}", v])
            for k,v in lb.items(): w.writerow([f"leaderboard.{k}", v])
        self.info.configure(text=f"CSV: {p}")
    def export_json(self):
        p = os.path.join(tempfile.gettempdir(), "gamesuite_backup.json")
        with open(p, "w", encoding="utf-8") as f: json.dump(self.app.data, f, ensure_ascii=False, indent=2)
        self.info.configure(text=f"JSON: {p}")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Game Suite — Arcade")
        self.geometry("1100x800"); self.minsize(940,660)
        self.data = load_state()
        try: ctk.set_appearance_mode(self.data.get("theme","dark"))
        except: pass
        NEON.clear(); NEON.update(NEON_THEMES.get(self.data.get("neon","cyber"), NEON_THEMES["cyber"]))
        self.bg_img_pil = make_arcade_bg(1100,800,32)
        self.bg_img = ctk.CTkImage(light_image=self.bg_img_pil, dark_image=self.bg_img_pil, size=(1100,800))
        self.bg = ctk.CTkLabel(self, text="", image=self.bg_img); self.bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.overlay_pil = make_overlay_rgba(1100, 800, 28)
        self.overlay_img = ctk.CTkImage(light_image=self.overlay_pil, dark_image=self.overlay_pil, size=(1100, 800))
        self.overlay = ctk.CTkLabel(self, text="", image=self.overlay_img); self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.sidebar = ctk.CTkFrame(self, width=220); style_panel(self.sidebar); self.sidebar.place(x=10,y=10, relheight=0.96)
        self.main = ctk.CTkFrame(self); style_panel(self.main); self.main.place(x=240,y=10, relwidth=0.76, relheight=0.96)
        m=ctk.CTkLabel(self.sidebar, text="МЕНЮ"); style_title(m); m.pack(pady=(10,10))
        self.btns = {
            "home": ctk.CTkButton(self.sidebar, text="Лаунчер", command=lambda: self.show_page("home")),
            "rps": ctk.CTkButton(self.sidebar, text="RPS", command=lambda: self.show_page("rps")),
            "rpsls": ctk.CTkButton(self.sidebar, text="RPSLS", command=lambda: self.show_page("rpsls")),
            "dice": ctk.CTkButton(self.sidebar, text="Кости d6", command=lambda: self.show_page("dice")),
            "react": ctk.CTkButton(self.sidebar, text="Реакция", command=lambda: self.show_page("react")),
            "guess": ctk.CTkButton(self.sidebar, text="Угадай число", command=lambda: self.show_page("guess")),
            "leaderboard": ctk.CTkButton(self.sidebar, text="Лидерборд", command=lambda: self.show_page("leaderboard")),
            "settings": ctk.CTkButton(self.sidebar, text="Настройки", command=lambda: self.show_page("settings"))
        }
        for b in self.btns.values():
            style_button(b); b.pack(fill="x", padx=12, pady=6); glow_loop(b,[NEON["button"], NEON["button2"]])
        self.splash = ctk.CTkFrame(self); style_panel(self.splash)
        self.splash.place(relx=0, rely=0, relwidth=1, relheight=1)
        title = ctk.CTkLabel(self.splash, text="GAME SUITE", font=ctk.CTkFont(size=42, weight="bold"), text_color=NEON["accent"])
        title.pack(pady=40)
        self.press = ctk.CTkLabel(self.splash, text="PRESS START", font=ctk.CTkFont(size=24, weight="bold"), text_color=NEON["text"])
        self.press.pack(pady=10)
        btn = ctk.CTkButton(self.splash, text="START", command=self._start_from_splash); style_button(btn); glow_loop(btn,[NEON["button"],NEON["button2"]]); btn.pack(pady=20)
        self._blink()
        self.pages = {}
        self.pages["home"]=Dashboard(self.main, self); self.pages["home"].pack(fill="both", expand=True)
        self.pages["rps"]=GameRPS(self.main, self)
        self.pages["rpsls"]=GameRPSLS(self.main, self)
        self.pages["dice"]=GameDice(self.main, self)
        self.pages["react"]=GameReaction(self.main, self)
        self.pages["guess"]=GameGuess(self.main, self)
        self.pages["leaderboard"]=Leaderboard(self.main, self)
        self.pages["settings"]=Settings(self.main, self)
        self.current="home"
        self._prefetch_all_async()
        self.bind("<Configure>", self._on_resize)
    def _blink(self):
        cur = self.press.cget("text_color")
        new = NEON["accent"] if cur==NEON["text"] else NEON["text"]
        try: self.press.configure(text_color=new)
        except: pass
        self.after(600, self._blink)
    def _start_from_splash(self):
        try: self.splash.destroy()
        except: pass
    def _prefetch_all_async(self):
        def job():
            try:
                skin = self.data.get("skin","twemoji")
                urls = list(SKINS[skin]["rps"].values())+list(SKINS[skin]["rpsls"].values())+list(ASSETS_MISC["dice"].values())
                for u in urls:
                    try: cache_fetch(u, timeout=6)
                    except: pass
            except: pass
        threading.Thread(target=job, daemon=True).start()
    def show_page(self, key):
        self.pages[self.current].pack_forget(); self.current=key; self.pages[key].pack(fill="both", expand=True)
    def reload_icons(self):
        self.pages["rps"]._load_async(); self.pages["rpsls"]._load_async()
    def redraw_theme(self):
        w,h = max(800, self.winfo_width()), max(600, self.winfo_height())
        self.bg_img_pil = make_arcade_bg(w,h,32)
        self.bg_img = ctk.CTkImage(light_image=self.bg_img_pil, dark_image=self.bg_img_pil, size=(w,h))
        self.bg.configure(image=self.bg_img)
        self.overlay_pil = make_overlay_rgba(w,h,28)
        self.overlay_img = ctk.CTkImage(light_image=self.overlay_pil, dark_image=self.overlay_pil, size=(w,h))
        self.overlay.configure(image=self.overlay_img)
    def _on_resize(self, e):
        try:
            w,h = max(800, self.winfo_width()), max(600, self.winfo_height())
            self.bg_img_pil = make_arcade_bg(w,h,32)
            self.bg_img = ctk.CTkImage(light_image=self.bg_img_pil, dark_image=self.bg_img_pil, size=(w,h))
            self.bg.configure(image=self.bg_img)
            self.overlay_pil = make_overlay_rgba(w,h,28)
            self.overlay_img = ctk.CTkImage(light_image=self.overlay_pil, dark_image=self.overlay_pil, size=(w,h))
            self.overlay.configure(image=self.overlay_img)
        except:
            pass

if __name__ == "__main__":
    App().mainloop()
