import asyncio
import os
import re
import speech_recognition as sr
import playsound
import webbrowser
import tkinter as tk
from tkinter import messagebox
from threading import Thread, Event # Event wird hier benötigt
from edge_tts import Communicate
from google import genai as gai
from google.genai import types
import numpy as np # Wird nicht mehr direkt in main.py benötigt, aber schadet nicht
import time
import pygame
import sys
from pystray import MenuItem as item, Icon as icon
from PIL import Image, ImageDraw

# Import from settings.py
try:
    from settings import (
        load_settings as app_load_settings,
        save_settings as app_save_settings,
        ModernSettingsApp,
        default_settings as app_default_settings
    )
except ImportError:
    messagebox.showerror("Fehler",
                         "settings.py konnte nicht gefunden oder importiert werden. Stellen Sie sicher, dass die Datei im selben Verzeichnis liegt.")
    sys.exit(1)

# Import from overlay.py
try:
    from overlay import ModernOverlay # <<< NEUER IMPORT
except ImportError:
    messagebox.showerror("Fehler",
                         "overlay.py konnte nicht gefunden oder importiert werden. Stellen Sie sicher, dass die Datei im selben Verzeichnis liegt.")
    sys.exit(1)


pygame.mixer.init()

# --- Konfigurationsmanagement (jetzt über settings.py) ---
current_app_settings = app_load_settings()

CodeWord = ""
StopWords = []
MAX_HISTORY = 0
API_KEY = ""
OPEN_LINKS_AUTOMATICALLY = True

client = None
chat = None
chat_config = None


def update_globals_from_settings(loaded_settings, initial_load=False):
    global CodeWord, StopWords, MAX_HISTORY, API_KEY, current_app_settings
    global client, chat, chat_config, OPEN_LINKS_AUTOMATICALLY

    old_api_key = current_app_settings.get("api_key") if not initial_load else None
    old_chat_length = current_app_settings.get("chat_length") if not initial_load else None
    old_open_links = current_app_settings.get("open_links_automatically") if not initial_load else None

    current_app_settings = loaded_settings

    CodeWord = current_app_settings.get("activation_word", app_default_settings["activation_word"])
    StopWords = current_app_settings.get("stop_words", app_default_settings["stop_words"])
    MAX_HISTORY = current_app_settings.get("chat_length", app_default_settings["chat_length"])
    OPEN_LINKS_AUTOMATICALLY = current_app_settings.get(
        "open_links_automatically",
        app_default_settings.get("open_links_automatically", True)
    )

    env_api_key = os.getenv("GEMINI_API_KEY")
    settings_api_key = current_app_settings.get("api_key", app_default_settings["api_key"])
    API_KEY = env_api_key or settings_api_key

    if not API_KEY:
        print(
            "WARNUNG: API-Key nicht konfiguriert. Bitte in settings.json oder als GEMINI_API_KEY Umgebungsvariable setzen.")
        if not initial_load and overlay and overlay.winfo_exists():
            messagebox.showwarning("API Key Warnung",
                                   "API-Key ist nicht konfiguriert. Bitte in den Einstellungen festlegen.")

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

    api_key_changed = (old_api_key != API_KEY) and not env_api_key
    chat_length_changed = (old_chat_length != MAX_HISTORY)
    open_links_setting_changed = (old_open_links != OPEN_LINKS_AUTOMATICALLY) if not initial_load else False

    if initial_load or api_key_changed:
        if API_KEY:
            try:
                client = gai.Client(api_key=API_KEY)
                current_history = chat.get_history() if chat and api_key_changed else []
                chat = client.chats.create(model="gemini-2.0-flash", config=chat_config,
                                           history=current_history)
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
            client = None
            chat = None

    if not initial_load:
        if not api_key_changed and (chat_length_changed or open_links_setting_changed):
            changed_parts = []
            if chat_length_changed:
                changed_parts.append("Chat Länge")
            if open_links_setting_changed:
                changed_parts.append("Automatisches Öffnen von Links")

            if changed_parts:
                messagebox.showinfo("Einstellungen aktualisiert",
                                    f"{' und '.join(changed_parts)} wurde(n) aktualisiert. Die Änderungen sind jetzt aktiv.")
        elif not api_key_changed and not chat_length_changed and not open_links_setting_changed:
            messagebox.showinfo("Einstellungen aktualisiert",
                                "Einstellungen wurden erfolgreich aktualisiert und angewendet.")

