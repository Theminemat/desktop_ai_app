# C:/Users/Theminemat/Documents/Programming/manfred desktop ai/settings.py
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter.font import Font
# from tkinter.scrolledtext import ScrolledText # No longer needed here
import sv_ttk
import sys
import re
import asyncio
from threading import Thread
from edge_tts import Communicate
import pygame
import time

# --- Mock speech_recognition for testing if not installed (for settings.py standalone) ---
try:
    import speech_recognition as sr_audio
except ImportError:
    print("WARNING (settings.py): speech_recognition not found. Using mock for microphone listing.")


    class MockRecognizerSettings:
        pass


    class MockMicrophoneSettings:
        @staticmethod
        def list_microphone_names():
            print("Mock list_microphone_names called from settings.py")
            return ["Mock Microphone 1 (Settings)", "Another Mock Mic (Settings)", "System Default Mock Mic (Settings)"]


    class MockSrAudioModule:
        Recognizer = MockRecognizerSettings
        Microphone = MockMicrophoneSettings
        WaitTimeoutError = type('WaitTimeoutError', (Exception,), {})
        UnknownValueError = type('UnknownValueError', (Exception,), {})
        RequestError = type('RequestError', (Exception,), {})


    sr_audio = MockSrAudioModule()
# --- End Mock ---

# Import from agent_builder
try:
    from agent_builder import (
        SystemPromptManagerWindow,
        load_system_prompts as agent_load_system_prompts,
        save_system_prompts as agent_save_system_prompts,  # Though not directly used here, good for consistency
        get_full_system_prompt as agent_get_full_system_prompt,
        # Constants for agent settings to reference default values if needed (though not directly used here for now)
        # AGENT_SETTING_ACTIVATION_WORD, AGENT_SETTING_STOP_WORDS,
        # AGENT_SETTING_CHAT_LENGTH, AGENT_SETTING_TTS_VOICE, AGENT_SETTING_OPEN_LINKS
    )
except ImportError:
    messagebox.showerror("Error", "agent_builder.py could not be found or imported.")
    sys.exit(1)

SETTINGS_FILE = "settings.json"
LANGUAGES_DIR = "languages"

DEFAULT_SYSTEM_PROMPT_NAME = "Default Prompt"
DEFAULT_SYSTEM_PROMPT_TEXT = (
    "You are Manfred, a highly intelligent and efficient AI assistant. "
    "Reply without formatting and keep replies short and simple. "
    "You always speak respectfully, and fluent English. "
    "Your responses must be clear, concise, and helpful—avoid unnecessary elaboration, especially for simple tasks. "
    "A good amount of humor is good to keep the conversation natural, friend-like. Your top priorities are efficiency and clarity."
)

# These settings now represent:
# - api_key, ui_language, selected_microphone, selected_speaker, active_system_prompt_name: True global settings
# - chat_length, activation_word, stop_words, open_links_automatically, tts_voice: Global fallbacks for agents
default_settings = {
    "api_key": "Enter your Gemini API key here",
    "ui_language": "en-US",
    "selected_microphone": "System Default",
    "selected_speaker": "System Default",
    "active_system_prompt_name": DEFAULT_SYSTEM_PROMPT_NAME,

    # Fallback settings for agents (if not overridden in agent_builder)
    "activation_word": "Manfred", # Fallback
    "stop_words": ["stop", "stopp", "exit", "quit"], # Fallback
    "chat_length": 5, # Fallback
    "open_links_automatically": True, # Fallback
    "tts_voice": "en-US-AriaNeural", # Fallback
}

TTS_VOICES_STRUCTURED = {
    "German": {
        "code": "de-DE", "flag": "🇩🇪",
        "preview_text": "Dies ist ein Test der ausgewählten Stimme.",
        "voices": {
            "Amala": "de-DE-AmalaNeural",
            "Conrad": "de-DE-ConradNeural",
            "Katja": "de-DE-KatjaNeural"
        }
    },
    "English (US)": {
        "code": "en-US", "flag": "🇺🇸",
        "preview_text": "This is a test of the selected voice.",
        "voices": {
            "Aria": "en-US-AriaNeural",
            "Jenny": "en-US-JennyNeural",
            "Guy": "en-US-GuyNeural"
        }
    },
    "English (GB)": {
        "code": "en-GB", "flag": "🇬🇧",
        "preview_text": "This is a test of the selected voice.",
        "voices": {
            "Libby": "en-GB-LibbyNeural",
            "Ryan": "en-GB-RyanNeural"
        }
    },
    "French": {
        "code": "fr-FR", "flag": "🇫🇷",
        "preview_text": "Ceci est un test de la voix sélectionnée.",
        "voices": {
            "Denise": "fr-FR-DeniseNeural",
            "Henri": "fr-FR-HenriNeural"
        }
    },
    "Spanish (Spain)": {
        "code": "es-ES", "flag": "🇪🇸",
        "preview_text": "Esta es una prueba de la voz seleccionada.",
        "voices": {
            "Alvaro": "es-ES-AlvaroNeural",
            "Elvira": "es-ES-ElviraNeural"
        }
    },
    "Italian": {
        "code": "it-IT", "flag": "🇮🇹",
        "preview_text": "Questa è una prova della voce selezionata.",
        "voices": {
            "Diego": "it-IT-DiegoNeural",
            "Elsa": "it-IT-ElsaNeural"
        }
    },
    "Portuguese (Portugal)": {
        "code": "pt-PT", "flag": "🇵🇹",
        "preview_text": "Este é um teste da voz selecionada.",
        "voices": {
            "Duarte": "pt-PT-DuarteNeural",
            "Raquel": "pt-PT-RaquelNeural"
        }
    },
    "Dutch": {
        "code": "nl-NL", "flag": "🇳🇱",
        "preview_text": "Dit is een test van de geselecteerde stem.",
        "voices": {
            "Colette": "nl-NL-ColetteNeural",
            "Maarten": "nl-NL-MaartenNeural"
        }
    },
    "Polish": {
        "code": "pl-PL", "flag": "🇵🇱",
        "preview_text": "To jest test wybranego głosu.",
        "voices": {
            "Marek": "pl-PL-MarekNeural",
            "Zofia": "pl-PL-ZofiaNeural"
        }
    },
    "Swedish": {
        "code": "sv-SE", "flag": "🇸🇪",
        "preview_text": "Detta är ett test av den valda rösten.",
        "voices": {
            "Mattias": "sv-SE-MattiasNeural",
            "Sofie": "sv-SE-SofieNeural"
        }
    },
    "Danish": {
        "code": "da-DK", "flag": "🇩🇰",
        "preview_text": "Dette er en test af den valgte stemme.",
        "voices": {
            "Jeppe": "da-DK-JeppeNeural",
            "Christel": "da-DK-ChristelNeural"
        }
    },
    "Norwegian (Bokmål)": {
        "code": "nb-NO", "flag": "🇳🇴",
        "preview_text": "Dette er en test av den valgte stemmen.",
        "voices": {
            "Finn": "nb-NO-FinnNeural",
            "Pernille": "nb-NO-PernilleNeural"
        }
    },
    "Finnish": {
        "code": "fi-FI", "flag": "🇫🇮",
        "preview_text": "Tämä on valitun äänen testi.",
        "voices": {
            "Harri": "fi-FI-HarriNeural",
            "Noora": "fi-FI-NooraNeural"
        }
    }
}
AVAILABLE_UI_LANGUAGES = {}


