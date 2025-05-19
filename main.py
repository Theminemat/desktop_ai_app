import asyncio
import os
import re
import speech_recognition as sr
import playsound
import webbrowser
import tkinter as tk
from tkinter import ttk  # Für bessere Widgets
from tkinter import messagebox  # Für Nachrichten
from threading import Thread, Event
from edge_tts import Communicate
from google import genai as gai
from google.genai import types
import numpy as np
import time
import pygame
import sys
import json  # Für config.json

# System Tray Imports
from pystray import MenuItem as item, Icon as icon
from PIL import Image, ImageDraw

pygame.mixer.init()

# --- Konfigurationsmanagement ---
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "api_key": "DEIN_GOOGLE_AI_API_KEY_HIER_EINFUEGEN",
    "codeword": "manfred",
    "stopwords": ["stopp", "stop", "halte an", "halt an"],
    "max_history": 5
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)  # Erstelle Default-Config, falls nicht vorhanden
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Stelle sicher, dass alle Keys vorhanden sind, füge Defaults hinzu, falls nicht
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
    except (json.JSONDecodeError, IOError) as e:
        print(f"Fehler beim Laden der Konfiguration ({CONFIG_FILE}): {e}. Verwende Standardkonfiguration.")
        return DEFAULT_CONFIG


def save_config(config_data):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        print(f"Konfiguration gespeichert in {CONFIG_FILE}")
    except IOError as e:
        print(f"Fehler beim Speichern der Konfiguration ({CONFIG_FILE}): {e}")


# Lade Konfiguration beim Start
app_config = load_config()

CodeWord = app_config.get("codeword", DEFAULT_CONFIG["codeword"])
StopWords = app_config.get("stopwords", DEFAULT_CONFIG["stopwords"])
MAX_HISTORY = app_config.get("max_history", DEFAULT_CONFIG["max_history"])
API_KEY = os.getenv("GEMINI_API_KEY") or app_config.get("api_key", DEFAULT_CONFIG["api_key"])

if not API_KEY or API_KEY == "DEIN_GOOGLE_AI_API_KEY_HIER_EINFUEGEN":
    print("WARNUNG: API-Key nicht konfiguriert. Bitte in config.json oder als GEMINI_API_KEY Umgebungsvariable setzen.")
    # Hier könntest du die Anwendung beenden oder in einen eingeschränkten Modus gehen
    # sys.exit("API Key fehlt.") # Beispiel für Beenden

client = gai.Client(api_key=API_KEY)

chat_config = types.GenerateContentConfig(
    system_instruction=(
        "You are Manfred, a highly intelligent and efficient AI assistant "
        "Reply without formatting and keep replys short and simple "
        "You always speak respectfully, and in fluent German. "
        "Your responses must be clear, concise, and helpful — avoid unnecessary elaboration, especially for simple tasks. "
        "A good amount of humor is is good to keep the conversation natural - friend like. Your top priorities are efficiency and clarity. "
        "Generate the reply that a dumb TTS can read it correctly"
        "You can open links on my pc by just including them in your message without formatting just start links with https:// also use this when the users asks you to search on a website like youtube"
    )
)
chat = client.chats.create(model="gemini-2.0-flash", config=chat_config)

recognizer = sr.Recognizer()
mic = sr.Microphone()

with mic as source:
    recognizer.adjust_for_ambient_noise(source)

# Events
speech_stop_event = Event()
main_loop_stop_event = Event()

# Globale Referenzen
overlay = None
main_loop_thread = None
tray_icon = None
settings_window_instance = None  # Für das Einstellungsfenster


