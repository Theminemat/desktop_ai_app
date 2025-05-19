import asyncio
import os
import re
import speech_recognition as sr
import playsound
import webbrowser
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from threading import Thread, Event
from edge_tts import Communicate
from google import genai as gai
from google.genai import types
import numpy as np
import time
import pygame
import sys
# import json # No longer needed for main.py's own config loading

# System Tray Imports
from pystray import MenuItem as item, Icon as icon
from PIL import Image, ImageDraw

# Import from settings.py
try:
    from settings import (
        load_settings as app_load_settings,
        save_settings as app_save_settings,  # Not directly used by main, but good to have if needed
        ModernSettingsApp,
        default_settings as app_default_settings
    )
except ImportError:
    messagebox.showerror("Fehler",
                         "settings.py konnte nicht gefunden oder importiert werden. Stellen Sie sicher, dass die Datei im selben Verzeichnis liegt.")
    sys.exit(1)

pygame.mixer.init()

# --- Konfigurationsmanagement (jetzt über settings.py) ---
# Lade Konfiguration beim Start
current_app_settings = app_load_settings()

# Globale Variablen, die aus den Einstellungen initialisiert werden
CodeWord = ""
StopWords = []
MAX_HISTORY = 0
API_KEY = ""

# Globale AI Objekte
client = None
chat = None
chat_config = None  # Wird in update_globals_from_settings initialisiert


def update_globals_from_settings(loaded_settings, initial_load=False):
    global CodeWord, StopWords, MAX_HISTORY, API_KEY, current_app_settings
    global client, chat, chat_config  # AI client/chat objects

    old_api_key = current_app_settings.get("api_key") if not initial_load else None
    old_chat_length = current_app_settings.get("chat_length") if not initial_load else None

    current_app_settings = loaded_settings  # Update the global settings dict

    CodeWord = current_app_settings.get("activation_word", app_default_settings["activation_word"])
    StopWords = current_app_settings.get("stop_words", app_default_settings["stop_words"])
    MAX_HISTORY = current_app_settings.get("chat_length", app_default_settings["chat_length"])

    # API Key: Environment variable takes precedence, then settings.json
    env_api_key = os.getenv("GEMINI_API_KEY")
    settings_api_key = current_app_settings.get("api_key", app_default_settings["api_key"])

    API_KEY = env_api_key or settings_api_key

    if not API_KEY:  # Default API key in settings.json is ""
        print(
            "WARNUNG: API-Key nicht konfiguriert. Bitte in settings.json oder als GEMINI_API_KEY Umgebungsvariable setzen.")
        if not initial_load and overlay and overlay.winfo_exists():  # Show warning if GUI is up
            messagebox.showwarning("API Key Warnung",
                                   "API-Key ist nicht konfiguriert. Bitte in den Einstellungen festlegen.")

    # Initialize chat_config (or re-initialize if needed, though it's static here)
    if chat_config is None:
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

    # Handle AI client and chat initialization/re-initialization
    api_key_changed = (old_api_key != API_KEY) and not env_api_key  # Only consider settings.json change for re-init
    chat_length_changed = (old_chat_length != MAX_HISTORY)

    if initial_load or api_key_changed:
        if API_KEY:
            try:
                client = gai.Client(api_key=API_KEY)
                # Preserve history if chat exists and API key changed
                current_history = chat.get_history() if chat and api_key_changed else []
                chat = client.chats.create(model="gemini-2.0-flash", config=chat_config, history=current_history)
                print("AI Client und Chat initialisiert/aktualisiert.")
                if api_key_changed and not initial_load:
                    messagebox.showinfo("Einstellungen aktualisiert",
                                        "API Key wurde aktualisiert. Der AI Client wurde neu initialisiert.")
            except Exception as e:
                print(f"Fehler bei der Initialisierung des Google AI Clients: {e}")
                client = None
                chat = None
                if overlay and overlay.winfo_exists():
                    messagebox.showerror("AI Client Fehler",
                                         f"Konnte AI Client nicht initialisieren: {e}\nBitte API Key in den Einstellungen prüfen.")
        else:
            client = None  # Ensure client is None if no API_KEY
            chat = None  # Ensure chat is None if no API_KEY

    if not initial_load and not api_key_changed and chat_length_changed:
        # Only chat length changed, no need to re-init client, just inform
        messagebox.showinfo("Einstellungen aktualisiert",
                            "Chat Länge wurde aktualisiert. Die Änderung wird beim nächsten Chat-Verlauf-Trimmen wirksam.")
    elif not initial_load and not api_key_changed and not chat_length_changed:
        # For other changes like activation word or stop words
        messagebox.showinfo("Einstellungen aktualisiert",
                            "Einstellungen wurden erfolgreich aktualisiert und angewendet.")