class LanguageManager:
    def __init__(self, initial_lang_code="en-US"):
        self.current_lang_code = initial_lang_code
        self.translations = {}
        self.fallback_translations = {}
        self._active_window_for_messagebox = None # For agent_builder
        self._load_fallback_language()
        self.load_language(self.current_lang_code)

    def _load_fallback_language(self):
        try:
            fallback_path = os.path.join(LANGUAGES_DIR, "en-US.json")
            if os.path.exists(fallback_path):
                with open(fallback_path, "r", encoding="utf-8") as f:
                    self.fallback_translations = json.load(f)
            else:
                print(
                    f"CRITICAL ERROR: Fallback language file en-US.json not found in '{LANGUAGES_DIR}'. UI text will be missing.")
                self.fallback_translations = {}
        except Exception as e:
            print(f"Error loading fallback language en-US: {e}")
            self.fallback_translations = {}

    def load_language(self, lang_code):
        self.current_lang_code = lang_code
        try:
            lang_file_path = os.path.join(LANGUAGES_DIR, f"{lang_code}.json")
            if not os.path.exists(lang_file_path):
                print(f"Warning: Language file {lang_file_path} not found. Using fallback (en-US).")
                self.translations = self.fallback_translations.copy()
                if lang_code != "en-US":
                    self.current_lang_code = "en-US"
                return

            with open(lang_file_path, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        except Exception as e:
            print(f"Error loading language {lang_code}: {e}. Using fallback (en-US).")
            self.translations = self.fallback_translations.copy()
            if lang_code != "en-US":
                self.current_lang_code = "en-US"

    def get_string(self, key, default_text=None, **kwargs):
        val_candidate = self.translations.get(key, self.fallback_translations.get(key))
        if val_candidate is None:
            if default_text is not None:
                val = default_text
            else:
                val = f"<{key}>"
        else:
            val = val_candidate

        if kwargs:
            try:
                return val.format(**kwargs)
            except (KeyError, ValueError, TypeError) as e:
                print(f"Warning: Formatting error for key '{key}' with value '{val}' and args {kwargs}: {e}")
                return val
        return val

    def set_language(self, lang_code):
        self.load_language(lang_code)

    def set_active_window_for_messagebox(self, window):
        self._active_window_for_messagebox = window

    def get_active_window_for_messagebox(self):
        return self._active_window_for_messagebox


def scan_available_languages():
    global AVAILABLE_UI_LANGUAGES
    AVAILABLE_UI_LANGUAGES = {}
    if not os.path.isdir(LANGUAGES_DIR):
        print(f"Warning: Languages directory '{LANGUAGES_DIR}' not found.")
        AVAILABLE_UI_LANGUAGES["en-US"] = {"name": "English (US)", "flag": "🇺🇸"}
        return

    for filename in os.listdir(LANGUAGES_DIR):
        if filename.endswith(".json"):
            lang_code = filename[:-5]
            display_name = lang_code
            flag = "🏳️"

            try:
                if lang_code == "en-US": display_name, flag = "English (US)", "🇺🇸"
                elif lang_code == "de-DE": display_name, flag = "Deutsch (German)", "🇩🇪"
                elif lang_code == "fr-FR": display_name, flag = "Français", "🇫🇷"
                AVAILABLE_UI_LANGUAGES[lang_code] = {"name": display_name, "flag": flag}
            except Exception as e:
                print(f"Error processing language file {filename}: {e}")
                AVAILABLE_UI_LANGUAGES[lang_code] = {"name": lang_code, "flag": "🏳️"}

    if not AVAILABLE_UI_LANGUAGES:
        AVAILABLE_UI_LANGUAGES["en-US"] = {"name": "English (US)", "flag": "🇺🇸"}


scan_available_languages()


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_settings, f, indent=4, ensure_ascii=False)
            print(f"'{SETTINGS_FILE}' not found. Created with default settings.")
            return default_settings.copy()
        except Exception as e:
            print(f"Error creating default settings file: {e}")
            return default_settings.copy()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            updated = False
            for key, value in default_settings.items():
                if key not in loaded:
                    loaded[key] = value
                    updated = True
            if updated:
                try:
                    with open(SETTINGS_FILE, "w", encoding="utf-8") as f_update:
                        json.dump(loaded, f_update, indent=4, ensure_ascii=False)
                    print(f"'{SETTINGS_FILE}' was missing some keys. Updated with defaults and saved.")
                except Exception as e_save:
                    print(f"Error saving updated settings file: {e_save}")
            return loaded
    except Exception as e:
        print(f"Error loading settings: {e}. Returning default settings.")
        return default_settings.copy()


