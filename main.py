
import asyncio
import os
import re
import webbrowser
import tkinter as tk
from tkinter import messagebox
from threading import Thread, Event
from edge_tts import Communicate
from google import genai as gai
from google.genai import types
from google.genai.errors import ClientError
from google.generativeai.types import StopCandidateException
import time
import pygame
import sys
from pystray import MenuItem as item, Icon as icon
from PIL import Image, ImageDraw
import speech_recognition as sr
import atexit

try:
    from settings import (
        load_settings as app_load_settings,
        ModernSettingsApp,
        default_settings as app_default_settings,
        DEFAULT_SYSTEM_PROMPT_NAME,
        DEFAULT_SYSTEM_PROMPT_TEXT,
        LanguageManager,
        TTS_VOICES_STRUCTURED # Added import
    )
    from agent_builder import (
        load_system_prompts as agent_load_system_prompts,
        get_full_system_prompt as agent_get_full_system_prompt,

        AGENT_SETTING_ACTIVATION_WORD,
        AGENT_SETTING_STOP_WORDS,
        AGENT_SETTING_CHAT_LENGTH,
        AGENT_SETTING_TTS_VOICE,
        AGENT_SETTING_OPEN_LINKS
    )
except ImportError as e:
    if 'settings' in str(e).lower():
        messagebox.showerror("Error", "settings.py could not be found or imported.")
    elif 'agent_builder' in str(e).lower():
        messagebox.showerror("Error", "agent_builder.py could not be found or imported.")
    else:
        messagebox.showerror("Error", f"A critical file could not be imported: {e}")
    sys.exit(1)

try:
    from overlay import ModernOverlay
except ImportError:
    messagebox.showerror("Error", "overlay.py could not be found or imported.")
    sys.exit(1)


try:
    from console import init_output_redirection, show_console_window as show_console_window_external, get_console_window_instance
    init_output_redirection()
except ImportError as e:
    messagebox.showerror("Error", f"console.py could not be found or imported: {e}")
    def init_output_redirection(): print("CRITICAL: Console redirection FAILED.")
    def show_console_window_external(overlay, lm): messagebox.showerror("Error", "Console module failed to load.")
    def get_console_window_instance(): return None
    init_output_redirection()



try:
    pygame.mixer.init()
except pygame.error as e:
    print(f"Initial Pygame mixer init failed: {e}. Audio output may not work.") # This print will be captured


current_app_settings = app_load_settings() # This may print, will be captured
lm_main = LanguageManager(current_app_settings.get("ui_language", app_default_settings["ui_language"])) # This may print
all_system_prompts = agent_load_system_prompts(DEFAULT_SYSTEM_PROMPT_NAME, DEFAULT_SYSTEM_PROMPT_TEXT)


_lock_file_descriptor = None
_lock_file_path = None


CodeWord = ""
StopWords = []
MAX_HISTORY = 0
API_KEY = ""
OPEN_LINKS_AUTOMATICALLY = True
ACTIVE_SYSTEM_PROMPT_NAME = DEFAULT_SYSTEM_PROMPT_NAME
TTS_VOICE = app_default_settings["tts_voice"] # Wird in update_globals_from_settings aktualisiert
STT_LANGUAGE = "en-US" # Wird in update_globals_from_settings aktualisiert
SELECTED_MIC_NAME = app_default_settings["selected_microphone"]
SELECTED_SPEAKER_NAME = app_default_settings["selected_speaker"]

client = None
chat = None
chat_config = None
recognizer = sr.Recognizer()
mic = None

speech_stop_event = Event()
main_loop_stop_event = Event()
overlay = None
main_loop_thread = None
tray_icon = None



def resource_path(relative_path):
    """ Pfad zu Datei relativ zum Skript oder zur gepackten EXE """
    if hasattr(sys, '_MEIPASS'):

        return os.path.join(sys._MEIPASS, relative_path)


    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base_path, relative_path)

def get_app_data_path(filename):

    if hasattr(sys, '_MEIPASS'):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(application_path, filename)


def cleanup_lock_file():
    global _lock_file_descriptor, _lock_file_path
    if _lock_file_descriptor is not None:
        try:
            os.close(_lock_file_descriptor)
            print(f"Lock file descriptor {_lock_file_descriptor} closed.")
        except OSError as e:
            print(f"Error closing lock file descriptor: {e}")
        _lock_file_descriptor = None

    if _lock_file_path and os.path.exists(_lock_file_path):
        try:
            os.remove(_lock_file_path)
            print(f"Lock file '{_lock_file_path}' removed.")
        except OSError as e:
            print(f"Error removing lock file '{_lock_file_path}': {e}")


