# C:/Users/Theminemat/Documents/Programming/manfred desktop ai/main.py
import asyncio
import os
import re
import playsound
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

try:
    from settings import (
        load_settings as app_load_settings,
        ModernSettingsApp,
        default_settings as app_default_settings,
        # load_system_prompts, # Removed from here
        # get_full_system_prompt, # Removed from here
        DEFAULT_SYSTEM_PROMPT_NAME, # Still needed from settings for defaults
        DEFAULT_SYSTEM_PROMPT_TEXT, # Needed for agent_get_full_system_prompt
        LanguageManager
    )
    from agent_builder import ( # New import for these
        load_system_prompts as agent_load_system_prompts,
        get_full_system_prompt as agent_get_full_system_prompt
    )
except ImportError as e:
    # Basic error handling for missing critical files
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
    pygame.mixer.init()
except pygame.error as e:
    print(f"Initial Pygame mixer init failed: {e}. Audio output may not work.")

# --- Global Variables ---
current_app_settings = app_load_settings()
lm_main = LanguageManager(current_app_settings.get("ui_language", app_default_settings["ui_language"]))
# Load system prompts using the new function, passing necessary defaults from settings.py
all_system_prompts = agent_load_system_prompts(DEFAULT_SYSTEM_PROMPT_NAME, DEFAULT_SYSTEM_PROMPT_TEXT)


CodeWord = ""
StopWords = []
MAX_HISTORY = 0
API_KEY = ""
OPEN_LINKS_AUTOMATICALLY = True
ACTIVE_SYSTEM_PROMPT_NAME = DEFAULT_SYSTEM_PROMPT_NAME # Initialized with default from settings
TTS_VOICE = app_default_settings["tts_voice"]
STT_LANGUAGE = "en-US"
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


# --- Utility Functions ---
def show_error_dialog(title_key: str, message_key: str, parent=None, **format_args):
    global lm_main, overlay

    title = lm_main.get_string(title_key, default_text="Error")
    message_text = lm_main.get_string(message_key, default_text="An error occurred: {e}", **format_args)

    if parent is None:
        if overlay and overlay.winfo_exists():
            parent = overlay

    messagebox.showerror(title, message_text, parent=parent)


def initialize_audio_devices():
    global mic, SELECTED_MIC_NAME, SELECTED_SPEAKER_NAME, recognizer, lm_main
    print("Initializing audio devices...")

    # Speaker (Pygame Mixer)
    try:
        current_mixer_device = None
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
                SELECTED_MIC_NAME = "System Default"
        except Exception as e:
            print(f"Error listing or finding microphones: {e}. Using system default.")
            SELECTED_MIC_NAME = "System Default"

    if SELECTED_MIC_NAME == "System Default":
        print("Using system default microphone.")

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
        try:
            mic = sr.Microphone()
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception as e_fallback_mic:
            print(f"Fallback microphone initialization also failed: {e_fallback_mic}")
            mic = None