# Initial load of settings and globals
update_globals_from_settings(current_app_settings, initial_load=True)

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


# settings_window_instance = None # No longer needed as ModernSettingsApp manages its own instance lifecycle via Toplevel

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


# Removed SettingsWindow class from main.py as it's now handled by ModernSettingsApp from settings.py

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
                if os.name == 'nt':  # playsound stop command is Windows-specific
                    # Attempt to stop sound; this is often unreliable with playsound
                    # For more robust control, pygame.mixer or another library might be better for playback.
                    # This is a known limitation of playsound's blocking nature.
                    # We'll rely on the thread ending and file cleanup.
                    pass  # No direct stop command that works reliably cross-platform for playsound after start.
            except Exception as e:
                print(f"Konnte Sound nicht stoppen (normal bei Abbruch): {e}")

        sound_thread.join(timeout=1.0)  # Wait briefly for thread to finish

        if os.path.exists(temp_audio_file):
            try:
                os.remove(temp_audio_file)
            except PermissionError:  # File might still be locked
                time.sleep(0.5)  # Wait a bit more
                try:
                    os.remove(temp_audio_file)
                except Exception as e:
                    print(f"Konnte temp_audio_file nach Wartezeit nicht löschen: {e}")
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
    global chat, CodeWord, StopWords, client  # Ensure global AI objects are used

    if not client or not chat:
        print("AI Client nicht initialisiert. Überprüfe API Key in den Einstellungen.")
        # Optionally play a sound indicating an error or wait
        # For now, the loop will continue but AI interaction will fail.
        # A message box might be too intrusive for a background process.
        # This state should ideally be handled by update_globals_from_settings showing a warning.

    pygame.mixer.music.load("sounds/start.mp3")
    pygame.mixer.music.play()
    listening_mode = False

    while not main_loop_stop_event.is_set():
        if not client or not chat:  # Check periodically
            if not main_loop_stop_event.is_set():  # Avoid print spam on exit
                print("Warte auf AI Client Initialisierung (API Key prüfen)...")
            time.sleep(5)  # Wait before retrying or next check
            continue

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
                if CodeWord.lower() in text_lower:
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
            else:  # listening_mode is true
                is_stop_command = False
                for stop_word in StopWords:
                    if stop_word.lower() in text_lower:
                        is_stop_command = True
                        break
                if is_stop_command:
                    listening_mode = False
                    print("Modus deaktiviert (durch Stopword).")
                    set_overlay_mode_safe(None)
                    pygame.mixer.music.load("sounds/deaktivated.mp3")
                    pygame.mixer.music.play()
                    continue
                else:
                    command = text.strip()  # Use original casing for command to AI

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
                if not response_text_for_tts:  # If only URL was in response
                    response_text_for_tts = "Link geöffnet."

            if response_text_for_tts:
                asyncio.run(generate_mp3(response_text_for_tts))
                speak_action()
            else:  # No text to speak (e.g. only URL was present and removed)
                if listening_mode and not main_loop_stop_event.is_set():  # Stay in listening mode if active
                    set_overlay_mode_safe('listening')
                # else: # if not listening_mode, overlay will be set to None at loop start

            chat = trim_chat_history(chat)  # Use the global chat object

        except sr.UnknownValueError:
            if listening_mode:
                print("Nichts verstanden.")
        except sr.RequestError as e:
            print(f"Fehler bei der Spracherkennung: {e}")
            asyncio.run(generate_mp3("Problem mit der Spracherkennung."))
            speak_action()
        except types.StopCandidateException as e:
            print(f"Antwort von AI gestoppt: {e}")
            asyncio.run(generate_mp3("Meine Antwort wurde aufgrund von Sicherheitsrichtlinien blockiert."))
            speak_action()
        except Exception as e:
            print(f"Ein Fehler in der Hauptschleife: {e}")
            # Consider more specific error handling or logging
            # asyncio.run(generate_mp3("Ein interner Fehler ist aufgetreten."))
            # speak_action() # Avoid speaking for every generic error

        if main_loop_stop_event.is_set(): break

    print("Main loop beendet.")
    set_overlay_mode_safe(None)