def show_error_dialog(title_key: str, message_key: str, parent=None, **format_args):
    global lm_main, overlay

    title = lm_main.get_string(title_key, default_text="Error")
    message_text = lm_main.get_string(message_key, default_text="An error occurred: {e}", **format_args)

    if parent is None:
        if overlay and overlay.winfo_exists():
            parent = overlay
        else:

            console_instance = get_console_window_instance()
            if console_instance and console_instance.winfo_exists():
                parent = console_instance
            # If still no parent, messagebox will use default root or be standalone

    messagebox.showerror(title, message_text, parent=parent)


def initialize_audio_devices():
    global mic, SELECTED_MIC_NAME, SELECTED_SPEAKER_NAME, recognizer, lm_main
    print("Initializing audio devices...")

    try:
        if pygame.mixer.get_init():
            pygame.mixer.quit()
            print("Pygame mixer quit for re-initialization.")

        if SELECTED_SPEAKER_NAME == "System Default":
            print("Initializing Pygame mixer with system default speaker.")
            pygame.mixer.init()
        else:
            print(f"Initializing Pygame mixer with speaker: {SELECTED_SPEAKER_NAME}")
            pygame.mixer.init(devicename=SELECTED_SPEAKER_NAME)

        print("Pygame mixer initialized successfully.")

    except Exception as e:
        print(f"Error initializing Pygame mixer with '{SELECTED_SPEAKER_NAME}': {e}. Falling back to default.")
        try:
            if pygame.mixer.get_init(): pygame.mixer.quit()
            pygame.mixer.init()
            print("Pygame mixer initialized with system default (fallback).")
        except Exception as e_fallback:
            print(f"Critical error: Pygame mixer could not be initialized even with default: {e_fallback}")
            show_error_dialog("error_title",
                              "pygame_mixer_init_failed_error",
                              e=str(e_fallback))

    # Microphone (SpeechRecognition)
    mic_index = None
    if SELECTED_MIC_NAME != "System Default":
        try:
            mic_names = sr.Microphone.list_microphone_names()
            if SELECTED_MIC_NAME in mic_names:
                mic_index = mic_names.index(SELECTED_MIC_NAME)
                print(f"Using microphone: {SELECTED_MIC_NAME} (Index: {mic_index})")
            else:
                print(f"Microphone '{SELECTED_MIC_NAME}' not found in list. Using system default.")
                SELECTED_MIC_NAME = "System Default" # Fallback
        except Exception as e:
            print(f"Error listing or finding microphones: {e}. Using system default.")
            SELECTED_MIC_NAME = "System Default" # Fallback


    if SELECTED_MIC_NAME == "System Default":
        print("Using system default microphone.")
        mic_index = None 

    try:
        mic = sr.Microphone(device_index=mic_index)
        with mic as source:
            print("Adjusting for ambient noise... ")
            recognizer.adjust_for_ambient_noise(source, duration=1.0)
            print("Ambient noise adjustment complete.")
    except Exception as e:
        print(f"Error initializing microphone or adjusting for ambient noise: {e}")
        show_error_dialog("error_title",
                          "microphone_init_failed_error",
                          e=str(e))
        try: # Fallback to truly default microphone
            mic = sr.Microphone() # No device_index
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("Successfully initialized with truly default microphone after error.")
        except Exception as e_fallback_mic:
            print(f"Fallback microphone initialization also failed: {e_fallback_mic}")
            mic = None