def update_globals_from_settings(loaded_settings, initial_load=False):
    global CodeWord, StopWords, MAX_HISTORY, API_KEY, current_app_settings, all_system_prompts
    global client, chat, chat_config, OPEN_LINKS_AUTOMATICALLY, ACTIVE_SYSTEM_PROMPT_NAME, TTS_VOICE
    global lm_main, STT_LANGUAGE, SELECTED_MIC_NAME, SELECTED_SPEAKER_NAME
    # DEFAULT_SYSTEM_PROMPT_NAME and DEFAULT_SYSTEM_PROMPT_TEXT are already global via import

    old_api_key = current_app_settings.get("api_key") if not initial_load else None
    old_chat_length = current_app_settings.get("chat_length") if not initial_load else None
    old_open_links = current_app_settings.get("open_links_automatically", app_default_settings[
        "open_links_automatically"]) if not initial_load else False
    old_active_prompt_name = current_app_settings.get("active_system_prompt_name") if not initial_load else None
    old_ui_language = current_app_settings.get("ui_language") if not initial_load else None
    old_tts_voice = current_app_settings.get("tts_voice") if not initial_load else None
    old_mic_name = current_app_settings.get("selected_microphone") if not initial_load else None
    old_speaker_name = current_app_settings.get("selected_speaker") if not initial_load else None

    current_app_settings = loaded_settings
    # Reload system prompts using the new function
    all_system_prompts = agent_load_system_prompts(DEFAULT_SYSTEM_PROMPT_NAME, DEFAULT_SYSTEM_PROMPT_TEXT)


    new_ui_language = current_app_settings.get("ui_language", app_default_settings["ui_language"])
    if initial_load or old_ui_language != new_ui_language:
        lm_main.set_language(new_ui_language)

    CodeWord = current_app_settings.get("activation_word", app_default_settings["activation_word"])
    StopWords = current_app_settings.get("stop_words", app_default_settings["stop_words"])
    MAX_HISTORY = current_app_settings.get("chat_length", app_default_settings["chat_length"])
    OPEN_LINKS_AUTOMATICALLY = current_app_settings.get("open_links_automatically",
                                                        app_default_settings["open_links_automatically"])
    ACTIVE_SYSTEM_PROMPT_NAME = current_app_settings.get("active_system_prompt_name",
                                                         app_default_settings["active_system_prompt_name"])
    TTS_VOICE = current_app_settings.get("tts_voice", app_default_settings["tts_voice"])
    SELECTED_MIC_NAME = current_app_settings.get("selected_microphone", app_default_settings["selected_microphone"])
    SELECTED_SPEAKER_NAME = current_app_settings.get("selected_speaker", app_default_settings["selected_speaker"])

    tts_voice_changed = initial_load or old_tts_voice != TTS_VOICE
    if tts_voice_changed:
        try:
            stt_lang_parts = TTS_VOICE.split('-', 2)
            if len(stt_lang_parts) >= 2:
                STT_LANGUAGE = f"{stt_lang_parts[0]}-{stt_lang_parts[1]}"
                print(f"STT language set to: {STT_LANGUAGE} (derived from TTS voice: {TTS_VOICE})")
            else:
                STT_LANGUAGE = "en-US";
                print(f"Warning: Could not parse TTS voice '{TTS_VOICE}'. Defaulting STT to en-US.")
        except Exception as e:
            STT_LANGUAGE = "en-US";
            print(f"Error deriving STT language: {e}. Defaulting to en-US.")

    if ACTIVE_SYSTEM_PROMPT_NAME not in all_system_prompts:
        ACTIVE_SYSTEM_PROMPT_NAME = DEFAULT_SYSTEM_PROMPT_NAME
        print(
            f"Warning: Active system prompt '{current_app_settings.get('active_system_prompt_name')}' not found. Falling back to default.")

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

    # Use the new function for getting the full system prompt
    current_system_instruction = agent_get_full_system_prompt(
        ACTIVE_SYSTEM_PROMPT_NAME,
        all_system_prompts,
        CodeWord,
        DEFAULT_SYSTEM_PROMPT_TEXT # Pass the default text for fallback within the function
    )
    old_system_instruction_from_config = chat_config.system_instruction if chat_config else None

    if chat_config is None:
        chat_config = types.GenerateContentConfig(system_instruction=current_system_instruction)
    else:
        chat_config.system_instruction = current_system_instruction

    api_key_changed = (old_api_key != API_KEY) and not env_api_key
    system_prompt_changed = (old_active_prompt_name != ACTIVE_SYSTEM_PROMPT_NAME) or \
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
            messagebox.showinfo(
                lm_main.get_string("settings_updated_title"),
                lm_main.get_string("audio_devices_updated_message",
                                   default_text="Audio device settings updated: {devices}. Speech input/output reinitialized.",
                                   devices=", ".join(changed_audio_parts)),
                parent=overlay if overlay and overlay.winfo_exists() else None
            )

    if initial_load or api_key_changed or system_prompt_changed:
        if API_KEY and API_KEY != app_default_settings["api_key"]:
            try:
                if client is None or api_key_changed: client = gai.Client(api_key=API_KEY)
                current_history = []
                if chat and not api_key_changed and system_prompt_changed: # Only preserve if API key didn't change
                    try:
                        current_history = chat.get_history(); print("Preserving chat history.")
                    except Exception as e:
                        print(f"Could not preserve chat history: {e}.")
                chat = client.chats.create(model="gemini-1.5-flash", config=chat_config, history=current_history)
                print("AI Client and Chat initialized/updated.")
                if not initial_load:
                    msg_key = "settings_updated_reinit_api_key" if api_key_changed else "settings_updated_reinit_system_prompt"
                    messagebox.showinfo(lm_main.get_string("settings_updated_title"), lm_main.get_string(msg_key),
                                        parent=overlay if overlay and overlay.winfo_exists() else None)
            except Exception as e:
                print(f"Error initializing Google AI Client: {e}");
                client = None;
                chat = None
                if overlay and overlay.winfo_exists():
                    show_error_dialog("ai_client_error_title",
                                      "ai_client_error_message",
                                      parent=overlay,
                                      e=str(e))
        else: # API Key is placeholder or missing
            client = None; chat = None

    if not initial_load and not (api_key_changed or system_prompt_changed or mic_changed or speaker_changed):
        changed_parts = []
        if old_chat_length != MAX_HISTORY: changed_parts.append(
            lm_main.get_string("chat_length_label").replace(":", ""))
        if old_open_links != OPEN_LINKS_AUTOMATICALLY: changed_parts.append(
            lm_main.get_string("open_links_label").replace(":", ""))
        if tts_voice_changed: changed_parts.append(lm_main.get_string("tts_voice_label").replace(":", ""))
        # Note: UI language change is handled differently, often requiring restart or re-init of UI parts.
        # Here we only show a message if other non-reinitializing settings changed.

        if changed_parts:
            messagebox.showinfo(lm_main.get_string("settings_updated_title"),
                                lm_main.get_string("settings_updated_applied_changes",
                                                   changed_parts=", ".join(changed_parts)),
                                parent=overlay if overlay and overlay.winfo_exists() else None)
        elif old_ui_language == new_ui_language: # No relevant change and UI lang same
            # No message needed if only UI language changed and it was handled, or no changes at all.
            pass


