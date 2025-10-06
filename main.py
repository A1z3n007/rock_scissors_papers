import io, os, random, tempfile, json, time, csv, threading
from typing import Dict, Tuple, List
import requests
from PIL import Image
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
SAVE_PATH = os.path.join(tempfile.gettempdir(), "rps_suite_state.json")

RESULT_TEXT = {"win": "Победа 🎉", "lose": "Поражение 😿", "draw": "Ничья 😐"}

RPS_RULES = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
RPSLS_RULES = {
    "rock": ["scissors", "lizard"],
    "paper": ["rock", "spock"],
    "scissors": ["paper", "lizard"],
    "lizard": ["spock", "paper"],
    "spock": ["scissors", "rock"]
}

def cache_key(url: str) -> str:
    return url.replace("://", "_").replace("/", "_").replace("?", "_").replace("=", "_").replace("&", "_")

def cache_path_for(url: str) -> str:
    return os.path.join(tempfile.gettempdir(), f"rps_cache_{cache_key(url)}")

def cache_fetch(url: str, timeout: int = 12) -> bytes:
    p = cache_path_for(url)
    if os.path.exists(p) and os.path.getsize(p) > 0:
        with open(p, "rb") as f:
            return f.read()
    r = SESSION.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0","Accept":"*/*"}, allow_redirects=True)
    r.raise_for_status()
    with open(p, "wb") as f:
        f.write(r.content)
    return r.content

def load_ctk_image(url: str, size: Tuple[int, int]) -> ctk.CTkImage:
    data = cache_fetch(url)
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    return ctk.CTkImage(light_image=im, dark_image=im, size=size)

def default_state():
    return {
        "stats": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
        "ach": {},
        "theme": "dark",
        "leaderboard": {"reaction_best_ms": None, "guess_best_attempts": None, "rps_series_wins": 0, "rpsls_series_wins": 0},
        "skin": "twemoji",
        "mute": False
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

def decide(pair_rules, you: str, bot: str) -> str:
    if you == bot: return "draw"
    if isinstance(pair_rules[you], list): return "win" if bot in pair_rules[you] else "lose"
    return "win" if pair_rules[you] == bot else "lose"

class BaseGame(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        self.history = ctk.CTkTextbox(self, width=360, height=140)
        self.result = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.score = {"you": 0, "bot": 0, "round": 0}
        self.gfx = {"you": ctk.CTkLabel(self, text=""), "bot": ctk.CTkLabel(self, text="")}
        self.fast_mode = ctk.BooleanVar(value=True)
        self.series = BaseSeries()
        self.series_var = ctk.StringVar(value="1")
    def add_history(self, line: str):
        self.history.configure(state="normal"); self.history.insert("end", line + "\n"); self.history.see("end"); self.history.configure(state="disabled")
    def series_box(self, parent):
        row = ctk.CTkFrame(parent); row.pack(side="right")
        ctk.CTkLabel(row, text="Best-of-N:").pack(side="left", padx=4)
        cb = ctk.CTkComboBox(row, values=["1","3","5","7"], variable=self.series_var, width=70, command=self._on_series)
        cb.pack(side="left", padx=4)
    def _on_series(self, v):
        try: self.series.set_best_of(int(v))
        except: self.series.set_best_of(1)
    def update_global_stats(self, outcome: str):
        s = self.app.data["stats"]; s["games"] += 1
        if outcome == "win": s["wins"] += 1
        elif outcome == "lose": s["losses"] += 1
        else: s["draws"] += 1
        save_state(self.app.data)

class GameRPS(BaseGame):
    def __init__(self, master, app_ref):
        super().__init__(master, app_ref)
        self.icons_small = {}
        self.icons_big = {}
        self._build()
        threading.Thread(target=self._load, daemon=True).start()
    def _assets(self):
        skin = self.app.data.get("skin","twemoji"); return SKINS.get(skin, SKINS["twemoji"])["rps"]
    def _build(self):
        top = ctk.CTkFrame(self); top.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkLabel(top, text="Камень • Ножницы • Бумага", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=6)
        ctk.CTkSwitch(top, text="Быстрый режим", variable=self.fast_mode).pack(side="left", padx=6)
        self.series_box(top)
        mid = ctk.CTkFrame(self); mid.pack(fill="x", padx=12, pady=6)
        left = ctk.CTkFrame(mid); left.pack(side="left", expand=True, fill="both", padx=(0,6))
        right = ctk.CTkFrame(mid); right.pack(side="right", expand=True, fill="both", padx=(6,0))
        ctk.CTkLabel(left, text="Ты", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(8,0))
        self.gfx["you"].master = left; self.gfx["you"].pack(pady=8)
        ctk.CTkLabel(right, text="Бот", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(8,0))
        self.gfx["bot"].master = right; self.gfx["bot"].pack(pady=8)
        self.result.pack(pady=2)
        bottom = ctk.CTkFrame(self); bottom.pack(fill="x", padx=12, pady=(6,12))
        self.btns = {}
        for k, t in [("rock","Камень"),("scissors","Ножницы"),("paper","Бумага")]:
            b = ctk.CTkButton(bottom, text=t, command=lambda x=k: self.play(x), width=120); b.pack(side="left", padx=6)
            self.btns[k]=b
        self.history.pack(side="right", padx=(8,0))
    def _load(self):
        try:
            for k,u in self._assets().items():
                self.icons_small[k]=load_ctk_image(u, ICON_SIZE); self.icons_big[k]=load_ctk_image(u, CHOICE_SIZE)
            self.after(0, self._apply)
        except Exception as ex:
            self.after(0, lambda ex=ex: self.result.configure(text=f"Ошибка загрузки иконок: {ex}"))
    def _apply(self):
        for k,b in self.btns.items():
            if k in self.icons_small: b.configure(image=self.icons_small[k], compound="left", text=f" {b.cget('text')}")
        if "rock" in self.icons_big: self.gfx["you"].configure(image=self.icons_big["rock"])
        if "paper" in self.icons_big: self.gfx["bot"].configure(image=self.icons_big["paper"])
    def play(self, your_choice: str):
        bot_choice = random.choice(list(self._assets().keys()))
        if self.fast_mode.get():
            self._resolve(your_choice, bot_choice)
        else:
            for b in self.btns.values(): b.configure(state="disabled")
            self.result.configure(text="3… 2… 1…")
            def go():
                self._resolve(your_choice, bot_choice)
                for b in self.btns.values(): b.configure(state="normal")
            self.after(700, go)
    def _resolve(self, your_choice, bot_choice):
        if your_choice in self.icons_big: self.gfx["you"].configure(image=self.icons_big[your_choice])
        if bot_choice in self.icons_big: self.gfx["bot"].configure(image=self.icons_big[bot_choice])
        outcome = decide(RPS_RULES, your_choice, bot_choice)
        if outcome=="win": self.score["you"]+=1
        elif outcome=="lose": self.score["bot"]+=1
        self.score["round"]+=1
        self.result.configure(text=RESULT_TEXT[outcome]+f" • серия {self.series.p_wins}:{self.series.b_wins}/{self.series.best_of}")
        self.add_history(f"Раунд {self.score['round']}: Ты — {your_choice} • Бот — {bot_choice} → {RESULT_TEXT[outcome]}")
        self.update_global_stats(outcome)
        self.series.record(outcome)
        champ = self.series.champion()
        if champ:
            self.add_history(f"Серия best-of-{self.series.best_of}: победитель — {'Ты' if champ=='player' else 'Бот'}")
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
        self.result.configure(text=RESULT_TEXT[outcome]+f" • серия {self.series.p_wins}:{self.series.b_wins}/{self.series.best_of}")
        self.add_history(f"Раунд {self.score['round']}: Ты — {your_choice} • Бот — {bot_choice} → {RESULT_TEXT[outcome]}")
        self.update_global_stats(outcome)
        self.series.record(outcome)
        champ = self.series.champion()
        if champ:
            self.add_history(f"Серия best-of-{self.series.best_of}: победитель — {'Ты' if champ=='player' else 'Бот'}")
            self.series.reset_series()

class GameDice(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        self.img = {}
        self.result = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.face = ctk.CTkLabel(self, text="")
        self.history = ctk.CTkTextbox(self, width=360, height=140)
        self._build()
        threading.Thread(target=self._load, daemon=True).start()
    def _build(self):
        top = ctk.CTkFrame(self); top.pack(fill="x", padx=12, pady=(12,6))
        ctk.CTkLabel(top, text="Кости d6", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=6)
        mid = ctk.CTkFrame(self); mid.pack(fill="x", padx=12, pady=6)
        self.face.master = mid; self.face.pack(side="left", expand=True, padx=6, pady=6)
        self.result.pack(pady=2)
        bottom = ctk.CTkFrame(self); bottom.pack(fill="x", padx=12, pady=(6,12))
        ctk.CTkButton(bottom, text="Бросить", command=self.roll, width=160).pack(side="left", padx=6)
        self.history.pack(side="right", padx=(8,0))
    def _load(self):
        try:
            for k,u in ASSETS_MISC["dice"].items():
                self.img[k]=load_ctk_image(u, DICE_SIZE)
            self.after(0, lambda: self.face.configure(image=self.img["1"]))
        except Exception as ex:
            self.after(0, lambda ex=ex: self.result.configure(text=f"Ошибка загрузки кубика: {ex}"))
    def roll(self):
        self.result.configure(text="Катим…")
        def done():
            val = random.randint(1,6)
            if str(val) in self.img: self.face.configure(image=self.img[str(val)])
            self.result.configure(text=f"Выпало {val}")
            self.history.configure(state="normal"); self.history.insert("end", f"{val}\n"); self.history.see("end"); self.history.configure(state="disabled")
            self.app.data["stats"]["games"]+=1; save_state(self.app.data)
        self.after(500, done)

class GameReaction(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        self.state = "idle"
        self.start_time = 0.0
        self.result = ctk.CTkLabel(self, text="Нажми «Старт», жди сигнал, и кликай как можно быстрее", font=ctk.CTkFont(size=16))
        self.btn = ctk.CTkButton(self, text="Старт", command=self.start_test, width=200)
        self.signal_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.history = ctk.CTkTextbox(self, width=360, height=140)
        self._build()
    def _build(self):
        self.result.pack(pady=(20,8)); self.signal_lbl.pack(pady=6); self.btn.pack(pady=6); self.history.pack(pady=10)
    def start_test(self):
        self.result.configure(text="Жди сигнал…"); self.signal_lbl.configure(text=""); self.btn.configure(state="disabled")
        delay = random.uniform(1.1, 2.8)
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
        self.secret = random.randint(1,100)
        self.attempts = 0
        self.max_attempts = 7
        self.lbl = ctk.CTkLabel(self, text="Я загадал число 1..100. Попробуй угадать за 7 попыток.")
        self.entry = ctk.CTkEntry(self, width=140, placeholder_text="Число")
        self.btn = ctk.CTkButton(self, text="Проверить", command=self.check)
        self.res = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.history = ctk.CTkTextbox(self, width=360, height=140)
        self._build()
    def _build(self):
        self.lbl.pack(pady=(16,6)); row = ctk.CTkFrame(self); row.pack(pady=6)
        self.entry.master = row; self.entry.pack(side="left", padx=6)
        self.btn.master = row; self.btn.pack(side="left", padx=6)
        self.res.pack(pady=6); self.history.pack(pady=8)
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
            self.app.data["stats"]["losses"]+=1; self.app.data["stats"]["games"]+=1; save_state(self.app.data); self.reset_game()

class Dashboard(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        t = ctk.CTkLabel(self, text="Game Suite", font=ctk.CTkFont(size=22, weight="bold")); t.pack(pady=(16,6))
        p = ctk.CTkLabel(self, text="Лаунчер мини-игр без socketio.", wraplength=560); p.pack(pady=(0,12))
        self.cards = ctk.CTkFrame(self); self.cards.pack(padx=12, pady=12, fill="x")
        self._card("Камень/Ножницы/Бумага", lambda: self.app.show_page("rps"))
        self._card("RPSLS", lambda: self.app.show_page("rpsls"))
        self._card("Кости d6", lambda: self.app.show_page("dice"))
        self._card("Реакция", lambda: self.app.show_page("react"))
        self._card("Угадай число", lambda: self.app.show_page("guess"))
    def _card(self, title, action):
        f = ctk.CTkFrame(self); f.pack(fill="x", pady=6)
        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(f, text="Открыть", command=action, width=120).pack(side="right", padx=10, pady=10)

class Leaderboard(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        ctk.CTkLabel(self, text="Лидерборд", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(16,6))
        self.box = ctk.CTkTextbox(self, width=420, height=200); self.box.pack(padx=12, pady=12)
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
        ctk.CTkLabel(self, text="Настройки", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(16,6))
        row1 = ctk.CTkFrame(self); row1.pack(pady=6)
        ctk.CTkLabel(row1, text="Тема:").pack(side="left", padx=8)
        self.theme_var = ctk.StringVar(value=self.app.data.get("theme","dark"))
        ctk.CTkComboBox(row1, values=["dark","light","system"], variable=self.theme_var, command=self.on_theme).pack(side="left", padx=8)
        row2 = ctk.CTkFrame(self); row2.pack(pady=6)
        ctk.CTkLabel(row2, text="Скин:").pack(side="left", padx=8)
        self.skin_var = ctk.StringVar(value=self.app.data.get("skin","twemoji"))
        ctk.CTkComboBox(row2, values=list(SKINS.keys()), variable=self.skin_var, command=self.on_skin).pack(side="left", padx=8)
        row3 = ctk.CTkFrame(self); row3.pack(pady=6)
        self.info = ctk.CTkLabel(self, text=""); self.info.pack(pady=6)
        ctk.CTkButton(self, text="Экспорт CSV", command=self.export_csv).pack(pady=4)
        ctk.CTkButton(self, text="JSON-бэкап", command=self.export_json).pack(pady=4)
    def on_theme(self, v):
        ctk.set_appearance_mode(v); self.app.data["theme"]=v; save_state(self.app.data)
    def on_skin(self, v):
        self.app.data["skin"]=v; save_state(self.app.data); self.app.reload_icons()
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
        self.title("Game Suite — clean")
        self.geometry("1100x800"); self.minsize(900,650)
        self.data = load_state()
        try: ctk.set_appearance_mode(self.data.get("theme","dark"))
        except: pass
        self.sidebar = ctk.CTkFrame(self, width=200); self.sidebar.pack(side="left", fill="y")
        self.main = ctk.CTkFrame(self); self.main.pack(side="right", fill="both", expand=True)
        ctk.CTkLabel(self.sidebar, text="Меню", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(16,6))
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
        for b in self.btns.values(): b.pack(fill="x", padx=12, pady=6)
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
        self.prefetch_assets_async()
    def prefetch_assets_async(self):
        def job():
            urls = []
            skin = self.data.get("skin","twemoji")
            urls += list(SKINS[skin]["rps"].values())
            urls += list(SKINS[skin]["rpsls"].values())
            urls += list(ASSETS_MISC["dice"].values())
            for u in urls:
                try: cache_fetch(u)
                except: pass
        threading.Thread(target=job, daemon=True).start()
    def show_page(self, key):
        self.pages[self.current].pack_forget(); self.current=key; self.pages[key].pack(fill="both", expand=True)
    def reload_icons(self):
        self.pages["rps"]._load(); self.pages["rpsls"]._load()

if __name__ == "__main__":
    App().mainloop()