def update_globals_from_settings(loaded_settings, initial_load=False):
    global CodeWord, StopWords, MAX_HISTORY, API_KEY, current_app_settings, all_system_prompts
    global client, chat, chat_config, OPEN_LINKS_AUTOMATICALLY, ACTIVE_SYSTEM_PROMPT_NAME, TTS_VOICE
    global lm_main, STT_LANGUAGE, SELECTED_MIC_NAME, SELECTED_SPEAKER_NAME


    old_api_key = current_app_settings.get("api_key") if not initial_load else None
    old_chat_length_global = current_app_settings.get("chat_length") if not initial_load else None # Global setting
    old_open_links_global = current_app_settings.get("open_links_automatically", app_default_settings[
        "open_links_automatically"]) if not initial_load else False
    old_active_prompt_name_global = current_app_settings.get("active_system_prompt_name") if not initial_load else None
    old_ui_language = current_app_settings.get("ui_language") if not initial_load else None
    old_effective_tts_voice = TTS_VOICE if not initial_load else None
    old_mic_name = current_app_settings.get("selected_microphone") if not initial_load else None
    old_speaker_name = current_app_settings.get("selected_speaker") if not initial_load else None


    current_app_settings = loaded_settings
    all_system_prompts = agent_load_system_prompts(DEFAULT_SYSTEM_PROMPT_NAME, DEFAULT_SYSTEM_PROMPT_TEXT)

    new_ui_language = current_app_settings.get("ui_language", app_default_settings["ui_language"])
    if initial_load or old_ui_language != new_ui_language:
        lm_main.set_language(new_ui_language)


    ACTIVE_SYSTEM_PROMPT_NAME = current_app_settings.get("active_system_prompt_name",
                                                         app_default_settings["active_system_prompt_name"])
    if ACTIVE_SYSTEM_PROMPT_NAME not in all_system_prompts:
        ACTIVE_SYSTEM_PROMPT_NAME = DEFAULT_SYSTEM_PROMPT_NAME
        print(
            f"Warning: Active system prompt '{current_app_settings.get('active_system_prompt_name')}' not found. Falling back to default.")


    active_agent_config = all_system_prompts.get(ACTIVE_SYSTEM_PROMPT_NAME, {})
    if not isinstance(active_agent_config, dict): # Should not happen with new loader
        active_agent_config = {} # Provide an empty dict to prevent errors on .get()


    agent_activation_word_override = active_agent_config.get(AGENT_SETTING_ACTIVATION_WORD)
    CodeWord = agent_activation_word_override if agent_activation_word_override else \
               current_app_settings.get("activation_word", app_default_settings["activation_word"])

    agent_stop_words_override = active_agent_config.get(AGENT_SETTING_STOP_WORDS)
    StopWords = agent_stop_words_override if agent_stop_words_override is not None else \
                current_app_settings.get("stop_words", app_default_settings["stop_words"])

    agent_chat_length_override = active_agent_config.get(AGENT_SETTING_CHAT_LENGTH)
    MAX_HISTORY = agent_chat_length_override if agent_chat_length_override is not None else \
                  current_app_settings.get("chat_length", app_default_settings["chat_length"])

    agent_open_links_override = active_agent_config.get(AGENT_SETTING_OPEN_LINKS)
    OPEN_LINKS_AUTOMATICALLY = agent_open_links_override if agent_open_links_override is not None else \
                               current_app_settings.get("open_links_automatically",
                                                        app_default_settings["open_links_automatically"])


    agent_tts_voice_override = active_agent_config.get(AGENT_SETTING_TTS_VOICE)
    global_tts_voice_setting = current_app_settings.get("tts_voice", app_default_settings["tts_voice"])
    TTS_VOICE = agent_tts_voice_override if agent_tts_voice_override else global_tts_voice_setting



    SELECTED_MIC_NAME = current_app_settings.get("selected_microphone", app_default_settings["selected_microphone"])
    SELECTED_SPEAKER_NAME = current_app_settings.get("selected_speaker", app_default_settings["selected_speaker"])



    tts_voice_effectively_changed = initial_load or old_effective_tts_voice != TTS_VOICE

    if tts_voice_effectively_changed:
        try:
            stt_lang_parts = TTS_VOICE.split('-', 2)
            if len(stt_lang_parts) >= 2:
                STT_LANGUAGE = f"{stt_lang_parts[0]}-{stt_lang_parts[1]}"
                print(f"STT language set to: {STT_LANGUAGE} (derived from effective TTS voice: {TTS_VOICE})")
            else:
                STT_LANGUAGE = "en-US"
                print(f"Warning: Could not parse effective TTS voice '{TTS_VOICE}'. Defaulting STT to en-US.")
        except Exception as e:
            STT_LANGUAGE = "en-US"
            print(f"Error deriving STT language from effective TTS voice: {e}. Defaulting to en-US.")


    env_api_key = os.getenv("GEMINI_API_KEY")
    settings_api_key = current_app_settings.get("api_key", app_default_settings["api_key"])
    API_KEY = env_api_key or settings_api_key

    if not API_KEY or API_KEY == app_default_settings["api_key"]:
        print("WARNING: API key not configured or is placeholder.")
        if initial_load or (old_api_key and old_api_key != app_default_settings["api_key"]):
            if overlay and overlay.winfo_exists():
                messagebox.showwarning(
                    lm_main.get_string("api_key_not_configured_warning_title"),
                    lm_main.get_string("api_key_not_configured_warning_message"),
                    parent=overlay
                )


    global_activation_word_default = current_app_settings.get("activation_word",
                                                              app_default_settings["activation_word"])
    global_open_links_default = current_app_settings.get("open_links_automatically",
                                                         app_default_settings["open_links_automatically"])

    current_system_instruction = agent_get_full_system_prompt(
        ACTIVE_SYSTEM_PROMPT_NAME,
        all_system_prompts,
        global_activation_word_default,
        global_open_links_default,
        DEFAULT_SYSTEM_PROMPT_TEXT,
        TTS_VOICE,  # Pass the effective TTS voice ID for the current agent
        TTS_VOICES_STRUCTURED # Pass the main structure from settings.py
    )
    old_system_instruction_from_config = chat_config.system_instruction if chat_config else None

    if chat_config is None:
        chat_config = types.GenerateContentConfig(system_instruction=current_system_instruction)
    else:
        chat_config.system_instruction = current_system_instruction

    api_key_changed = (old_api_key != API_KEY) and not env_api_key
    system_prompt_changed = (old_active_prompt_name_global != ACTIVE_SYSTEM_PROMPT_NAME) or \
                            (old_system_instruction_from_config != current_system_instruction)


    mic_changed = initial_load or old_mic_name != SELECTED_MIC_NAME
    speaker_changed = initial_load or old_speaker_name != SELECTED_SPEAKER_NAME

    if mic_changed or speaker_changed:
        initialize_audio_devices()
        if not initial_load:
            changed_audio_parts = []
            if mic_changed: changed_audio_parts.append(
                lm_main.get_string("microphone_label", default_text="Microphone").replace(":", ""))
            if speaker_changed: changed_audio_parts.append(
                lm_main.get_string("speaker_label", default_text="Speaker").replace(":", ""))
            if overlay and overlay.winfo_exists():
                messagebox.showinfo(
                    lm_main.get_string("settings_updated_title"),
                    lm_main.get_string("audio_devices_updated_message",
                                       default_text="Audio device settings updated: {devices}. Speech input/output reinitialized.",
                                       devices=", ".join(changed_audio_parts)),
                    parent=overlay
                )

    if initial_load or api_key_changed or system_prompt_changed:
        if API_KEY and API_KEY != app_default_settings["api_key"]:
            try:
                if client is None or api_key_changed: client = gai.Client(api_key=API_KEY)
                current_history = []
                if chat and not api_key_changed and system_prompt_changed:
                    try:
                        current_history = chat.get_history(); print("Preserving chat history.")
                    except Exception as e:
                        print(f"Could not preserve chat history: {e}.")
                chat = client.chats.create(model="gemini-1.5-flash", config=chat_config, history=current_history)
                print("AI Client and Chat initialized/updated.")
                if not initial_load:
                    msg_key = "settings_updated_reinit_api_key" if api_key_changed else "settings_updated_reinit_system_prompt"
                    if overlay and overlay.winfo_exists():
                        messagebox.showinfo(lm_main.get_string("settings_updated_title"), lm_main.get_string(msg_key),
                                            parent=overlay)
            except Exception as e:
                print(f"Error initializing Google AI Client: {e}");
                client = None;
                chat = None
                if overlay and overlay.winfo_exists():
                    show_error_dialog("ai_client_error_title",
                                      "ai_client_error_message",
                                      parent=overlay,
                                      e=str(e))
        else:
            client = None; chat = None

    if not initial_load and not (api_key_changed or system_prompt_changed or mic_changed or speaker_changed):
        changed_parts = []
        if old_chat_length_global != MAX_HISTORY:
             changed_parts.append(lm_main.get_string("chat_length_label").replace(":", ""))
        if old_open_links_global != OPEN_LINKS_AUTOMATICALLY:
             changed_parts.append(lm_main.get_string("open_links_label").replace(":", ""))

        if tts_voice_effectively_changed:
            changed_parts.append(lm_main.get_string("tts_voice_label").replace(":", ""))

        if changed_parts:
            if overlay and overlay.winfo_exists():
                messagebox.showinfo(lm_main.get_string("settings_updated_title"),
                                    lm_main.get_string("settings_updated_applied_changes",
                                                       changed_parts=", ".join(changed_parts)),
                                    parent=overlay)