class ModernOverlay(tk.Tk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.9)
        self.config(bg='#0D1117')

        self.corner_radius = 20
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = 280
        height = 80
        x_pos = screen_width - width - 20
        y_pos = screen_height - height - 50
        self.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

        self.canvas = tk.Canvas(self, width=width, height=height, bg='#0D1117', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.create_rectangle(self.corner_radius, 0, width - self.corner_radius, height, fill='#0D1117',
                                     outline='')
        self.canvas.create_rectangle(0, self.corner_radius, width, height - self.corner_radius, fill='#0D1117',
                                     outline='')
        self.canvas.create_arc(0, 0, self.corner_radius * 2, self.corner_radius * 2, start=90, extent=90,
                               fill='#0D1117', outline='')
        self.canvas.create_arc(width - self.corner_radius * 2, 0, width, self.corner_radius * 2, start=0, extent=90,
                               fill='#0D1117', outline='')
        self.canvas.create_arc(0, height - self.corner_radius * 2, self.corner_radius * 2, height, start=180, extent=90,
                               fill='#0D1117', outline='')
        self.canvas.create_arc(width - self.corner_radius * 2, height - self.corner_radius * 2, width, height,
                               start=270, extent=90, fill='#0D1117', outline='')

        self.border = self.canvas.create_rectangle(2, 2, width - 2, height - 2, outline='#1E90FF', width=2)

        self.mode = None
        self.orb_size = 36
        self.orb_x = 40
        self.orb_y = height // 2

        gradient = []
        for i in range(100):
            r = int(0 + (64 * i / 100))
            g = int(170 + (50 * i / 100))
            b = int(210 + (45 * i / 100))
            gradient.append(f'#{r:02x}{g:02x}{b:02x}')
        self.gradient = gradient

        self.orb_id = self.canvas.create_oval(
            self.orb_x - self.orb_size // 2, self.orb_y - self.orb_size // 2,
            self.orb_x + self.orb_size // 2, self.orb_y + self.orb_size // 2,
            fill='#10AFCF', width=0)
        self.highlight_id = self.canvas.create_oval(
            self.orb_x - self.orb_size // 3, self.orb_y - self.orb_size // 3,
            self.orb_x - 2, self.orb_y - 2,
            fill='white', width=0)

        self.font = ("Segoe UI", 14, "bold")
        self.text_id = self.canvas.create_text(
            self.orb_x + self.orb_size // 2 + 20, height // 2,
            anchor='w', text="", fill='#10DFFF', font=self.font)

        self.particles = []
        self.max_particles = 15
        self.pulse_direction = 1
        self.pulse_size = 0
        self.pulse_speed = 0.05
        self.pulse_max = 10
        self.listening_speed = 0.05
        self.speaking_speed = 0.12
        self.particle_chance = 0.05

        self.canvas.bind("<Button-1>", self.on_click)
        self.withdraw()
        self.after(20, self._animate)

    def on_click(self, event):
        if self.mode == 'speaking':
            speech_stop_event.set()

    def set_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        if mode == 'listening':
            self.canvas.itemconfig(self.orb_id, fill='#10EFCF')
            self.canvas.itemconfig(self.text_id, text="Höre zu...", fill='#10EFCF')
            self.canvas.itemconfig(self.border, outline='#10EFCF')
            self.pulse_speed = self.listening_speed
            self.particle_chance = 0.05
            self.show()
        elif mode == 'speaking':
            self.canvas.itemconfig(self.orb_id, fill='#10AFCF')
            self.canvas.itemconfig(self.text_id, text="Spreche...", fill='#10DFFF')
            self.canvas.itemconfig(self.border, outline='#1E90FF')
            self.pulse_speed = self.speaking_speed
            self.particle_chance = 0.2
            speech_stop_event.clear()
            self.show()
        else:
            self.hide()
        self.particles = []

    def show(self):
        if not self.winfo_viewable():
            self.deiconify()

    def hide(self):
        if self.winfo_viewable():
            self.withdraw()

    def _create_particle(self):
        if len(self.particles) >= self.max_particles: return
        angle = np.random.uniform(0, 2 * np.pi)
        speed = np.random.uniform(0.5, 2.0)
        if self.mode == 'speaking': speed *= 1.5
        size = np.random.uniform(2, 6)
        distance = np.random.uniform(0, 10)
        x = self.orb_x + distance * np.cos(angle)
        y = self.orb_y + distance * np.sin(angle)
        colors = ['#10AFCF', '#1E90FF', '#00CED1', '#48D1CC', '#20B2AA']
        color = np.random.choice(colors)
        particle = {
            'id': self.canvas.create_oval(x - size / 2, y - size / 2, x + size / 2, y + size / 2, fill=color, width=0),
            'dx': speed * np.cos(angle), 'dy': speed * np.sin(angle),
            'ttl': np.random.uniform(10, 30), 'fade': np.random.uniform(0.92, 0.98)}
        self.particles.append(particle)

    def _update_particles(self):
        particles_to_remove = []
        for i, p in enumerate(self.particles):
            self.canvas.move(p['id'], p['dx'], p['dy'])
            p['ttl'] -= 1
            if p['ttl'] <= 0:
                particles_to_remove.append(i)
                self.canvas.delete(p['id'])
            else:
                x1, y1, x2, y2 = self.canvas.coords(p['id'])
                width, height = x2 - x1, y2 - y1
                new_width, new_height = width * p['fade'], height * p['fade']
                center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
                self.canvas.coords(p['id'], center_x - new_width / 2, center_y - new_height / 2,
                                   center_x + new_width / 2, center_y + new_height / 2)
        for i in sorted(particles_to_remove, reverse=True):
            self.particles.pop(i)

    def _animate(self):
        self.pulse_size += self.pulse_speed * self.pulse_direction
        if self.pulse_size > self.pulse_max or self.pulse_size < 0:
            self.pulse_direction *= -1
        size = self.orb_size + self.pulse_size
        self.canvas.coords(self.orb_id, self.orb_x - size // 2, self.orb_y - size // 2,
                           self.orb_x + size // 2, self.orb_y + size // 2)
        highlight_size = size * 0.6
        self.canvas.coords(self.highlight_id, self.orb_x - highlight_size // 2,
                           self.orb_y - highlight_size // 2, self.orb_x, self.orb_y)

        if self.mode == 'listening':
            pulse_factor = abs(self.pulse_size / self.pulse_max)
            color_idx = int(20 + pulse_factor * 30)
            self.canvas.itemconfig(self.orb_id, fill=self.gradient[color_idx])
            if np.random.random() < self.particle_chance: self._create_particle()
        elif self.mode == 'speaking':
            pulse_factor = abs(self.pulse_size / self.pulse_max)
            color_idx = int(40 + pulse_factor * 50)
            self.canvas.itemconfig(self.orb_id, fill=self.gradient[min(99, color_idx)])
            if np.random.random() < self.particle_chance: self._create_particle()

        self._update_particles()
        self.after(20, self._animate)


class SettingsWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Manfred AI Einstellungen")
        self.geometry("450x300")  # Angepasste Größe
        self.transient(master)  # Bleibt über dem Hauptfenster (falls master gesetzt ist)
        self.grab_set()  # Modal

        self.config_vars = {}
        self.current_config = load_config()

        # Styling
        style = ttk.Style(self)
        style.configure("TLabel", padding=6)
        style.configure("TEntry", padding=6)
        style.configure("TButton", padding=6)

        main_frame = ttk.Frame(self, padding="10 10 10 10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # API Key
        ttk.Label(main_frame, text="Google AI API Key:").grid(row=0, column=0, sticky=tk.W)
        self.config_vars["api_key"] = tk.StringVar(value=self.current_config.get("api_key"))
        ttk.Entry(main_frame, textvariable=self.config_vars["api_key"], width=40).grid(row=0, column=1, sticky=tk.EW)

        # Codeword
        ttk.Label(main_frame, text="Codeword:").grid(row=1, column=0, sticky=tk.W)
        self.config_vars["codeword"] = tk.StringVar(value=self.current_config.get("codeword"))
        ttk.Entry(main_frame, textvariable=self.config_vars["codeword"], width=40).grid(row=1, column=1, sticky=tk.EW)

        # Stopwords (als Komma-separierter String)
        ttk.Label(main_frame, text="Stopwords (Komma-getrennt):").grid(row=2, column=0, sticky=tk.W)
        stopwords_str = ", ".join(self.current_config.get("stopwords", []))
        self.config_vars["stopwords"] = tk.StringVar(value=stopwords_str)
        ttk.Entry(main_frame, textvariable=self.config_vars["stopwords"], width=40).grid(row=2, column=1, sticky=tk.EW)

        # Max History
        ttk.Label(main_frame, text="Max. Chat Verlauf:").grid(row=3, column=0, sticky=tk.W)
        self.config_vars["max_history"] = tk.IntVar(value=self.current_config.get("max_history"))
        ttk.Entry(main_frame, textvariable=self.config_vars["max_history"], width=10).grid(row=3, column=1,
                                                                                           sticky=tk.W)  # sticky W für linksbündig

        # Buttons Frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20, sticky=tk.E)

        ttk.Button(button_frame, text="Speichern", command=self.save_settings_action).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=self.destroy).pack(side=tk.LEFT, padx=5)

        main_frame.columnconfigure(1, weight=1)  # Spalte 1 soll sich ausdehnen

        self.protocol("WM_DELETE_WINDOW", self.destroy)  # Handle Schließen über X

    def save_settings_action(self):
        global CodeWord, StopWords, MAX_HISTORY, API_KEY, client, chat, chat_config, app_config

        new_config = {}
        new_config["api_key"] = self.config_vars["api_key"].get()
        new_config["codeword"] = self.config_vars["codeword"].get()

        stopwords_str = self.config_vars["stopwords"].get()
        new_config["stopwords"] = [s.strip() for s in stopwords_str.split(',') if s.strip()]

        try:
            new_config["max_history"] = int(self.config_vars["max_history"].get())
            if new_config["max_history"] < 1:
                messagebox.showerror("Fehler", "Max. Chat Verlauf muss mindestens 1 sein.")
                return
        except ValueError:
            messagebox.showerror("Fehler", "Max. Chat Verlauf muss eine Zahl sein.")
            return

        save_config(new_config)
        app_config = new_config  # Update laufende Konfiguration

        # Einige Einstellungen direkt anwenden (andere erfordern Neustart)
        CodeWord = new_config["codeword"]
        StopWords = new_config["stopwords"]

        restart_needed = False
        if MAX_HISTORY != new_config["max_history"]:
            MAX_HISTORY = new_config["max_history"]
            restart_needed = True  # Chat muss neu initialisiert werden

        if API_KEY != new_config["api_key"]:
            API_KEY = new_config["api_key"]
            restart_needed = True  # Client und Chat müssen neu initialisiert werden

        if restart_needed:
            messagebox.showinfo("Einstellungen gespeichert",
                                "Einstellungen wurden gespeichert. Einige Änderungen (API Key, Max. Verlauf) erfordern einen Neustart der Anwendung, um wirksam zu werden.")
            # Optional: Client und Chat neu initialisieren, wenn möglich und gewünscht
            # try:
            #     client = gai.Client(api_key=API_KEY)
            #     chat = client.chats.create(model="gemini-2.0-flash", config=chat_config) # chat_config bleibt gleich
            #     print("AI Client und Chat wurden mit neuem API Key / Verlaufseinstellungen neu initialisiert.")
            # except Exception as e:
            #     print(f"Fehler bei der Reinitialisierung des AI Clients: {e}")
            #     messagebox.showerror("Fehler", "Konnte AI Client nicht mit neuem API Key initialisieren. Bitte manuell neu starten.")
        else:
            messagebox.showinfo("Einstellungen gespeichert",
                                "Einstellungen wurden erfolgreich gespeichert und angewendet.")

        self.destroy()


def set_overlay_mode_safe(mode):
    if overlay:
        overlay.after(0, lambda: overlay.set_mode(mode))


def speak_action():
    set_overlay_mode_safe('speaking')
    try:
        temp_audio_file = "reply_temp.mp3"
        if os.path.exists("reply.mp3"):
            try:
                os.replace("reply.mp3", temp_audio_file)
            except Exception as e:
                print(f"Konnte reply.mp3 nicht zu {temp_audio_file} umbenennen: {e}. Überspringe Abspielen.")
                set_overlay_mode_safe('listening' if not main_loop_stop_event.is_set() else None)
                return
        else:
            print("Keine reply.mp3 gefunden zum Abspielen.")
            set_overlay_mode_safe('listening' if not main_loop_stop_event.is_set() else None)
            return

        sound_thread = Thread(target=playsound.playsound, args=(temp_audio_file,), daemon=True)
        sound_thread.start()

        while sound_thread.is_alive() and not speech_stop_event.is_set() and not main_loop_stop_event.is_set():
            time.sleep(0.1)

        if speech_stop_event.is_set() or main_loop_stop_event.is_set():
            print("Sprachausgabe abgebrochen oder Hauptschleife gestoppt.")
            try:
                if os.name == 'nt':
                    playsound._playsoundWin.winCommand('stop', temp_audio_file)
            except Exception as e:
                print(f"Konnte Sound nicht stoppen (normal bei Abbruch): {e}")

        sound_thread.join(timeout=1.0)

        if os.path.exists(temp_audio_file):
            try:
                os.remove(temp_audio_file)
            except PermissionError:
                time.sleep(0.5)
                try:
                    os.remove(temp_audio_file)
                except Exception as e:
                    print(f"Konnte temp_audio_file nicht löschen: {e}")
            except Exception as e:
                print(f"Fehler beim Löschen von {temp_audio_file}: {e}")

    except Exception as e:
        print(f"Fehler beim Abspielen des Sounds: {e}")
    finally:
        speech_stop_event.clear()
        if not main_loop_stop_event.is_set():
            set_overlay_mode_safe('listening')
        else:
            set_overlay_mode_safe(None)


def main_loop_logic():
    global chat, CodeWord, StopWords  # Stelle sicher, dass globale Variablen verwendet werden
    pygame.mixer.music.load("sounds/start.mp3")
    pygame.mixer.music.play()
    listening_mode = False

    while not main_loop_stop_event.is_set():
        if listening_mode:
            set_overlay_mode_safe('listening')
        else:
            set_overlay_mode_safe(None)

        print("Warte auf Spracheingabe..." if not listening_mode else "Höre zu...")
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=2, phrase_time_limit=7)
        except sr.WaitTimeoutError:
            continue
        except Exception as e:
            print(f"Fehler mit Mikrofon: {e}")
            time.sleep(1)
            continue

        if main_loop_stop_event.is_set(): break

        try:
            text = recognizer.recognize_google(audio, language="de-DE")
            print(f"Erkannt: {text}")
            text_lower = text.lower()

            if not listening_mode:
                if CodeWord.lower() in text_lower:  # Verwende aktuelle CodeWord Variable
                    listening_mode = True
                    command = text_lower.split(CodeWord.lower(), 1)[-1].strip()
                    if not command:
                        print("Aktiviert. Warte auf Befehl...")
                        pygame.mixer.music.load("sounds/listening.mp3")
                        pygame.mixer.music.play()
                        asyncio.run(generate_mp3("Ja?"))
                        speak_action()
                        continue
                else:
                    continue
            else:
                if any(stop_word.lower() in text_lower for stop_word in StopWords):  # Verwende aktuelle StopWords
                    listening_mode = False
                    print("Modus deaktiviert (durch Stopword).")
                    set_overlay_mode_safe(None)
                    pygame.mixer.music.load("sounds/deaktivated.mp3")
                    pygame.mixer.music.play()
                    continue
                else:
                    command = text.strip()

            if not command:
                print("Kein verwertbarer Befehl.")
                continue

            print(f"Befehl erkannt: {command}")
            response = chat.send_message(command)
            print(f"Antwort: {response.text}")

            url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
            match = re.search(url_pattern, response.text)
            response_text_for_tts = response.text

            if match:
                url = match.group(0)
                if not url.startswith("http"):
                    url = "http://" + url
                print(f"Öffne Link aus Antwort: {url}")
                webbrowser.open(url)
                response_text_for_tts = re.sub(url_pattern, '', response.text).strip()
                if not response_text_for_tts:
                    response_text_for_tts = "Link geöffnet."

            if response_text_for_tts:
                asyncio.run(generate_mp3(response_text_for_tts))
                speak_action()
            else:
                set_overlay_mode_safe('listening')

            chat = trim_chat_history(chat)

        except sr.UnknownValueError:
            if listening_mode:
                print("Nichts verstanden.")
        except sr.RequestError as e:
            print(f"Fehler bei der Spracherkennung: {e}")
            asyncio.run(generate_mp3("Problem mit der Spracherkennung."))
            speak_action()
        except Exception as e:
            print(f"Ein Fehler in der Hauptschleife: {e}")

        if main_loop_stop_event.is_set(): break

    print("Main loop beendet.")
    set_overlay_mode_safe(None)


async def generate_mp3(text):
    if not text.strip():
        text = "Okay."
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    text = text.replace('\n', ' ').replace('\r', '')
    if not text.strip():
        text = "Verstanden."

    communicate = Communicate(text=text, voice="de-DE-ConradNeural")
    for _ in range(3):
        try:
            if os.path.exists("reply.mp3"):
                os.remove("reply.mp3")
            break
        except PermissionError:
            print("reply.mp3 ist noch in Benutzung, versuche es erneut...")
            await asyncio.sleep(0.2)
        except FileNotFoundError:
            break
        except Exception as e:
            print(f"Konnte reply.mp3 nicht löschen: {e}")
            break
    else:
        print("Konnte reply.mp3 nach mehreren Versuchen nicht löschen. Speichere als reply_new.mp3")
        try:
            await communicate.save("reply_new.mp3")
            return
        except Exception as save_err:
            print(f"Konnte MP3 auch als reply_new.mp3 nicht speichern: {save_err}")
            return

    try:
        await communicate.save("reply.mp3")
    except Exception as e:
        print(f"Fehler beim Speichern von reply.mp3: {e}")


def trim_chat_history(current_chat):
    global MAX_HISTORY  # Stelle sicher, dass die globale Variable verwendet wird
    history = current_chat.get_history()
    if len(history) > MAX_HISTORY * 2:  # Verwende aktuelle MAX_HISTORY
        trimmed_history = history[-(MAX_HISTORY * 2):]
        new_chat = client.chats.create(
            model="gemini-2.0-flash",
            config=current_chat._config,
            history=trimmed_history
        )
        print(f"Chat-Verlauf gekürzt. Alte Länge: {len(history)}, Neue Länge: {len(trimmed_history)}")
        return new_chat
    return current_chat


# --- Tray Icon Functions ---
def create_image(width, height, color1, color2):
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image


def get_icon_image():
    icon_path = "icon.png"
    if os.path.exists(icon_path):
        try:
            return Image.open(icon_path)
        except Exception as e:
            print(f"Konnte icon.png nicht laden: {e}. Benutze Standard-Icon.")
    return create_image(64, 64, 'black', 'blue')


def on_settings_clicked(icon_instance, item_instance):
    global settings_window_instance, overlay
    if settings_window_instance is None or not settings_window_instance.winfo_exists():
        # Stelle sicher, dass das Overlay (als potenzieller Master) existiert, bevor das Einstellungsfenster erstellt wird
        if overlay:
            settings_window_instance = SettingsWindow(master=overlay)  # oder master=None, wenn kein Hauptfensterbezug
            settings_window_instance.lift()
            settings_window_instance.focus_force()  # Versuche, den Fokus zu erzwingen
        else:
            print("Overlay nicht initialisiert, kann Einstellungsfenster nicht öffnen.")
            messagebox.showwarning("Fehler",
                                   "Overlay ist nicht bereit. Einstellungsfenster kann nicht geöffnet werden.")
    else:
        settings_window_instance.lift()
        settings_window_instance.focus_force()


def on_exit_clicked(icon_instance, item_instance):
    print("Beende Anwendung...")
    global overlay, main_loop_thread, tray_icon

    main_loop_stop_event.set()
    speech_stop_event.set()

    if tray_icon:
        tray_icon.stop()
    print("Tray Icon gestoppt-Anfrage gesendet.")

    if overlay:
        print("Sende quit-Anfrage an Overlay (Tkinter mainloop)...")
        overlay.after(0, overlay.quit)


if __name__ == "__main__":
    overlay = ModernOverlay()

    tray_icon_image = get_icon_image()
    menu = (
        item('Einstellungen', on_settings_clicked),  # Neuer Menüpunkt
        item('Beenden', on_exit_clicked),
    )
    tray_icon = icon("ManfredAI", tray_icon_image, "Manfred AI", menu)

    main_loop_stop_event.clear()
    main_loop_thread = Thread(target=main_loop_logic, daemon=True)
    main_loop_thread.start()
    print("Main-Loop-Thread gestartet.")

    tray_icon.run_detached()
    print("Manfred AI Tray-Anwendung gestartet (detached). Rechtsklick auf das Icon für Optionen.")

    try:
        overlay.mainloop()
    except KeyboardInterrupt:
        print("KeyboardInterrupt empfangen, beende Anwendung...")
        on_exit_clicked(tray_icon, None)

    print("Tkinter mainloop beendet.")

    if main_loop_thread and main_loop_thread.is_alive():
        print("Warte auf Main-Loop-Thread (nach Tkinter exit)...")
        main_loop_thread.join(timeout=5)
        if main_loop_thread.is_alive():
            print("Main-Loop-Thread konnte nicht sauber beendet werden.")

    pygame.mixer.quit()
    print("Pygame Mixer beendet.")
    print("Anwendung wird vollständig beendet.")