async def generate_mp3(text):
    if not text.strip():
        text = "Okay."  # Default if empty
    # Sanitize text for TTS and filename
    text = re.sub(r'[<>:"/\\|?*]', '', text)  # Remove characters problematic for filenames/TTS
    text = text.replace('\n', ' ').replace('\r', '')  # Replace newlines
    if not text.strip():  # If sanitizing made it empty
        text = "Verstanden."

    communicate = Communicate(text=text, voice="de-DE-ConradNeural")  # Using a specific German voice

    # Attempt to remove old reply.mp3 with retries
    for attempt in range(3):
        try:
            if os.path.exists("reply.mp3"):
                os.remove("reply.mp3")
            break  # Success
        except PermissionError:
            print(f"reply.mp3 ist noch in Benutzung, Versuch {attempt + 1}/3...")
            await asyncio.sleep(0.2)  # Wait a bit before retrying
        except FileNotFoundError:
            break  # File already gone
        except Exception as e:
            print(f"Konnte reply.mp3 nicht löschen: {e}")
            break  # Other error, stop trying
    else:  # If all attempts failed
        print("Konnte reply.mp3 nach mehreren Versuchen nicht löschen. Speichere als reply_new.mp3")
        try:
            await communicate.save("reply_new.mp3")  # Save as a new file
            # Potentially rename reply_new.mp3 to reply.mp3 here if speak_action expects "reply.mp3"
            # For now, speak_action is hardcoded to use "reply.mp3" after renaming.
            # This path means the original "reply.mp3" is stuck.
            # The speak_action needs to be aware of this alternative filename or this needs to resolve.
            # For simplicity, if reply.mp3 cannot be deleted, we might have an issue for speak_action.
            # The current speak_action renames reply.mp3 to reply_temp.mp3.
            # So, if reply.mp3 is stuck, generate_mp3 should try to overwrite it or fail gracefully.
            # Let's assume communicate.save will overwrite if possible.
        except Exception as save_err:
            print(f"Konnte MP3 auch als reply_new.mp3 nicht speichern: {save_err}")
            return  # Cannot save audio

    try:
        await communicate.save("reply.mp3")  # Attempt to save/overwrite reply.mp3
    except Exception as e:
        print(f"Fehler beim Speichern von reply.mp3: {e}")


def trim_chat_history(current_chat_session):
    global MAX_HISTORY, client, chat_config  # Use global MAX_HISTORY
    if not current_chat_session or not client:  # Ensure chat and client exist
        return current_chat_session

    try:
        history = current_chat_session.get_history()
        # MAX_HISTORY refers to pairs of user/model messages. Each pair is 2 entries in history.
        if len(history) > MAX_HISTORY * 2:
            trimmed_history = history[-(MAX_HISTORY * 2):]
            # Create a new chat session with the trimmed history
            new_chat_session = client.chats.create(
                model="gemini-2.0-flash",  # Ensure this matches your desired model
                config=chat_config,  # Use the global chat_config
                history=trimmed_history
            )
            print(f"Chat-Verlauf gekürzt. Alte Länge: {len(history)}, Neue Länge: {len(trimmed_history)}")
            return new_chat_session
    except Exception as e:
        print(f"Fehler beim Kürzen des Chat-Verlaufs: {e}")
    return current_chat_session


# --- Tray Icon Functions ---
def create_image(width, height, color1, color2):  # Fallback icon
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image


def get_icon_image():
    icon_path = "icon.png"  # Ensure this icon exists or adjust path
    if os.path.exists(icon_path):
        try:
            return Image.open(icon_path)
        except Exception as e:
            print(f"Konnte icon.png nicht laden: {e}. Benutze Standard-Icon.")
    return create_image(64, 64, 'black', 'blue')  # Fallback