def set_overlay_mode_safe(mode):
    if overlay and overlay.winfo_exists():
        overlay.after(0, lambda: overlay.set_mode(mode))


def speak_action():
    set_overlay_mode_safe('speaking')
    try:
        if not pygame.mixer.get_init():
            print("Pygame mixer not initialized. Cannot play audio.")
            set_overlay_mode_safe('listening' if not main_loop_stop_event.is_set() else None)
            return

        temp_audio_file = get_app_data_path("tts_playback_temp.mp3") # Use helper
        source_audio_file = get_app_data_path("reply.mp3") # Use helper

        if not os.path.exists(source_audio_file):
            print(f"No {source_audio_file} found for playback.")
            set_overlay_mode_safe('listening' if not main_loop_stop_event.is_set() else None)
            return

        if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
        pygame.mixer.music.unload();
        time.sleep(0.05) # Give a moment for unload

        if os.path.exists(temp_audio_file):
            try:
                os.remove(temp_audio_file)
            except Exception as e:
                print(f"Could not remove old temp file {temp_audio_file}: {e}")
        try:
            os.rename(source_audio_file, temp_audio_file)
        except Exception as e:
            print(f"Could not rename {source_audio_file} to {temp_audio_file}: {e}. Skipping playback.")
            set_overlay_mode_safe('listening' if not main_loop_stop_event.is_set() else None)
            return

        pygame.mixer.music.load(temp_audio_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy() and not speech_stop_event.is_set() and not main_loop_stop_event.is_set():
            time.sleep(0.05)
        if pygame.mixer.music.get_busy(): pygame.mixer.music.stop() # Stop if event was set
        pygame.mixer.music.unload(); time.sleep(0.1) # Unload and pause
        if os.path.exists(temp_audio_file): # Remove after unload
            try: os.remove(temp_audio_file)
            except Exception as e_rem: print(f"Error removing temp playback file {temp_audio_file}: {e_rem}")
    except pygame.error as e:
        print(f"Pygame error during playback: {e}")
    except Exception as e:
        print(f"Error during speak_action: {e}")
    finally:
        speech_stop_event.clear()
        set_overlay_mode_safe('listening' if not main_loop_stop_event.is_set() else None)


def main_loop_logic():
    global chat, CodeWord, StopWords, client, OPEN_LINKS_AUTOMATICALLY, STT_LANGUAGE, lm_main, mic, recognizer

    if not client or not chat:
        print("AI Client not initialized. Check API Key/System Prompt in settings.")

    if not mic:
        print("Microphone not initialized. Speech input will not work.")

    try:
        if client and chat and pygame.mixer.get_init(): # Check mixer init
            while pygame.mixer.music.get_busy(): time.sleep(0.05)
    except pygame.error as e:
        print(f"Could not play start sound: {e}")

    listening_mode = False
    while not main_loop_stop_event.is_set():
        if not client or not chat:
            if not main_loop_stop_event.is_set(): print("AI Client not ready. Waiting...")
            set_overlay_mode_safe(None); time.sleep(5); continue

        if not mic: # Check if mic is available
            if not main_loop_stop_event.is_set(): print("Microphone not available. Waiting...")
            set_overlay_mode_safe(None); time.sleep(5); continue

        set_overlay_mode_safe('listening' if listening_mode else None)
        if client and chat: # Redundant check, but safe
            print("Waiting for voice input..." if not listening_mode else f"Listening (lang: {STT_LANGUAGE})...")

        try:
            with mic as source: # Use the global mic object
                audio = recognizer.listen(source, timeout=2, phrase_time_limit=7)
        except sr.WaitTimeoutError:
            continue
        except AttributeError: # This can happen if mic is None
            print("Microphone object is None. Cannot listen.")
            time.sleep(2); continue
        except Exception as e: # Other mic errors (e.g. OSError if device disconnected)
            print(f"Error with microphone: {e}"); time.sleep(1); continue
        if main_loop_stop_event.is_set(): break

        try:
            text = recognizer.recognize_google(audio, language=STT_LANGUAGE) # STT_LANGUAGE is now agent-aware
            print(f"Recognized (lang: {STT_LANGUAGE}): {text}")
            text_lower = text.lower()

            if not listening_mode:
                if CodeWord.lower() in text_lower: # CodeWord is now agent-aware
                    listening_mode = True
                    command = text_lower.split(CodeWord.lower(), 1)[-1].strip()
                    if not command: # Only activation word spoken
                        print("Activated. Waiting for command...")
                        if pygame.mixer.get_init():
                            try: pygame.mixer.music.load(resource_path("sounds/listening.mp3")); pygame.mixer.music.play()
                            except pygame.error as e: print(f"Sound error: {e}")
                        asyncio.run(generate_mp3(lm_main.get_string("activation_confirmation_speech")))
                        speak_action(); continue
                else: # Not activation word
                    continue
            else: # Already listening_mode
                is_stop_command = any(re.search(r"\b" + re.escape(sw.lower()) + r"\b", text_lower) for sw in StopWords)
                if is_stop_command:
                    listening_mode = False; print("Mode deactivated (by stopword).")
                    set_overlay_mode_safe(None)
                    if pygame.mixer.get_init():
                        try: pygame.mixer.music.load(resource_path("sounds/deactivated.mp3")); pygame.mixer.music.play()
                        except pygame.error as e: print(f"Sound error: {e}")
                    continue
                else: # It's a command
                    command = text.strip()

            if not command: print("No usable command."); continue
            print(f"Command recognized: {command}")

            response = chat.send_message(command)
            print(f"Response: {response.text}")
            response_text_for_tts = response.text

            url_pattern = r'(https?://[^\s]+|www\.[^\s]+)' # Basic URL regex
            match = re.search(url_pattern, response.text)
            if match:
                url = match.group(0)
                if OPEN_LINKS_AUTOMATICALLY:
                    if not url.startswith("http"): url = "https://" + url # Ensure scheme for webbrowser
                    print(f"Opening link: {url}")
                    try:
                        webbrowser.open(url)
                        response_text_for_tts = re.sub(url_pattern, '', response.text).strip() # Remove URL for TTS
                        if not response_text_for_tts: response_text_for_tts = lm_main.get_string("link_opened_speech")
                    except Exception as e:
                        print(f"Failed to open link {url}: {e}")
                        response_text_for_tts = lm_main.get_string("failed_to_open_link_speech", default_text="Failed to open link.")
                        asyncio.run(generate_mp3(response_text_for_tts)); speak_action(); continue
                else: # Not opening automatically
                    print(f"Link found (not opened): {url}")

            if response_text_for_tts:

                await_task = asyncio.run(generate_mp3(response_text_for_tts))
                speak_action()
            elif listening_mode and not main_loop_stop_event.is_set():
                set_overlay_mode_safe('listening')
            chat = trim_chat_history(chat)

        except sr.UnknownValueError:
            if listening_mode: print("Could not understand.")
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            asyncio.run(generate_mp3(lm_main.get_string("speech_recognition_problem_speech"))); speak_action()
        except ClientError as e:
            print(f"Google AI ClientError: {e}")
            is_api_key_invalid = False
            if hasattr(e, 'response_json') and e.response_json and 'error' in e.response_json and 'details' in e.response_json['error']:
                for detail in e.response_json['error']['details']:
                    if detail.get('reason') == 'API_KEY_INVALID': is_api_key_invalid = True; break
            if is_api_key_invalid:
                show_error_dialog("api_key_invalid_error_title", "api_key_invalid_error_message")
            else:
                show_error_dialog("ai_client_error_title", "ai_client_error_message_generic")
                asyncio.run(generate_mp3(lm_main.get_string("ai_client_error_message_generic")));
                speak_action()
            time.sleep(3)
        except StopCandidateException as e:
            print(f"Response from AI stopped: {e}")
            asyncio.run(generate_mp3(lm_main.get_string("response_blocked_speech"))); speak_action()
        except Exception as e:
            print(f"An unexpected error occurred in the main loop: {e}")
            import traceback; traceback.print_exc()
            asyncio.run(generate_mp3(lm_main.get_string("unexpected_error_speech"))); speak_action()
            time.sleep(3)
        if main_loop_stop_event.is_set(): break
    print("Main loop finished.")
    set_overlay_mode_safe(None)


async def generate_mp3(text):
    global TTS_VOICE, lm_main # TTS_VOICE is now the effective one for the active agent
    if not text or not text.strip():
        text_sanitized = lm_main.get_string("default_tts_okay")
    else:
        text_sanitized = re.sub(r'[<>:"/\\|?*]', '', text).replace('\n', ' ').replace('\r', '')
        if not text_sanitized.strip():
            text_sanitized = lm_main.get_string("default_tts_understood")

    if not pygame.mixer.get_init():
        print("TTS generated, but Pygame mixer not initialized. Playback might fail.")

    communicate = Communicate(text=text_sanitized, voice=TTS_VOICE)
    output_file = get_app_data_path("reply.mp3") # Use helper for consistent path

    for attempt in range(5):
        try:
            if os.path.exists(output_file):
                if pygame.mixer.get_init() and pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
                if pygame.mixer.get_init(): pygame.mixer.music.unload()
                time.sleep(0.1); os.remove(output_file)
            break
        except OSError as e:
            print(f"{output_file} in use, attempt {attempt+1}/5... {e}"); await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error pre-save cleanup {output_file}, attempt {attempt+1}/5... {e}"); await asyncio.sleep(0.5)
    else:
        print(f"Could not delete {output_file}. Skipping TTS."); return
    try:
        await communicate.save(output_file); print(f"TTS saved to {output_file}")
    except Exception as e:
        print(f"Error saving {output_file}: {e}")


def trim_chat_history(current_chat_session):
    global MAX_HISTORY, client, chat_config # MAX_HISTORY is now the effective one
    if not current_chat_session or not client or not chat_config: return current_chat_session
    try:
        history = current_chat_session.get_history()
        required_history_length = MAX_HISTORY * 2
        if len(history) > required_history_length:
            trimmed_history = history[-required_history_length:]
            new_chat_session = client.chats.create(model="gemini-1.5-flash", config=chat_config, history=trimmed_history)
            print(f"Chat history trimmed. Old: {len(history)}, New: {len(trimmed_history)}")
            return new_chat_session
    except Exception as e:
        print(f"Error trimming chat history: {e}")
    return current_chat_session


def create_image(width, height, color1, color2):
    image = Image.new('RGB', (width, height), color1); dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2); return image