update_globals_from_settings(current_app_settings, initial_load=True)

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

        temp_audio_file = "tts_playback_temp.mp3"
        source_audio_file = "reply.mp3"

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
            pygame.mixer.music.load("sounds/start.mp3")
            pygame.mixer.music.play()
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
            text = recognizer.recognize_google(audio, language=STT_LANGUAGE)
            print(f"Recognized (lang: {STT_LANGUAGE}): {text}")
            text_lower = text.lower()

            if not listening_mode:
                if CodeWord.lower() in text_lower:
                    listening_mode = True
                    command = text_lower.split(CodeWord.lower(), 1)[-1].strip()
                    if not command: # Only activation word spoken
                        print("Activated. Waiting for command...")
                        if pygame.mixer.get_init():
                            try: pygame.mixer.music.load("sounds/listening.mp3"); pygame.mixer.music.play()
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
                        try: pygame.mixer.music.load("sounds/deaktivated.mp3"); pygame.mixer.music.play()
                        except pygame.error as e: print(f"Sound error: {e}")
                    continue
                else: # It's a command
                    command = text.strip()

            if not command: print("No usable command."); continue # Should be caught by earlier logic if only activation word
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
                        asyncio.run(generate_mp3(response_text_for_tts)); speak_action(); continue # Speak failure and loop
                else: # Not opening automatically
                    print(f"Link found (not opened): {url}")

            if response_text_for_tts:
                await_task = asyncio.run(generate_mp3(response_text_for_tts)) # Ensure this runs and completes
                speak_action()
            elif listening_mode and not main_loop_stop_event.is_set(): # No TTS but still listening
                set_overlay_mode_safe('listening')
            chat = trim_chat_history(chat)

        except sr.UnknownValueError:
            if listening_mode: print("Could not understand.") # Only print if we expected to understand
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            asyncio.run(generate_mp3(lm_main.get_string("speech_recognition_problem_speech"))); speak_action()
        except ClientError as e:
            print(f"Google AI ClientError: {e}")
            is_api_key_invalid = False # Simplified check
            if hasattr(e, 'response_json') and e.response_json and 'error' in e.response_json and 'details' in e.response_json['error']:
                for detail in e.response_json['error']['details']:
                    if detail.get('reason') == 'API_KEY_INVALID': is_api_key_invalid = True; break
            if is_api_key_invalid:
                show_error_dialog("api_key_invalid_error_title", "api_key_invalid_error_message")
            else:
                show_error_dialog("ai_client_error_title", "ai_client_error_message_generic")
                asyncio.run(generate_mp3(lm_main.get_string("ai_client_error_message_generic"))); # Also speak it
                speak_action()
            time.sleep(3) # Pause to avoid spamming errors
        except StopCandidateException as e: # Handle Gemini safety blocks
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
    global TTS_VOICE, lm_main
    if not text or not text.strip(): # Handle empty or whitespace-only text
        text_sanitized = lm_main.get_string("default_tts_okay") # "Okay." or similar
    else:
        # Sanitize text for TTS, removing characters that might cause issues with edge-tts or filenames
        text_sanitized = re.sub(r'[<>:"/\\|?*]', '', text).replace('\n', ' ').replace('\r', '')
        if not text_sanitized.strip(): # If sanitization results in empty string
            text_sanitized = lm_main.get_string("default_tts_understood") # "Understood." or similar

    if not pygame.mixer.get_init(): # Check if mixer is available for playback later
        print("TTS generated, but Pygame mixer not initialized. Playback might fail.")

    communicate = Communicate(text=text_sanitized, voice=TTS_VOICE)
    output_file = "reply.mp3"
    # Attempt to delete existing file with retries, especially if music is busy
    for attempt in range(5): # Retry up to 5 times
        try:
            if os.path.exists(output_file):
                if pygame.mixer.get_init() and pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
                if pygame.mixer.get_init(): pygame.mixer.music.unload() # Ensure file is not locked
                time.sleep(0.1); os.remove(output_file)
            break # Success
        except OSError as e: # FileInUse or PermissionError
            print(f"{output_file} in use, attempt {attempt+1}/5... {e}"); await asyncio.sleep(0.5)
        except Exception as e: # Other errors
            print(f"Error pre-save cleanup {output_file}, attempt {attempt+1}/5... {e}"); await asyncio.sleep(0.5)
    else: # Loop completed without break (all attempts failed)
        print(f"Could not delete {output_file}. Skipping TTS."); return
    try:
        await communicate.save(output_file); print(f"TTS saved to {output_file}")
    except Exception as e:
        print(f"Error saving {output_file}: {e}")