update_globals_from_settings(current_app_settings, initial_load=True)

recognizer = sr.Recognizer()
mic = sr.Microphone()

with mic as source:
    recognizer.adjust_for_ambient_noise(source)

speech_stop_event = Event() # Wird hier definiert
main_loop_stop_event = Event()

overlay = None
main_loop_thread = None
tray_icon = None

# --- ModernOverlay Klasse wurde entfernt ---

def set_overlay_mode_safe(mode):
    if overlay:
        overlay.after(0, lambda: overlay.set_mode(mode))

# ... (Rest von speak_action, main_loop_logic, generate_mp3, trim_chat_history, Tray Icon Functions unverändert) ...
# ... (Stelle sicher, dass die Funktionen, die overlay verwenden, weiterhin korrekt sind) ...

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

        sound_thread.join(timeout=1.0)

        if os.path.exists(temp_audio_file):
            try:
                os.remove(temp_audio_file)
            except PermissionError:
                time.sleep(0.5)
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
    global chat, CodeWord, StopWords, client, OPEN_LINKS_AUTOMATICALLY

    if not client or not chat:
        print("AI Client nicht initialisiert. Überprüfe API Key in den Einstellungen.")

    pygame.mixer.music.load("sounds/start.mp3")
    pygame.mixer.music.play()
    listening_mode = False

    while not main_loop_stop_event.is_set():
        if not client or not chat:
            if not main_loop_stop_event.is_set():
                print("Warte auf AI Client Initialisierung (API Key prüfen)...")
            time.sleep(5)
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
            else:
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
                    command = text.strip()

            if not command:
                print("Kein verwertbarer Befehl.")
                continue

            print(f"Befehl erkannt: {command}")
            response = chat.send_message(command)
            print(f"Antwort: {response.text}")

            response_text_for_tts = response.text

            url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
            match = re.search(url_pattern, response.text)

            if match:
                url = match.group(0)
                if OPEN_LINKS_AUTOMATICALLY:
                    if not url.startswith("http"):
                        url = "https://" + url
                    print(f"Öffne Link aus Antwort (Einstellung): {url}")
                    webbrowser.open(url)
                    response_text_for_tts = re.sub(url_pattern, '', response.text).strip()
                    if not response_text_for_tts:
                        response_text_for_tts = "Link geöffnet."
                else:
                    print(f"Link gefunden, wird vorgelesen (nicht geöffnet gemäß Einstellung): {url}")

            if response_text_for_tts:
                asyncio.run(generate_mp3(response_text_for_tts))
                speak_action()
            else:
                if listening_mode and not main_loop_stop_event.is_set():
                    set_overlay_mode_safe('listening')

            chat = trim_chat_history(chat)

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

    for attempt in range(3):
        try:
            if os.path.exists("reply.mp3"):
                os.remove("reply.mp3")
            break
        except PermissionError:
            print(f"reply.mp3 ist noch in Benutzung, Versuch {attempt + 1}/3...")
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
        except Exception as save_err:
            print(f"Konnte MP3 auch als reply_new.mp3 nicht speichern: {save_err}")
            return

    try:
        await communicate.save("reply.mp3")
    except Exception as e:
        print(f"Fehler beim Speichern von reply.mp3: {e}")