def get_icon_image():
    for ext in ["ico", "png"]:
        path = resource_path(f"icon.{ext}")
        if os.path.exists(path):
            try: return Image.open(path)
            except Exception as e: print(f"Could not load {path}: {e}")
    print("Icon file (icon.ico or icon.png) not found using resource_path. Using fallback image.")
    return create_image(64, 64, 'black', 'blue')


def on_settings_clicked(icon_instance, item_instance):
    global overlay, lm_main
    active_settings_toplevel = None
    if overlay and overlay.winfo_exists():
        for widget in overlay.winfo_children():
            if isinstance(widget, tk.Toplevel):
                try:
                    if widget.winfo_exists() and widget.title() == lm_main.get_string("settings_window_title"):
                        active_settings_toplevel = widget; break
                except tk.TclError: continue
        if not active_settings_toplevel:
            if tk._default_root:
                for widget in tk._default_root.winfo_children():
                    if isinstance(widget, tk.Toplevel) and widget.master == overlay:
                        try:
                            if widget.winfo_exists() and widget.title() == lm_main.get_string("settings_window_title"):
                                active_settings_toplevel = widget; break
                        except tk.TclError: continue

    if active_settings_toplevel:
        print("Settings window already open. Bringing to front.")
        active_settings_toplevel.lift(); active_settings_toplevel.focus_force(); return

    if not overlay or not overlay.winfo_exists():
        print("Error: Overlay window does not exist. Cannot open settings.")
        show_error_dialog("error_title", "overlay_not_available_error")
        return

    settings_top_level = tk.Toplevel(overlay)
    _settings_app_instance = ModernSettingsApp(settings_top_level, lm=lm_main)
    overlay.wait_window(settings_top_level)
    print("Settings window closed. Reloading and applying configuration.")
    newly_loaded_settings = app_load_settings()
    update_globals_from_settings(newly_loaded_settings)