def trim_chat_history(current_chat_session):
    global MAX_HISTORY, client, chat_config
    if not current_chat_session or not client or not chat_config: return current_chat_session # Guard clause
    try:
        history = current_chat_session.get_history()
        # Each "turn" is a user message and a model reply, so MAX_HISTORY turns = MAX_HISTORY * 2 messages
        required_history_length = MAX_HISTORY * 2
        if len(history) > required_history_length:
            trimmed_history = history[-required_history_length:] # Keep the most recent messages
            # Create a new chat session with the trimmed history
            new_chat_session = client.chats.create(model="gemini-1.5-flash", config=chat_config, history=trimmed_history)
            print(f"Chat history trimmed. Old: {len(history)}, New: {len(trimmed_history)}")
            return new_chat_session
    except Exception as e:
        print(f"Error trimming chat history: {e}")
    return current_chat_session # Return original on error or if no trimming needed


def create_image(width, height, color1, color2): # Fallback icon generator
    image = Image.new('RGB', (width, height), color1); dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2); return image

def get_icon_image():
    for ext in ["ico", "png"]: # Prefer .ico for Windows tray
        path = f"icon.{ext}"
        if os.path.exists(path):
            try: return Image.open(path)
            except Exception as e: print(f"Could not load {path}: {e}")
    return create_image(64, 64, 'black', 'blue') # Fallback


def on_settings_clicked(icon_instance, item_instance):
    global overlay, lm_main # Ensure lm_main is accessible
    active_settings_toplevel = None
    # Check if a settings window (Toplevel) is already open and is a child of overlay
    if overlay and overlay.winfo_exists(): # Check if overlay itself exists
        for widget in overlay.winfo_children(): # Check direct children first
            if isinstance(widget, tk.Toplevel):
                try: # Check if widget still exists and has the correct title
                    if widget.winfo_exists() and widget.title() == lm_main.get_string("settings_window_title"):
                        active_settings_toplevel = widget; break
                except tk.TclError: continue # Widget might have been destroyed
        # If not found in direct children, check all Toplevels (less ideal but a fallback)
        if not active_settings_toplevel:
            for widget in tk._default_root.winfo_children(): # Check all Toplevels
                if isinstance(widget, tk.Toplevel) and widget.master == overlay: # Check master
                    try:
                        if widget.winfo_exists() and widget.title() == lm_main.get_string("settings_window_title"):
                            active_settings_toplevel = widget; break
                    except tk.TclError: continue

    if active_settings_toplevel:
        print("Settings window already open. Bringing to front.")
        active_settings_toplevel.lift(); active_settings_toplevel.focus_force(); return

    if not overlay or not overlay.winfo_exists(): # Ensure overlay exists before opening settings
        print("Error: Overlay window does not exist. Cannot open settings.")
        show_error_dialog("error_title", "overlay_not_available_error")
        return

    settings_top_level = tk.Toplevel(overlay) # Make settings a child of overlay
    _settings_app_instance = ModernSettingsApp(settings_top_level, lm=lm_main) # Pass lm_main
    overlay.wait_window(settings_top_level) # Wait for settings window to close
    print("Settings window closed. Reloading and applying configuration.")
    newly_loaded_settings = app_load_settings()
    update_globals_from_settings(newly_loaded_settings)