def trim_chat_history(current_chat_session):
    global MAX_HISTORY, client, chat_config
    if not current_chat_session or not client:
        return current_chat_session

    try:
        history = current_chat_session.get_history()
        if len(history) > MAX_HISTORY * 2:
            trimmed_history = history[-(MAX_HISTORY * 2):]
            new_chat_session = client.chats.create(
                model="gemini-2.0-flash",
                config=chat_config,
                history=trimmed_history
            )
            print(f"Chat-Verlauf gekürzt. Alte Länge: {len(history)}, Neue Länge: {len(trimmed_history)}")
            return new_chat_session
    except Exception as e:
        print(f"Fehler beim Kürzen des Chat-Verlaufs: {e}")
    return current_chat_session


def create_image(width, height, color1, color2):
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image


def get_icon_image():
    icon_path = "icon.ico"
    if os.path.exists(icon_path):
        try:
            return Image.open(icon_path)
        except Exception as e:
            print(f"Konnte {icon_path} nicht laden: {e}. Benutze Standard-Icon.")
    icon_path_png = "icon.png"
    if os.path.exists(icon_path_png):
        try:
            return Image.open(icon_path_png)
        except Exception as e:
            print(f"Konnte auch icon.png nicht laden: {e}. Benutze generiertes Icon.")
    return create_image(64, 64, 'black', 'blue')


def on_settings_clicked(icon_instance, item_instance):
    global overlay

    active_settings_toplevel = None
    if overlay:
        for child_window in overlay.winfo_children():
            if isinstance(child_window, tk.Toplevel) and child_window.title() == "Bot Settings":
                active_settings_toplevel = child_window
                break

    if active_settings_toplevel and active_settings_toplevel.winfo_exists():
        active_settings_toplevel.lift()
        active_settings_toplevel.focus_force()
        return

    settings_top_level = tk.Toplevel(overlay)
    _settings_app_instance = ModernSettingsApp(settings_top_level)
    overlay.wait_window(settings_top_level)

    print("Einstellungsfenster geschlossen. Lade Konfiguration neu und wende an.")
    newly_loaded_settings = app_load_settings()
    update_globals_from_settings(newly_loaded_settings)


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
    if not API_KEY and not os.getenv("GEMINI_API_KEY"):
        messagebox.showwarning("API Key fehlt",
                               "Der Google AI API Key ist nicht in settings.json oder als Umgebungsvariable GEMINI_API_KEY konfiguriert. Die AI-Funktionalität ist eingeschränkt. Bitte in den Einstellungen konfigurieren.")

    # speech_stop_event ist bereits global definiert
    overlay = ModernOverlay(speech_stop_event) # <<< HIER WIRD DAS EVENT ÜBERGEBEN

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

    tray_thread = Thread(target=tray_icon.run, daemon=True)
    tray_thread.start()
    print("Manfred AI Tray-Anwendung gestartet. Rechtsklick auf das Icon für Optionen.")

    try:
        overlay.mainloop()
    except KeyboardInterrupt:
        print("KeyboardInterrupt empfangen, beende Anwendung...")
        on_exit_clicked(tray_icon, None) # type: ignore

    print("Tkinter mainloop beendet.")

    if main_loop_thread and main_loop_thread.is_alive():
        print("Warte auf Main-Loop-Thread (nach Tkinter exit)...")
        main_loop_thread.join(timeout=5)
        if main_loop_thread.is_alive():
            print("Main-Loop-Thread konnte nicht sauber beendet werden.")

    if tray_icon and hasattr(tray_icon, 'visible') and tray_icon.visible: # type: ignore
        tray_icon.stop() # type: ignore

    if tray_thread and tray_thread.is_alive():
        print("Warte auf Tray-Icon-Thread...")
        tray_thread.join(timeout=2)
        if tray_thread.is_alive():
            print("Tray-Icon-Thread konnte nicht sauber beendet werden.")

    pygame.mixer.quit()
    print("Pygame Mixer beendet.")
    print("Anwendung wird vollständig beendet.")
    sys.exit()