def on_exit_clicked(icon_instance, item_instance):
    print("Exiting application...")
    global overlay, main_loop_thread, tray_icon
    main_loop_stop_event.set(); speech_stop_event.set()

    if tray_icon:
        try: tray_icon.stop(); print("Tray icon stop request sent.")
        except Exception as e: print(f"Error stopping tray icon: {e}")

    if overlay and overlay.winfo_exists():
        print("Sending quit request to Overlay (Tkinter mainloop)...")
        overlay.after(100, overlay.quit)
    elif overlay:
        print("Overlay window already destroyed.")
    else:
        print("Overlay not initialized.")

    if main_loop_thread and main_loop_thread.is_alive():
        print("Waiting for main loop thread to join...")
        main_loop_thread.join(timeout=5)
        if main_loop_thread.is_alive(): print("Warning: Main loop thread did not terminate cleanly.")

    if pygame.mixer.get_init(): pygame.mixer.quit(); print("Pygame Mixer quit.")
    print("Application exit sequence complete.")




if __name__ == "__main__":
    print("Manfred AI starting up...")




    _lock_file_path = get_app_data_path("manfred_ai.lock")
    try:
        _lock_file_descriptor = os.open(_lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(_lock_file_descriptor, str(os.getpid()).encode())
        except OSError as e:
            print(f"Warning: Could not write PID to lock file: {e}")
        atexit.register(cleanup_lock_file)
        print(f"Application instance lock acquired with file: {_lock_file_path}, PID: {os.getpid()}")
    except FileExistsError:
        print(f"Lock file '{_lock_file_path}' already exists. Another instance may be running.")
        if lm_main: # lm_main sollte hier verfügbar sein
            messagebox.showerror(
                lm_main.get_string("application_already_running_title"),
                lm_main.get_string("application_already_running_message")
            )
        else: # Fallback, falls lm_main aus irgendeinem Grund nicht initialisiert ist
            messagebox.showerror("Application Already Running", "Another instance of Manfred AI is already running.")
        sys.exit(1)
    except OSError as e:
        print(f"Critical error creating lock file '{_lock_file_path}': {e}. Cannot ensure single instance. Exiting.")
        if lm_main:
            messagebox.showerror(
                lm_main.get_string("lock_file_critical_error_title"),
                lm_main.get_string("lock_file_critical_error_message", e=str(e))
            )
        else:
            messagebox.showerror("Critical Startup Error", f"Could not create a lock file: {e}\nThe application cannot start.")
        sys.exit(1)

    update_globals_from_settings(current_app_settings, initial_load=True)

    if not API_KEY or API_KEY == app_default_settings["api_key"] and not os.getenv("GEMINI_API_KEY"):
        if lm_main:
             messagebox.showwarning(lm_main.get_string("api_key_not_configured_warning_title"),
                                   lm_main.get_string("api_key_not_configured_warning_message"))
        else:
            messagebox.showwarning("API Key Warning", "API key is not configured. Please set it in the settings.")

    overlay = ModernOverlay(speech_stop_event)
    tray_icon_image = get_icon_image()
    menu_items = (
        item(lambda text: lm_main.get_string("tray_settings", default_text="Settings"), on_settings_clicked),
        item(lambda text: lm_main.get_string("tray_console", default_text="Console"),
             lambda: show_console_window_external(overlay, lm_main)),
        item(lambda text: lm_main.get_string("tray_exit", default_text="Exit"), on_exit_clicked)
    )
    tray_icon = icon("ManfredAI", tray_icon_image, "Manfred AI", menu_items)

    main_loop_stop_event.clear(); speech_stop_event.clear()
    main_loop_thread = Thread(target=main_loop_logic, daemon=True); main_loop_thread.start()
    print("Main loop thread started.")

    tray_thread = Thread(target=tray_icon.run, daemon=True); tray_thread.start()
    print("Manfred AI tray application started. Right-click the icon for options.")
    pygame.mixer.music.load(resource_path("sounds/start.mp3"))
    pygame.mixer.music.play()

    try:
        overlay.mainloop()
    except KeyboardInterrupt:
        print("KeyboardInterrupt received, initiating exit..."); on_exit_clicked(None, None)
    except tk.TclError as e:
        if "application has been destroyed" in str(e).lower():
            print("Tkinter mainloop exited (app destroyed).")
        else:
            print(f"Tkinter TclError: {e}"); import traceback; traceback.print_exc(); on_exit_clicked(None, None)
    except Exception as e:
        print(f"An unexpected error in Tkinter mainloop: {e}"); import traceback; traceback.print_exc(); on_exit_clicked(None, None)

    print("Tkinter mainloop finished.")
    if not main_loop_stop_event.is_set():
        on_exit_clicked(None, None)
    print("Application process ending.")