def on_settings_clicked(icon_instance, item_instance):
    global overlay  # current_app_settings is already global and updated by update_globals_from_settings

    # Check if a settings window (Toplevel with specific title) already exists
    # to prevent opening multiple instances.
    active_settings_toplevel = None
    if overlay:  # overlay is the ModernOverlay instance (our main tk.Tk root)
        for child_window in overlay.winfo_children():
            if isinstance(child_window, tk.Toplevel) and child_window.title() == "Bot Settings":
                active_settings_toplevel = child_window
                break

    if active_settings_toplevel and active_settings_toplevel.winfo_exists():
        active_settings_toplevel.lift()
        active_settings_toplevel.focus_force()
        return

    # Create a new Toplevel window for the settings UI
    # This Toplevel will be the root for ModernSettingsApp
    settings_top_level = tk.Toplevel(overlay)
    # ModernSettingsApp will set its own title "Bot Settings"

    # Instantiate ModernSettingsApp from settings.py, passing the Toplevel
    # The ModernSettingsApp instance itself is not the window; its 'self.root' is settings_top_level.
    _settings_app_instance = ModernSettingsApp(settings_top_level)

    settings_top_level.grab_set()  # Make the settings window modal
    overlay.wait_window(settings_top_level)  # Pause execution here until settings_top_level is closed

    # After settings window is closed (destroyed), reload settings from file and update globals
    print("Einstellungsfenster geschlossen. Lade Konfiguration neu und wende an.")
    newly_loaded_settings = app_load_settings()  # Reload from settings.json
    update_globals_from_settings(newly_loaded_settings)  # Apply them


def on_exit_clicked(icon_instance, item_instance):
    print("Beende Anwendung...")
    global overlay, main_loop_thread, tray_icon

    main_loop_stop_event.set()  # Signal main_loop_logic to stop
    speech_stop_event.set()  # Signal speak_action to stop any ongoing speech

    if tray_icon:
        tray_icon.stop()
    print("Tray Icon gestoppt-Anfrage gesendet.")

    if overlay:
        print("Sende quit-Anfrage an Overlay (Tkinter mainloop)...")
        overlay.after(0, overlay.quit)  # Schedule Tkinter mainloop to quit


if __name__ == "__main__":
    if not API_KEY and not os.getenv("GEMINI_API_KEY"):  # Check after initial load
        messagebox.showwarning("API Key fehlt",
                               "Der Google AI API Key ist nicht in settings.json oder als Umgebungsvariable GEMINI_API_KEY konfiguriert. Die AI-Funktionalität ist eingeschränkt. Bitte in den Einstellungen konfigurieren.")

    overlay = ModernOverlay()

    tray_icon_image = get_icon_image()
    menu = (
        item('Einstellungen', on_settings_clicked),
        item('Beenden', on_exit_clicked),
    )
    tray_icon = icon("ManfredAI", tray_icon_image, "Manfred AI", menu)

    main_loop_stop_event.clear()
    main_loop_thread = Thread(target=main_loop_logic, daemon=True)
    main_loop_thread.start()
    print("Main-Loop-Thread gestartet.")

    # Run tray icon in a non-blocking way if possible, or ensure it doesn't block main Tkinter loop
    # pystray's icon.run() is blocking. icon.run_detached() or running in a separate thread is needed.
    tray_thread = Thread(target=tray_icon.run, daemon=True)
    tray_thread.start()
    # tray_icon.run_detached() # Alternative if available and preferred
    print("Manfred AI Tray-Anwendung gestartet. Rechtsklick auf das Icon für Optionen.")

    try:
        overlay.mainloop()  # Start Tkinter main loop for the overlay
    except KeyboardInterrupt:
        print("KeyboardInterrupt empfangen, beende Anwendung...")
        on_exit_clicked(tray_icon, None)  # Graceful shutdown

    print("Tkinter mainloop beendet.")

    # Ensure main_loop_thread finishes
    if main_loop_thread and main_loop_thread.is_alive():
        print("Warte auf Main-Loop-Thread (nach Tkinter exit)...")
        main_loop_thread.join(timeout=5)  # Wait for up to 5 seconds
        if main_loop_thread.is_alive():
            print("Main-Loop-Thread konnte nicht sauber beendet werden.")

    # Ensure tray icon thread also finishes if it was started with tray_icon.run()
    if tray_icon and tray_icon.visible:  # Check if tray icon is still running
        tray_icon.stop()

    if tray_thread and tray_thread.is_alive():
        print("Warte auf Tray-Icon-Thread...")
        tray_thread.join(timeout=2)
        if tray_thread.is_alive():
            print("Tray-Icon-Thread konnte nicht sauber beendet werden.")

    pygame.mixer.quit()
    print("Pygame Mixer beendet.")
    print("Anwendung wird vollständig beendet.")
    sys.exit()  # Ensure application exits cleanly