def on_exit_clicked(icon_instance, item_instance):
    print("Exiting application...")
    global overlay, main_loop_thread, tray_icon
    main_loop_stop_event.set(); speech_stop_event.set() # Signal all loops to stop

    if tray_icon:
        try: tray_icon.stop(); print("Tray icon stop request sent.")
        except Exception as e: print(f"Error stopping tray icon: {e}") # pystray might raise if already stopped

    if overlay and overlay.winfo_exists(): # If overlay exists, quit its mainloop
        print("Sending quit request to Overlay (Tkinter mainloop)...")
        overlay.after(100, overlay.quit) # Schedule quit after short delay
    elif overlay: # Overlay object exists but window doesn't (already destroyed)
        print("Overlay window already destroyed.")
    else: # Overlay was never initialized
        print("Overlay not initialized.")

    if main_loop_thread and main_loop_thread.is_alive():
        print("Waiting for main loop thread to join...")
        main_loop_thread.join(timeout=5) # Wait for thread to finish
        if main_loop_thread.is_alive(): print("Warning: Main loop thread did not terminate cleanly.")

    if pygame.mixer.get_init(): pygame.mixer.quit(); print("Pygame Mixer quit.")
    print("Application exit sequence complete.")
    # sys.exit(0) # Not always needed if all threads/loops terminate cleanly


if __name__ == "__main__":
    if not API_KEY or API_KEY == app_default_settings["api_key"] and not os.getenv("GEMINI_API_KEY"):
        # No parent for this initial messagebox
        messagebox.showwarning(lm_main.get_string("api_key_not_configured_warning_title"),
                               lm_main.get_string("api_key_not_configured_warning_message"))

    overlay = ModernOverlay(speech_stop_event) # Pass the event object
    tray_icon_image = get_icon_image()
    # Use lambdas for menu items to ensure lm_main.get_string is called when menu is built/shown
    menu_items = (
        item(lambda text: lm_main.get_string("tray_settings", default_text="Settings"), on_settings_clicked),
        item(lambda text: lm_main.get_string("tray_exit", default_text="Exit"), on_exit_clicked)
    )
    tray_icon = icon("ManfredAI", tray_icon_image, "Manfred AI", menu_items)

    main_loop_stop_event.clear(); speech_stop_event.clear() # Ensure events are clear at start
    main_loop_thread = Thread(target=main_loop_logic, daemon=True); main_loop_thread.start()
    print("Main loop thread started.")

    tray_thread = Thread(target=tray_icon.run, daemon=True); tray_thread.start() # Run tray in its own thread
    print("Manfred AI tray application started. Right-click the icon for options.")

    try:
        overlay.mainloop() # Start Tkinter main loop for the overlay
    except KeyboardInterrupt:
        print("KeyboardInterrupt received, initiating exit..."); on_exit_clicked(None, None)
    except tk.TclError as e: # Catch Tcl errors, often from destroying widgets
        if "application has been destroyed" in str(e).lower():
            print("Tkinter mainloop exited (app destroyed).")
        else: # Other TclError
            print(f"Tkinter TclError: {e}"); import traceback; traceback.print_exc(); on_exit_clicked(None, None)
    except Exception as e: # Catch any other unexpected errors in mainloop
        print(f"An unexpected error in Tkinter mainloop: {e}"); import traceback; traceback.print_exc(); on_exit_clicked(None, None)

    print("Tkinter mainloop finished.")
    if not main_loop_stop_event.is_set(): # If exit wasn't already triggered
        on_exit_clicked(None, None)
    print("Application process ending.")