def save_settings(settings, lm):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        if lm:
            messagebox.showinfo(lm.get_string("success_title"), lm.get_string("settings_saved_success"),
                                parent=lm.get_active_window_for_messagebox()) # Use parent from lm
        return True
    except Exception as e:
        if lm:
            messagebox.showerror(lm.get_string("error_title"), lm.get_string("failed_to_save_settings_error", e=e),
                                 parent=lm.get_active_window_for_messagebox()) # Use parent from lm
        else:
            messagebox.showerror("Error", f"Failed to save settings:\n{e}")
        return False


class ModernSettingsApp:
    def __init__(self, root, lm):
        self.root = root
        self.settings = load_settings()
        self.lm = lm
        self.lm.set_active_window_for_messagebox(self.root) # Set parent for lm's messageboxes

        # Store default_settings for agent_builder placeholders
        self.default_settings = default_settings.copy() # Make a copy
        self.TTS_VOICES_STRUCTURED = TTS_VOICES_STRUCTURED # For agent_builder

        if not pygame.mixer.get_init():
            try: pygame.mixer.init()
            except pygame.error as e: print(f"Warning: Pygame mixer could not be initialized in settings: {e}")

        try:
            icon_path = "icon.ico"
            if os.path.exists(icon_path): self.root.iconbitmap(default=icon_path)
        except Exception as e: print(f"Warning: Could not set icon: {e}")

        self.root.minsize(650, 800) # Adjusted minsize for new layout

        try: sv_ttk.set_theme("dark")
        except Exception: print("Warning: sv_ttk theme failed. Using default Tkinter theme.")

        self.header_font = Font(family="Segoe UI", size=16, weight="bold")
        self.label_font = Font(family="Segoe UI", size=10)
        self.small_font = Font(family="Segoe UI", size=8)

        self.system_prompts = agent_load_system_prompts(DEFAULT_SYSTEM_PROMPT_NAME, DEFAULT_SYSTEM_PROMPT_TEXT)

        self.main_frame = ttk.Frame(root, padding=(20, 20, 20, 20))
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.build_ui()
        self.retranslate_ui()
        self.load_settings_into_ui()

        self.center_window()
        if isinstance(self.root, tk.Toplevel):
            self.root.grab_set()
            self.root.protocol("WM_DELETE_WINDOW", self.cancel_and_close)

    def _get_speaker_names(self):
        names = [self.lm.get_string("system_default_device_option", default_text="System Default")]
        try:
            if not pygame.mixer.get_init(): pygame.mixer.init()
            if pygame.mixer.get_init():
                num_devices = pygame.mixer.get_num_output_devices()
                for i in range(num_devices):
                    name = pygame.mixer.get_output_device_name(i)
                    if name:
                        decoded_name = name.decode('utf-8', errors='replace') if isinstance(name, bytes) else name
                        if decoded_name.strip(): names.append(decoded_name)
            else: print("Pygame mixer could not be initialized. Cannot list speaker devices.")
        except Exception as e: print(f"Error listing speaker devices: {e}")
        return list(dict.fromkeys(names))

    def _get_microphone_names(self):
        names = [self.lm.get_string("system_default_device_option", default_text="System Default")]
        try:
            if sr_audio and hasattr(sr_audio, 'Microphone') and hasattr(sr_audio.Microphone, 'list_microphone_names'):
                mic_names = sr_audio.Microphone.list_microphone_names()
                if mic_names: names.extend(m for m in mic_names if m and m.strip())
            else: print("Cannot list microphones: speech_recognition library not available or incomplete.")
        except Exception as e: print(f"Error listing microphone devices: {e}")
        return list(dict.fromkeys(names))

    def _get_sorted_tts_language_display_names(self):
        ui_lang_code = self.lm.current_lang_code
        ui_tts_lang_key = None
        for lang_key, lang_data in TTS_VOICES_STRUCTURED.items():
            if lang_data["code"] == ui_lang_code: ui_tts_lang_key = lang_key; break
        english_keys = [k for k, data in TTS_VOICES_STRUCTURED.items() if data["code"].startswith("en-")]
        sorted_keys = []
        if ui_tts_lang_key: sorted_keys.append(ui_tts_lang_key)
        for eng_key in sorted(english_keys):
            if eng_key not in sorted_keys: sorted_keys.append(eng_key)
        for lang_key in sorted(TTS_VOICES_STRUCTURED.keys()):
            if lang_key not in sorted_keys: sorted_keys.append(lang_key)
        return [f"{TTS_VOICES_STRUCTURED[key]['flag']} {key}" for key in sorted_keys]

    def _on_tts_language_selected(self, event=None):
        self._update_tts_specific_voices_combobox()
        if self.tts_specific_voice_combobox['values'] and not self.tts_specific_voice_var.get():
            self.tts_specific_voice_var.set(self.tts_specific_voice_combobox['values'][0])
        elif not self.tts_specific_voice_combobox['values']:
            self.tts_specific_voice_var.set("")

    def _update_tts_specific_voices_combobox(self):
        selected_lang_display_with_flag = self.tts_language_var.get()
        voice_names = []
        if selected_lang_display_with_flag:
            target_lang_key = None
            for l_key, l_data in TTS_VOICES_STRUCTURED.items():
                if f"{l_data['flag']} {l_key}" == selected_lang_display_with_flag: target_lang_key = l_key; break
            if target_lang_key and target_lang_key in TTS_VOICES_STRUCTURED:
                voice_names = sorted(list(TTS_VOICES_STRUCTURED[target_lang_key]["voices"].keys()))

        current_specific_voice = self.tts_specific_voice_var.get()
        self.tts_specific_voice_combobox['values'] = voice_names
        if voice_names:
            if current_specific_voice in voice_names: self.tts_specific_voice_var.set(current_specific_voice)
            else: self.tts_specific_voice_var.set(voice_names[0])
            self.tts_specific_voice_combobox.configure(state="readonly")
            self.preview_tts_button.configure(state="normal")
        else:
            self.tts_specific_voice_var.set("")
            self.tts_specific_voice_combobox.configure(state="disabled")
            self.preview_tts_button.configure(state="disabled")

    def _play_tts_preview(self):
        selected_lang_display_with_flag = self.tts_language_var.get()
        selected_voice_name_short = self.tts_specific_voice_var.get()
        if not selected_lang_display_with_flag or not selected_voice_name_short:
            messagebox.showwarning(self.lm.get_string("warning_title"),
                                   self.lm.get_string("select_language_voice_warning"), parent=self.root)
            return

        voice_id_to_preview, preview_text_for_tts, target_lang_key = None, "Voice preview.", None
        for l_key, l_data_tts in TTS_VOICES_STRUCTURED.items():
            if f"{l_data_tts['flag']} {l_key}" == selected_lang_display_with_flag: target_lang_key = l_key; break
        if target_lang_key:
            lang_data = TTS_VOICES_STRUCTURED[target_lang_key]
            if selected_voice_name_short in lang_data["voices"]:
                voice_id_to_preview = lang_data["voices"][selected_voice_name_short]
            preview_text_for_tts = lang_data.get("preview_text", preview_text_for_tts)
        if not voice_id_to_preview:
            messagebox.showerror(self.lm.get_string("error_title"),
                                   self.lm.get_string("could_not_find_voice_id_error"), parent=self.root)
            return
        self.preview_tts_button.configure(state=tk.DISABLED)

        def _do_preview_thread():
            temp_file = "tts_preview_temp.mp3"
            try:
                loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                communicate_obj = Communicate(text=preview_text_for_tts, voice=voice_id_to_preview)
                async def save_audio(): await communicate_obj.save(temp_file)
                loop.run_until_complete(save_audio())
                if os.path.exists(temp_file) and pygame.mixer.get_init():
                    pygame.mixer.music.load(temp_file); pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy(): time.sleep(0.05)
                    pygame.mixer.music.unload(); time.sleep(0.1); os.remove(temp_file)
                elif not pygame.mixer.get_init(): print("Pygame mixer not initialized, cannot play preview.")
            except Exception as e:
                print(f"Error during TTS preview: {e}")
                self.root.after(0, lambda: messagebox.showerror(
                    self.lm.get_string("error_title"),
                    self.lm.get_string("preview_failed_error", e=str(e)), parent=self.root))
            finally:
                self.root.after(0, lambda: self.preview_tts_button.configure(state=tk.NORMAL))
                if os.path.exists(temp_file):
                    try: os.remove(temp_file)
                    except Exception as e_rem: print(f"Error removing temp preview file: {e_rem}")
        Thread(target=_do_preview_thread, daemon=True).start()

    def build_ui(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()

        self.header_frame = ttk.Frame(self.main_frame)
        self.header_frame.pack(fill=tk.X, pady=(0, 15)) # Reduced bottom padding
        self.header_label = ttk.Label(self.header_frame, font=self.header_font)
        self.header_label.pack(side=tk.LEFT)

        # --- Standard Settings Group ---
        self.standard_settings_frame = ttk.LabelFrame(self.main_frame, padding=(15, 10))
        self.standard_settings_frame.pack(fill=tk.X, pady=(0, 10)) # Add some bottom padding
        self.standard_settings_frame.columnconfigure(2, weight=1)
        current_row_std = 0

        # Helper to create a setting row
        def create_setting_row(parent_frame, label_key, tooltip_key, widget_creator_func, row):
            label = ttk.Label(parent_frame, font=self.label_font)
            label.grid(row=row, column=0, sticky="w", pady=5, padx=(0, 2))
            help_button = ttk.Button(parent_frame, text="?", width=2, style="Help.TButton",
                                     command=lambda tk_key=tooltip_key: self.show_help_tooltip(tk_key))
            help_button.grid(row=row, column=1, sticky="w", padx=(0, 5))
            widget_container = widget_creator_func(parent_frame)
            if isinstance(widget_container, tuple) and len(widget_container) == 2 and isinstance(widget_container[0], tk.Widget):
                widget, grid_options = widget_container
                final_grid_options = {**{"sticky": "ew", "padx": (5, 0), "pady": 5}, **grid_options}
                widget.grid(row=row, column=2, **final_grid_options)
            elif isinstance(widget_container, tk.Widget):
                widget_container.grid(row=row, column=2, sticky="ew", padx=(5, 0), pady=5)
            else: # Frame or complex widget
                widget_container.grid(row=row, column=2, sticky="ew", padx=(5, 0), pady=5)
            return label, widget_container # Return label and main input widget/container

        # API Key
        self.api_key_var = tk.StringVar()
        self.api_key_label, _ = create_setting_row(self.standard_settings_frame, "api_key_label", "api_key_tooltip",
            lambda sf: ttk.Entry(sf, textvariable=self.api_key_var, width=40), current_row_std)
        current_row_std += 1

        # UI Language
        self.ui_language_var = tk.StringVar()
        self.ui_language_label, self.ui_language_combobox = create_setting_row(self.standard_settings_frame, "ui_language_label", "ui_language_tooltip",
            lambda sf: ttk.Combobox(sf, textvariable=self.ui_language_var, state="readonly", width=30), current_row_std)
        current_row_std += 1
        self.ui_language_combobox.bind("<<ComboboxSelected>>", self.on_language_change)

        # Microphone Selection
        self.microphone_var = tk.StringVar()
        self.microphone_label, self.microphone_combobox = create_setting_row(self.standard_settings_frame, "microphone_label", "microphone_tooltip",
            lambda sf: ttk.Combobox(sf, textvariable=self.microphone_var, state="readonly", width=30), current_row_std)
        current_row_std += 1

        # Speaker Selection
        self.speaker_var = tk.StringVar()
        self.speaker_label, self.speaker_combobox = create_setting_row(self.standard_settings_frame, "speaker_label", "speaker_tooltip",
            lambda sf: ttk.Combobox(sf, textvariable=self.speaker_var, state="readonly", width=30), current_row_std)
        current_row_std += 1

        # Active System Prompt
        self.active_prompt_name_var = tk.StringVar()
        def create_prompt_selector_std(sf):
            prompt_selection_frame = ttk.Frame(sf)
            prompt_selection_frame.columnconfigure(0, weight=1)
            self.prompt_combobox = ttk.Combobox(prompt_selection_frame, textvariable=self.active_prompt_name_var, state="readonly", width=30)
            self.prompt_combobox.grid(row=0, column=0, sticky="ew", padx=(0, 5))
            self.manage_prompts_button = ttk.Button(prompt_selection_frame, command=self.open_prompt_manager)
            self.manage_prompts_button.grid(row=0, column=1, sticky="e")
            return prompt_selection_frame
        self.active_prompt_label, _ = create_setting_row(self.standard_settings_frame, "active_system_prompt_label", "active_system_prompt_tooltip",
                                                         create_prompt_selector_std, current_row_std)
        current_row_std += 1


        # --- Fallback Agent Settings Group ---
        self.fallback_agent_settings_frame = ttk.LabelFrame(self.main_frame, padding=(15, 10))
        self.fallback_agent_settings_frame.pack(fill=tk.X, pady=(10, 10))
        self.fallback_agent_settings_frame.columnconfigure(2, weight=1)
        current_row_fallback = 0

        # Explanation text for fallback settings
        self.fallback_explanation_label = ttk.Label(self.fallback_agent_settings_frame, font=self.small_font, foreground="gray", wraplength=500)
        self.fallback_explanation_label.grid(row=current_row_fallback, column=0, columnspan=3, sticky="w", pady=(0,10), padx=0)
        current_row_fallback +=1

        # Fallback Activation Word
        self.activation_word_var = tk.StringVar()
        self.activation_word_label, _ = create_setting_row(self.fallback_agent_settings_frame, "activation_word_label", "activation_word_tooltip",
            lambda sf: ttk.Entry(sf, textvariable=self.activation_word_var), current_row_fallback)
        current_row_fallback += 1

        # Fallback Stop Words
        self.stop_words_var = tk.StringVar()
        self.stop_words_label, self.stop_words_entry_widget = create_setting_row(self.fallback_agent_settings_frame, "stop_words_label", "stop_words_tooltip",
            lambda sf: ttk.Entry(sf, textvariable=self.stop_words_var), current_row_fallback)
        current_row_fallback += 1
        self.stop_words_helper_label = ttk.Label(self.fallback_agent_settings_frame, font=self.small_font, foreground="gray")
        self.stop_words_helper_label.grid(row=current_row_fallback -1 , column=2, sticky="w", padx=(10,0), pady=(25,0))


        # Fallback Chat Length
        self.chat_length_var = tk.IntVar()
        self.chat_length_label, _ = create_setting_row(self.fallback_agent_settings_frame, "chat_length_label", "chat_length_tooltip",
            lambda sf: ttk.Spinbox(sf, from_=1, to=100, textvariable=self.chat_length_var, width=10), current_row_fallback)
        current_row_fallback += 1

        # Fallback Open Links Automatically
        self.open_links_var = tk.BooleanVar()
        self.open_links_label, self.open_links_checkbutton_widget = create_setting_row(self.fallback_agent_settings_frame, "open_links_label", "open_links_tooltip",
            lambda sf: ttk.Checkbutton(sf, variable=self.open_links_var), current_row_fallback)
        current_row_fallback += 1

        # Fallback TTS Voice Selection
        self.tts_language_var = tk.StringVar()
        self.tts_specific_voice_var = tk.StringVar()
        def create_tts_selector_widget_fallback(parent_frame):
            tts_frame = ttk.Frame(parent_frame)
            tts_frame.columnconfigure(0, weight=1); tts_frame.columnconfigure(1, weight=1)
            self.tts_language_combobox = ttk.Combobox(tts_frame, textvariable=self.tts_language_var, state="readonly", width=20)
            self.tts_language_combobox.grid(row=0, column=0, sticky="ew", padx=(0, 5))
            self.tts_language_combobox.bind("<<ComboboxSelected>>", self._on_tts_language_selected)
            self.tts_specific_voice_combobox = ttk.Combobox(tts_frame, textvariable=self.tts_specific_voice_var, state="disabled", width=20)
            self.tts_specific_voice_combobox.grid(row=0, column=1, sticky="ew", padx=(0, 5))
            self.preview_tts_button = ttk.Button(tts_frame, command=self._play_tts_preview, width=12, state="disabled")
            self.preview_tts_button.grid(row=0, column=2, sticky="e", padx=(0,0))
            return tts_frame
        self.tts_voice_label, _ = create_setting_row(self.fallback_agent_settings_frame, "tts_voice_label", "tts_voice_tooltip",
                                                     create_tts_selector_widget_fallback, current_row_fallback)
        current_row_fallback += 1


        # Separator and Buttons
        self.separator = ttk.Separator(self.main_frame, orient='horizontal')
        self.separator.pack(fill=tk.X, pady=(15, 10), side=tk.BOTTOM)

        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=(10, 0), side=tk.BOTTOM)

        self.save_button = ttk.Button(self.button_frame, command=self.save_and_close, style="Accent.TButton")
        self.save_button.pack(side=tk.RIGHT, padx=5)
        self.cancel_button_widget = ttk.Button(self.button_frame, command=self.cancel_and_close)
        self.cancel_button_widget.pack(side=tk.RIGHT, padx=5)


    def retranslate_ui(self):
        self.root.title(self.lm.get_string("settings_window_title"))
        self.header_label.configure(text=self.lm.get_string("settings_header"))

        # Group Titles
        self.standard_settings_frame.configure(text=self.lm.get_string("standard_settings_group_title", default_text="Standard Application Settings"))
        self.fallback_agent_settings_frame.configure(text=self.lm.get_string("fallback_agent_settings_group_title", default_text="Global Default Agent Settings (Fallbacks)"))
        self.fallback_explanation_label.configure(text=self.lm.get_string("fallback_agent_settings_explanation", default_text="These settings are used as defaults if an agent does not specify its own overrides in the Agent Builder."))


        # Standard Settings Labels
        self.api_key_label.configure(text=self.lm.get_string("api_key_label"))
        self.ui_language_label.configure(text=self.lm.get_string("ui_language_label"))
        self.microphone_label.configure(text=self.lm.get_string("microphone_label"))
        self.speaker_label.configure(text=self.lm.get_string("speaker_label"))
        self.active_prompt_label.configure(text=self.lm.get_string("active_system_prompt_label"))
        if hasattr(self, 'manage_prompts_button'):
            self.manage_prompts_button.configure(text=self.lm.get_string("manage_prompts_button"))

        # Fallback Agent Settings Labels
        self.chat_length_label.configure(text=self.lm.get_string("chat_length_label"))
        self.activation_word_label.configure(text=self.lm.get_string("activation_word_label"))
        self.stop_words_label.configure(text=self.lm.get_string("stop_words_label"))
        self.stop_words_helper_label.configure(text=self.lm.get_string("stop_words_helper"))
        self.open_links_label.configure(text=self.lm.get_string("open_links_label"))
        if hasattr(self, 'open_links_checkbutton_widget'):
            self.open_links_checkbutton_widget.configure(text=self.lm.get_string("open_links_checkbox_label"))
        self.tts_voice_label.configure(text=self.lm.get_string("tts_voice_label"))
        if hasattr(self, 'preview_tts_button'):
            self.preview_tts_button.configure(text=self.lm.get_string("tts_preview_button"))


        # Common UI elements
        system_default_translated = self.lm.get_string("system_default_device_option", default_text="System Default")
        if hasattr(self, 'microphone_combobox') and self.microphone_combobox.cget('values'):
            current_mic_selection = self.microphone_var.get()
            mic_values = list(self.microphone_combobox['values'])
            if mic_values and mic_values[0] != system_default_translated and current_mic_selection == mic_values[0]:
                self.microphone_var.set(system_default_translated)
            if mic_values: mic_values[0] = system_default_translated; self.microphone_combobox['values'] = mic_values
        if hasattr(self, 'speaker_combobox') and self.speaker_combobox.cget('values'):
            current_speaker_selection = self.speaker_var.get()
            speaker_values = list(self.speaker_combobox['values'])
            if speaker_values and speaker_values[0] != system_default_translated and current_speaker_selection == speaker_values[0]:
                self.speaker_var.set(system_default_translated)
            if speaker_values: speaker_values[0] = system_default_translated; self.speaker_combobox['values'] = speaker_values

        lang_display_names_ui = [f"{AVAILABLE_UI_LANGUAGES[code]['flag']} {AVAILABLE_UI_LANGUAGES[code]['name']}"
                                 for code in sorted(AVAILABLE_UI_LANGUAGES.keys(), key=lambda c: AVAILABLE_UI_LANGUAGES[c]['name'])]
        if hasattr(self, 'ui_language_combobox'): self.ui_language_combobox['values'] = lang_display_names_ui
        if hasattr(self, 'tts_language_combobox'): self.tts_language_combobox['values'] = self._get_sorted_tts_language_display_names()

        self.save_button.configure(text=self.lm.get_string("save_button"))
        self.cancel_button_widget.configure(text=self.lm.get_string("cancel_button"))

    def load_settings_into_ui(self):
        self.settings = load_settings()

        # Standard Settings
        self.api_key_var.set(self.settings.get("api_key", default_settings["api_key"]))
        current_ui_lang_code = self.settings.get("ui_language", default_settings["ui_language"])
        if not AVAILABLE_UI_LANGUAGES: scan_available_languages()
        if not self.ui_language_combobox['values']: # Populate if empty
            lang_display_names_ui = [f"{AVAILABLE_UI_LANGUAGES[code]['flag']} {AVAILABLE_UI_LANGUAGES[code]['name']}"
                                     for code in sorted(AVAILABLE_UI_LANGUAGES.keys(), key=lambda c: AVAILABLE_UI_LANGUAGES[c]['name'])]
            self.ui_language_combobox['values'] = lang_display_names_ui
        default_ui_info = AVAILABLE_UI_LANGUAGES.get("en-US", {"name": "English (US)", "flag": "🇺🇸"})
        lang_info = AVAILABLE_UI_LANGUAGES.get(current_ui_lang_code, default_ui_info)
        ui_display_to_set = f"{lang_info['flag']} {lang_info['name']}"
        if ui_display_to_set in self.ui_language_combobox['values']: self.ui_language_var.set(ui_display_to_set)
        elif self.ui_language_combobox['values']: self.ui_language_var.set(self.ui_language_combobox['values'][0])

        mic_names = self._get_microphone_names()
        self.microphone_combobox['values'] = mic_names
        current_mic_setting_value = self.settings.get("selected_microphone", default_settings["selected_microphone"])
        system_default_translated = self.lm.get_string("system_default_device_option", default_text="System Default")
        if current_mic_setting_value == "System Default": self.microphone_var.set(system_default_translated)
        elif current_mic_setting_value in mic_names: self.microphone_var.set(current_mic_setting_value)
        elif mic_names: self.microphone_var.set(mic_names[0])
        else: self.microphone_var.set(""); self.microphone_combobox.configure(state="disabled")

        speaker_names = self._get_speaker_names()
        self.speaker_combobox['values'] = speaker_names
        current_speaker_setting_value = self.settings.get("selected_speaker", default_settings["selected_speaker"])
        if current_speaker_setting_value == "System Default": self.speaker_var.set(system_default_translated)
        elif current_speaker_setting_value in speaker_names: self.speaker_var.set(current_speaker_setting_value)
        elif speaker_names: self.speaker_var.set(speaker_names[0])
        else: self.speaker_var.set(""); self.speaker_combobox.configure(state="disabled")

        self.refresh_prompt_options()
        current_active_prompt = self.settings.get("active_system_prompt_name", DEFAULT_SYSTEM_PROMPT_NAME)
        if current_active_prompt not in self.system_prompts: current_active_prompt = DEFAULT_SYSTEM_PROMPT_NAME
        self.active_prompt_name_var.set(current_active_prompt)

        # Fallback Agent Settings
        self.chat_length_var.set(self.settings.get("chat_length", default_settings["chat_length"]))
        self.activation_word_var.set(self.settings.get("activation_word", default_settings["activation_word"]))
        self.stop_words_var.set(", ".join(self.settings.get("stop_words", default_settings["stop_words"])))
        self.open_links_var.set(self.settings.get("open_links_automatically", default_settings["open_links_automatically"]))

        if not self.tts_language_combobox['values']:
            self.tts_language_combobox['values'] = self._get_sorted_tts_language_display_names()
        current_tts_voice_id = self.settings.get("tts_voice", default_settings["tts_voice"])
        selected_lang_display, selected_voice_name = None, None
        for lang_key, lang_data in TTS_VOICES_STRUCTURED.items():
            for voice_name_short, voice_id_val in lang_data["voices"].items():
                if voice_id_val == current_tts_voice_id:
                    selected_lang_display = f"{lang_data['flag']} {lang_key}"; selected_voice_name = voice_name_short; break
            if selected_lang_display: break
        if selected_lang_display and selected_lang_display in self.tts_language_combobox['values']:
            self.tts_language_var.set(selected_lang_display)
            self._update_tts_specific_voices_combobox()
            if selected_voice_name and selected_voice_name in self.tts_specific_voice_combobox['values']:
                self.tts_specific_voice_var.set(selected_voice_name)
        elif self.tts_language_combobox['values']:
            self.tts_language_var.set(self.tts_language_combobox['values'][0])
            self._update_tts_specific_voices_combobox()
        else:
            self.tts_language_var.set(""); self._update_tts_specific_voices_combobox()

    def show_help_tooltip(self, tooltip_key):
        message = self.lm.get_string(tooltip_key)
        title = self.lm.get_string("tooltip_title")
        messagebox.showinfo(title, message, parent=self.root)

    def on_language_change(self, event=None):
        selected_lang_display_name_with_flag = self.ui_language_var.get()
        new_lang_code, selected_lang_name_for_msg = "en-US", "English (US)"
        for code, lang_data in AVAILABLE_UI_LANGUAGES.items():
            if f"{lang_data['flag']} {lang_data['name']}" == selected_lang_display_name_with_flag:
                new_lang_code, selected_lang_name_for_msg = code, lang_data['name']; break
        if new_lang_code != self.lm.current_lang_code:
            self.lm.set_language(new_lang_code)
            stored_tts_lang_display = self.tts_language_var.get()
            stored_tts_voice_name = self.tts_specific_voice_var.get()
            self.retranslate_ui()
            self.load_settings_into_ui() # Re-applies settings to UI, handling translated defaults
            if stored_tts_lang_display in self.tts_language_combobox['values']: # Try to preserve TTS
                self.tts_language_var.set(stored_tts_lang_display)
                self._update_tts_specific_voices_combobox()
                if stored_tts_voice_name in self.tts_specific_voice_combobox['values']:
                    self.tts_specific_voice_var.set(stored_tts_voice_name)
            messagebox.showinfo(self.lm.get_string("language_change_applied_title"),
                                self.lm.get_string("language_change_applied_message", lang_name=selected_lang_name_for_msg),
                                parent=self.root)

    def refresh_prompt_options(self):
        self.system_prompts = agent_load_system_prompts(DEFAULT_SYSTEM_PROMPT_NAME, DEFAULT_SYSTEM_PROMPT_TEXT)
        prompt_names = sorted(list(self.system_prompts.keys()))
        current_selection = self.active_prompt_name_var.get()
        if hasattr(self, 'prompt_combobox'):
            self.prompt_combobox['values'] = prompt_names
            if current_selection in prompt_names: self.active_prompt_name_var.set(current_selection)
            elif DEFAULT_SYSTEM_PROMPT_NAME in prompt_names: self.active_prompt_name_var.set(DEFAULT_SYSTEM_PROMPT_NAME)
            elif prompt_names: self.active_prompt_name_var.set(prompt_names[0])
            else: self.active_prompt_name_var.set("")

    def open_prompt_manager(self):
        manager_window = SystemPromptManagerWindow(self.root, self, self.lm,
                                                   DEFAULT_SYSTEM_PROMPT_NAME,
                                                   DEFAULT_SYSTEM_PROMPT_TEXT)
        self.root.wait_window(manager_window)
        self.refresh_prompt_options()

    def center_window(self):
        self.root.update_idletasks()
        width, height = self.root.winfo_width(), self.root.winfo_height()
        min_w, min_h = self.root.minsize()
        width, height = max(width, min_w), max(height, min_h)
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def save_and_close(self):
        try: chat_length_val = self.chat_length_var.get()
        except tk.TclError:
            messagebox.showerror(self.lm.get_string("invalid_input_title"),
                                 self.lm.get_string("chat_length_integer_error"), parent=self.root); return
        if not isinstance(chat_length_val, int) or chat_length_val < 1:
            messagebox.showerror(self.lm.get_string("invalid_input_title"),
                                 self.lm.get_string("chat_length_positive_integer_error"), parent=self.root); return

        selected_lang_display_with_flag = self.tts_language_var.get()
        selected_voice_name_short = self.tts_specific_voice_var.get()
        final_tts_voice_id = default_settings["tts_voice"]
        if selected_lang_display_with_flag and selected_voice_name_short:
            target_lang_key = None
            for l_key, l_data in TTS_VOICES_STRUCTURED.items():
                if f"{l_data['flag']} {l_key}" == selected_lang_display_with_flag: target_lang_key = l_key; break
            if target_lang_key and target_lang_key in TTS_VOICES_STRUCTURED:
                lang_data_tts = TTS_VOICES_STRUCTURED[target_lang_key]
                if selected_voice_name_short in lang_data_tts["voices"]:
                    final_tts_voice_id = lang_data_tts["voices"][selected_voice_name_short]

        selected_ui_lang_display_with_flag = self.ui_language_var.get()
        ui_language_code = default_settings["ui_language"]
        for code, lang_data_ui in AVAILABLE_UI_LANGUAGES.items():
            if f"{lang_data_ui['flag']} {lang_data_ui['name']}" == selected_ui_lang_display_with_flag:
                ui_language_code = code; break

        selected_mic_display = self.microphone_var.get()
        final_selected_mic = default_settings["selected_microphone"]
        system_default_translated = self.lm.get_string("system_default_device_option", default_text="System Default")
        if selected_mic_display == system_default_translated: final_selected_mic = "System Default"
        elif selected_mic_display: final_selected_mic = selected_mic_display

        selected_speaker_display = self.speaker_var.get()
        final_selected_speaker = default_settings["selected_speaker"]
        if selected_speaker_display == system_default_translated: final_selected_speaker = "System Default"
        elif selected_speaker_display: final_selected_speaker = selected_speaker_display

        new_settings = {
            "api_key": self.api_key_var.get(),
            "ui_language": ui_language_code,
            "selected_microphone": final_selected_mic,
            "selected_speaker": final_selected_speaker,
            "active_system_prompt_name": self.active_prompt_name_var.get(),
            # Fallback settings
            "chat_length": chat_length_val,
            "activation_word": self.activation_word_var.get(),
            "stop_words": [word.strip() for word in self.stop_words_var.get().split(",") if word.strip()],
            "open_links_automatically": self.open_links_var.get(),
            "tts_voice": final_tts_voice_id,
        }

        current_saved_prompts = agent_load_system_prompts(DEFAULT_SYSTEM_PROMPT_NAME, DEFAULT_SYSTEM_PROMPT_TEXT)
        if not new_settings["active_system_prompt_name"] or \
           new_settings["active_system_prompt_name"] not in current_saved_prompts:
            new_settings["active_system_prompt_name"] = DEFAULT_SYSTEM_PROMPT_NAME

        if save_settings(new_settings, self.lm):
            self.root.destroy()

    def cancel_and_close(self):
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        initial_settings_for_lm = load_settings()
        lm_standalone = LanguageManager(initial_settings_for_lm.get("ui_language", default_settings["ui_language"]))
        if not pygame.mixer.get_init():
            try: pygame.mixer.init()
            except pygame.error as e: print(f"Pygame mixer could not be initialized (standalone settings): {e}")
        app = ModernSettingsApp(root, lm=lm_standalone)
    except NameError as e:
        if 'sv_ttk' in str(e).lower():
            print(f"Error initializing ModernSettingsApp (likely sv_ttk missing or import error): {e}")
            root.title("Bot Settings (Basic Fallback)")
            ttk.Label(root, text="Error loading modern theme. sv_ttk might be missing. Basic fallback UI.").pack(pady=20)
        else:
            print(f"A NameError occurred: {e}")
            root.title("Bot Settings (Error)")
            ttk.Label(root, text=f"Could not initialize settings UI (NameError): {e}").pack(pady=20)
        ttk.Button(root, text="Close", command=root.destroy).pack(pady=10)
    except Exception as e:
        print(f"An unexpected error occurred initializing ModernSettingsApp: {e}")
        import traceback; traceback.print_exc()
        root.title("Bot Settings (Error)")
        ttk.Label(root, text=f"Could not initialize settings UI: {e}").pack(pady=20)
        ttk.Button(root, text="Close", command=root.destroy).pack(pady=10)

    root.mainloop()
    if pygame.mixer.get_init(): pygame.mixer.quit()