# C:/Users/Theminemat/Documents/Programming/manfred desktop ai/settings.py
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter.font import Font
from tkinter.scrolledtext import ScrolledText
import sv_ttk
import sys
import re  # Added for parsing display names if needed, though direct structure is preferred
import asyncio  # Added for TTS preview
from threading import Thread  # Added for TTS preview
from edge_tts import Communicate  # Added for TTS preview
import pygame  # Added for TTS preview playback
import time  # Added for TTS preview playback

# --- Mock speech_recognition for testing if not installed (for settings.py standalone) ---
try:
    import speech_recognition as sr_audio
except ImportError:
    print("WARNING (settings.py): speech_recognition not found. Using mock for microphone listing.")


    class MockRecognizerSettings:
        pass  # Different name to avoid conflict if main.py mock is somehow imported


    class MockMicrophoneSettings:
        @staticmethod
        def list_microphone_names():
            print("Mock list_microphone_names called from settings.py")
            # Simulate some microphone names
            return ["Mock Microphone 1 (Settings)", "Another Mock Mic (Settings)", "System Default Mock Mic (Settings)"]


    class MockSrAudioModule:  # Different name
        Recognizer = MockRecognizerSettings
        Microphone = MockMicrophoneSettings
        WaitTimeoutError = type('WaitTimeoutError', (Exception,), {})
        UnknownValueError = type('UnknownValueError', (Exception,), {})
        RequestError = type('RequestError', (Exception,), {})


    sr_audio = MockSrAudioModule()
# --- End Mock ---


SETTINGS_FILE = "settings.json"
SYSPROMPTS_FILE = "sysprompts.json"
LANGUAGES_DIR = "languages"

DEFAULT_SYSTEM_PROMPT_NAME = "Default Manfred Prompt"
DEFAULT_SYSTEM_PROMPT_TEXT = (
    "You are Manfred, a highly intelligent and efficient AI assistant. "
    "Reply without formatting and keep replies short and simple. "
    "You always speak respectfully, and fluent English. "
    "Your responses must be clear, concise, and helpful—avoid unnecessary elaboration, especially for simple tasks. "
    "A good amount of humor is good to keep the conversation natural, friend-like. Your top priorities are efficiency and clarity."
)
SYSTEM_PROMPT_SUFFIX = (
    "\n\nGenerate the reply so that a simple TTS can read it correctly. "
    "\nYou can open links on my PC by just including them in your message without formatting; "
    "just start links with https://. Also use this when the user asks you to search on a website like YouTube."
)

default_settings = {
    "api_key": "Enter your Gemini API key here",
    "chat_length": 5,
    "activation_word": "Manfred",
    "stop_words": ["stop", "stopp" "exit", "quit"],
    "open_links_automatically": True,
    "active_system_prompt_name": DEFAULT_SYSTEM_PROMPT_NAME,
    "ui_language": "en-US",
    "tts_voice": "en-US-AriaNeural",  # Default voice ID
    "selected_microphone": "System Default",  # New setting
    "selected_speaker": "System Default"  # New setting
}

# New structured TTS voices
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
                if lang_code == "en-US":
                    display_name = "English (US)"
                    flag = "🇺🇸"
                elif lang_code == "de-DE":
                    display_name = "Deutsch (German)"
                    flag = "🇩🇪"
                elif lang_code == "fr-FR":
                    display_name = "Français"
                    flag = "🇫🇷"
                AVAILABLE_UI_LANGUAGES[lang_code] = {"name": display_name, "flag": flag}
            except Exception as e:
                print(f"Error processing language file {filename}: {e}")
                AVAILABLE_UI_LANGUAGES[lang_code] = {"name": lang_code, "flag": "🏳️"}

    if not AVAILABLE_UI_LANGUAGES:
        AVAILABLE_UI_LANGUAGES["en-US"] = {"name": "English (US)", "flag": "🇺🇸"}


scan_available_languages()


def load_system_prompts():
    if not os.path.exists(SYSPROMPTS_FILE):
        try:
            with open(SYSPROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump({DEFAULT_SYSTEM_PROMPT_NAME: DEFAULT_SYSTEM_PROMPT_TEXT}, f, indent=4, ensure_ascii=False)
            print(f"'{SYSPROMPTS_FILE}' not found. Created with default system prompt.")
            return {DEFAULT_SYSTEM_PROMPT_NAME: DEFAULT_SYSTEM_PROMPT_TEXT}
        except Exception as e:
            print(f"Error creating default system prompts file: {e}")
            return {DEFAULT_SYSTEM_PROMPT_NAME: DEFAULT_SYSTEM_PROMPT_TEXT}

    try:
        with open(SYSPROMPTS_FILE, "r", encoding="utf-8") as f:
            prompts = json.load(f)
            if not isinstance(prompts, dict) or not prompts:
                raise ValueError("Invalid format or empty prompts file.")
            if DEFAULT_SYSTEM_PROMPT_NAME not in prompts:
                prompts[DEFAULT_SYSTEM_PROMPT_NAME] = DEFAULT_SYSTEM_PROMPT_TEXT
                save_system_prompts(prompts, None)
                print(f"Default system prompt was missing from '{SYSPROMPTS_FILE}'. Added and saved.")
            return prompts
    except Exception as e:
        print(f"Error loading system prompts: {e}. Returning default prompt.")
        return {DEFAULT_SYSTEM_PROMPT_NAME: DEFAULT_SYSTEM_PROMPT_TEXT}


def save_system_prompts(prompts_dict, lm):
    try:
        with open(SYSPROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(prompts_dict, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        if lm:
            messagebox.showerror(lm.get_string("error_title"), lm.get_string("failed_to_save_prompts_error", e=e))
        else:
            messagebox.showerror("Error", f"Failed to save system prompts:\n{e}")
        return False


def get_full_system_prompt(prompt_name, all_prompts, activation_word):
    base_text = all_prompts.get(prompt_name, DEFAULT_SYSTEM_PROMPT_TEXT)
    base_text = base_text.replace("{name}", activation_word)
    return base_text + SYSTEM_PROMPT_SUFFIX


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
                print(f"'{SETTINGS_FILE}' was missing some keys. Updated with defaults.")
            return loaded
    except Exception as e:
        print(f"Error loading settings: {e}. Returning default settings.")
        return default_settings.copy()


def save_settings(settings, lm):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        if lm:
            messagebox.showinfo(lm.get_string("success_title"), lm.get_string("settings_saved_success"))
        return True
    except Exception as e:
        if lm:
            messagebox.showerror(lm.get_string("error_title"), lm.get_string("failed_to_save_settings_error", e=e))
        else:
            messagebox.showerror("Error", f"Failed to save settings:\n{e}")
        return False


class SystemPromptManagerWindow(tk.Toplevel):
    def __init__(self, master_widget, app_instance, lm):
        super().__init__(master_widget)
        self.parent_app = app_instance
        self.lm = lm

        self.grab_set()
        self.prompts_dict = load_system_prompts()

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(main_frame, padding=(0, 0, 10, 0))
        left_panel.pack(side=tk.LEFT, fill=tk.Y)

        self.prompts_list_label = ttk.Label(left_panel, font=self.parent_app.label_font)
        self.prompts_list_label.pack(anchor="w", pady=(0, 5))
        self.prompts_listbox = tk.Listbox(left_panel, exportselection=False, height=15)
        self.prompts_listbox.pack(fill=tk.BOTH, expand=True)
        self.prompts_listbox.bind("<<ListboxSelect>>", self.on_prompt_select)

        list_actions_frame = ttk.Frame(left_panel)
        list_actions_frame.pack(fill=tk.X, pady=5)

        self.new_button = ttk.Button(list_actions_frame, command=self.new_prompt)
        self.new_button.pack(side=tk.LEFT, padx=2)
        self.duplicate_button = ttk.Button(list_actions_frame, command=self.duplicate_prompt)
        self.duplicate_button.pack(side=tk.LEFT, padx=2)
        self.delete_button = ttk.Button(list_actions_frame, command=self.delete_prompt)
        self.delete_button.pack(side=tk.LEFT, padx=2)

        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.prompt_name_label_widget = ttk.Label(right_panel, font=self.parent_app.label_font)
        self.prompt_name_label_widget.pack(anchor="w", pady=(0, 2))
        self.prompt_name_var = tk.StringVar()
        self.prompt_name_entry = ttk.Entry(right_panel, textvariable=self.prompt_name_var, state=tk.DISABLED)
        self.prompt_name_entry.pack(fill=tk.X, pady=(0, 10))

        self.prompt_text_label_widget = ttk.Label(right_panel, font=self.parent_app.label_font)
        self.prompt_text_label_widget.pack(anchor="w", pady=(0, 2))
        self.prompt_text_widget = ScrolledText(right_panel, wrap=tk.WORD, height=10, state=tk.DISABLED, relief=tk.SOLID,
                                               borderwidth=1)
        self.prompt_text_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.style_scrolled_text()

        edit_actions_frame = ttk.Frame(right_panel)
        edit_actions_frame.pack(fill=tk.X, pady=5)
        self.save_button = ttk.Button(edit_actions_frame, command=self.save_edited_prompt, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=2)
        self.cancel_button = ttk.Button(edit_actions_frame, command=self.cancel_edit, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=2)

        bottom_frame = ttk.Frame(self, padding=10)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.close_manager_button = ttk.Button(bottom_frame, command=self.close_manager, style="Accent.TButton")
        self.close_manager_button.pack(side=tk.RIGHT)

        self.retranslate_ui()
        self.populate_prompts_listbox()
        self.selected_prompt_original_name = None
        self.protocol("WM_DELETE_WINDOW", self.close_manager)

    def style_scrolled_text(self):
        style = ttk.Style()
        bg_color_text_widget, fg_color_text_widget = "", ""
        try:
            bg_color_text_widget = style.lookup('TEntry', 'fieldbackground')
            fg_color_text_widget = style.lookup('TEntry', 'foreground')
            if not bg_color_text_widget: bg_color_text_widget = style.lookup('TFrame', 'background') or "white"
            if not fg_color_text_widget: fg_color_text_widget = style.lookup('TFrame', 'foreground') or "black"
            self.prompt_text_widget.configure(bg=bg_color_text_widget, fg=fg_color_text_widget,
                                              insertbackground=fg_color_text_widget)
        except Exception as e:
            print(f"Error styling ScrolledText: {e}. Using defaults.")
            safe_bg, safe_fg = (
                "#2b2b2b", "#cccccc") if 'sv_ttk' in sys.modules and sv_ttk.get_theme().lower() == "dark" else (
                "white", "black")
            self.prompt_text_widget.configure(bg=safe_bg, fg=safe_fg, insertbackground=safe_fg)

    def retranslate_ui(self):
        self.title(self.lm.get_string("prompt_manager_title"))
        self.prompts_list_label.configure(text=self.lm.get_string("prompts_list_label"))
        self.new_button.configure(text=self.lm.get_string("new_prompt_button"))
        self.duplicate_button.configure(text=self.lm.get_string("duplicate_prompt_button"))
        self.delete_button.configure(text=self.lm.get_string("delete_prompt_button"))
        self.prompt_name_label_widget.configure(text=self.lm.get_string("prompt_name_label"))
        self.prompt_text_label_widget.configure(text=self.lm.get_string("prompt_text_label"))
        self.save_button.configure(text=self.lm.get_string("save_changes_button"))
        self.cancel_button.configure(text=self.lm.get_string("cancel_edit_button"))
        self.close_manager_button.configure(text=self.lm.get_string("close_manager_button"))
        if self.save_button.cget("text") != self.lm.get_string("save_changes_button") and \
                self.selected_prompt_original_name is None:
            self.save_button.configure(text=self.lm.get_string("save_new_prompt_button"))

    def populate_prompts_listbox(self):
        self.prompts_listbox.delete(0, tk.END)
        for name in sorted(self.prompts_dict.keys()):
            self.prompts_listbox.insert(tk.END, name)
        self.disable_editing_fields()

    def on_prompt_select(self, event=None):
        if not self.prompts_listbox.curselection():
            self.disable_editing_fields()
            return
        selected_index = self.prompts_listbox.curselection()[0]
        prompt_name = self.prompts_listbox.get(selected_index)
        self.selected_prompt_original_name = prompt_name
        self.prompt_name_var.set(prompt_name)
        self.prompt_text_widget.configure(state=tk.NORMAL)
        self.prompt_text_widget.delete("1.0", tk.END)
        self.prompt_text_widget.insert("1.0", self.prompts_dict.get(prompt_name, ""))
        self.enable_editing_fields()
        if prompt_name == DEFAULT_SYSTEM_PROMPT_NAME:
            self.prompt_name_entry.configure(state=tk.DISABLED)
        else:
            self.prompt_name_entry.configure(state=tk.NORMAL)
        self.save_button.configure(text=self.lm.get_string("save_changes_button"))

    def enable_editing_fields(self):
        self.prompt_name_entry.configure(state=tk.NORMAL)
        self.prompt_text_widget.configure(state=tk.NORMAL)
        self.save_button.configure(state=tk.NORMAL)
        self.cancel_button.configure(state=tk.NORMAL)

    def disable_editing_fields(self):
        self.prompt_name_var.set("")
        self.prompt_text_widget.delete("1.0", tk.END)
        self.prompt_name_entry.configure(state=tk.DISABLED)
        self.prompt_text_widget.configure(state=tk.DISABLED)
        self.save_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.DISABLED)
        self.selected_prompt_original_name = None

    def new_prompt(self):
        self.prompts_listbox.selection_clear(0, tk.END)
        self.selected_prompt_original_name = None
        self.prompt_name_var.set(self.lm.get_string("new_prompt_default_name", default_text="New Prompt Name"))
        self.prompt_text_widget.configure(state=tk.NORMAL)
        self.prompt_text_widget.delete("1.0", tk.END)
        self.prompt_text_widget.insert("1.0", self.lm.get_string("new_prompt_default_text",
                                                                 default_text="Enter prompt text here..."))
        self.enable_editing_fields()
        self.prompt_name_entry.focus()
        self.save_button.configure(text=self.lm.get_string("save_new_prompt_button"))

    def save_edited_prompt(self):
        new_name = self.prompt_name_var.get().strip()
        text = self.prompt_text_widget.get("1.0", tk.END).strip()

        if not new_name:
            messagebox.showerror(self.lm.get_string("error_title"), self.lm.get_string("prompt_name_empty_error"),
                                 parent=self)
            return
        if not text:
            messagebox.showerror(self.lm.get_string("error_title"), self.lm.get_string("prompt_text_empty_error"),
                                 parent=self)
            return

        is_new_prompt = self.selected_prompt_original_name is None
        is_renaming = not is_new_prompt and new_name != self.selected_prompt_original_name

        if is_new_prompt or is_renaming:
            if new_name in self.prompts_dict:
                messagebox.showerror(self.lm.get_string("error_title"),
                                     self.lm.get_string("prompt_name_exists_error", new_name=new_name), parent=self)
                return
            if is_renaming:
                if self.selected_prompt_original_name == DEFAULT_SYSTEM_PROMPT_NAME:
                    messagebox.showerror(self.lm.get_string("error_title"),
                                         self.lm.get_string("cannot_rename_default_prompt_error"), parent=self)
                    self.prompt_name_var.set(DEFAULT_SYSTEM_PROMPT_NAME)
                    return
                del self.prompts_dict[self.selected_prompt_original_name]
        elif self.selected_prompt_original_name == DEFAULT_SYSTEM_PROMPT_NAME and new_name != DEFAULT_SYSTEM_PROMPT_NAME:
            messagebox.showerror(self.lm.get_string("error_title"),
                                 self.lm.get_string("cannot_rename_default_prompt_error"), parent=self)
            self.prompt_name_var.set(DEFAULT_SYSTEM_PROMPT_NAME)
            return

        self.prompts_dict[new_name] = text
        self.populate_prompts_listbox()
        try:
            idx = list(sorted(self.prompts_dict.keys())).index(new_name)
            self.prompts_listbox.selection_set(idx)
            self.prompts_listbox.see(idx)
            self.on_prompt_select()
        except ValueError:
            self.disable_editing_fields()

        messagebox.showinfo(self.lm.get_string("success_title"),
                            self.lm.get_string("prompt_saved_success", new_name=new_name), parent=self)

    def cancel_edit(self):
        if self.selected_prompt_original_name:
            self.on_prompt_select()
        else:
            self.disable_editing_fields()

    def delete_prompt(self):
        if not self.prompts_listbox.curselection():
            messagebox.showwarning(self.lm.get_string("warning_title"),
                                   self.lm.get_string("no_prompt_selected_delete_warning"), parent=self)
            return
        selected_index = self.prompts_listbox.curselection()[0]
        prompt_name = self.prompts_listbox.get(selected_index)
        if prompt_name == DEFAULT_SYSTEM_PROMPT_NAME:
            messagebox.showerror(self.lm.get_string("error_title"),
                                 self.lm.get_string("cannot_delete_default_prompt_error"), parent=self)
            return
        if messagebox.askyesno(self.lm.get_string("confirm_delete_prompt_title"),
                               self.lm.get_string("confirm_delete_prompt_message", prompt_name=prompt_name),
                               parent=self):
            if prompt_name in self.prompts_dict:
                del self.prompts_dict[prompt_name]
                self.populate_prompts_listbox()
                self.disable_editing_fields()
                messagebox.showinfo(self.lm.get_string("success_title"),
                                    self.lm.get_string("prompt_deleted_success", prompt_name=prompt_name), parent=self)
                if self.parent_app.active_prompt_name_var.get() == prompt_name:
                    self.parent_app.active_prompt_name_var.set(DEFAULT_SYSTEM_PROMPT_NAME)
                    self.parent_app.settings[
                        "active_system_prompt_name"] = DEFAULT_SYSTEM_PROMPT_NAME

    def duplicate_prompt(self):
        if not self.prompts_listbox.curselection():
            messagebox.showwarning(self.lm.get_string("warning_title"),
                                   self.lm.get_string("no_prompt_selected_duplicate_warning"), parent=self)
            return
        selected_index = self.prompts_listbox.curselection()[0]
        original_name = self.prompts_listbox.get(selected_index)
        original_text = self.prompts_dict.get(original_name)
        if original_text is None: return

        copy_suffix = self.lm.get_string("prompt_copy_suffix", default_text=" (copy)")
        copy_num_suffix_template = self.lm.get_string("prompt_copy_num_suffix", default_text=" (copy {num})")

        copy_num = 1
        new_name = f"{original_name}{copy_suffix}"
        while new_name in self.prompts_dict:
            copy_num += 1
            new_name = f"{original_name}{copy_num_suffix_template.format(num=copy_num)}"

        self.prompts_dict[new_name] = original_text
        self.populate_prompts_listbox()
        try:
            idx = list(sorted(self.prompts_dict.keys())).index(new_name)
            self.prompts_listbox.selection_set(idx)
            self.prompts_listbox.see(idx)
            self.on_prompt_select()
        except ValueError:
            pass
        messagebox.showinfo(self.lm.get_string("success_title"),
                            self.lm.get_string("prompt_duplicated_success", original_name=original_name,
                                               new_name=new_name), parent=self)

    def close_manager(self):
        if save_system_prompts(self.prompts_dict, self.lm):
            self.parent_app.refresh_prompt_options()
            self.destroy()


class ModernSettingsApp:
    def __init__(self, root, lm):
        self.root = root
        self.settings = load_settings()
        self.lm = lm

        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()  # Initialize here for device listing
            except pygame.error as e:
                print(f"Warning: Pygame mixer could not be initialized in settings: {e}")

        try:
            icon_path = "icon.ico"
            if os.path.exists(icon_path): self.root.iconbitmap(default=icon_path)
        except Exception as e:
            print(f"Warning: Could not set icon: {e}")

        self.root.minsize(600, 750)  # Increased min height for new settings

        try:
            sv_ttk.set_theme("dark")
        except Exception:
            print("Warning: sv_ttk theme failed. Using default.")

        self.header_font = Font(family="Segoe UI", size=16, weight="bold")
        self.label_font = Font(family="Segoe UI", size=10)

        self.system_prompts = load_system_prompts()

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
            if not pygame.mixer.get_init():  # Ensure mixer is initialized
                pygame.mixer.init()

            if pygame.mixer.get_init():  # Check again
                num_devices = pygame.mixer.get_num_output_devices()
                for i in range(num_devices):
                    name = pygame.mixer.get_output_device_name(i)
                    if name:  # Pygame can return bytes or str
                        decoded_name = name.decode('utf-8', errors='replace') if isinstance(name, bytes) else name
                        if decoded_name.strip():  # Ensure not empty after decoding
                            names.append(decoded_name)
            else:
                print("Pygame mixer could not be initialized. Cannot list speaker devices.")
        except Exception as e:
            print(f"Error listing speaker devices: {e}")
        return names

    def _get_microphone_names(self):
        names = [self.lm.get_string("system_default_device_option", default_text="System Default")]
        try:
            if sr_audio and hasattr(sr_audio, 'Microphone') and hasattr(sr_audio.Microphone, 'list_microphone_names'):
                mic_names = sr_audio.Microphone.list_microphone_names()
                if mic_names:  # Ensure it's not None or empty
                    names.extend(m for m in mic_names if m and m.strip())  # Add only non-empty names
            else:
                print("Cannot list microphones: speech_recognition library not available or incomplete.")
        except Exception as e:
            print(f"Error listing microphone devices: {e}")
        return names

    def _get_sorted_tts_language_display_names(self):
        ui_lang_code = self.lm.current_lang_code
        ui_tts_lang_key = None

        for lang_key, lang_data in TTS_VOICES_STRUCTURED.items():
            if lang_data["code"] == ui_lang_code:
                ui_tts_lang_key = lang_key
                break

        english_keys = [k for k, data in TTS_VOICES_STRUCTURED.items() if data["code"].startswith("en-")]
        sorted_keys = []
        if ui_tts_lang_key:
            sorted_keys.append(ui_tts_lang_key)
        for eng_key in sorted(english_keys):
            if eng_key not in sorted_keys:
                sorted_keys.append(eng_key)
        for lang_key in sorted(TTS_VOICES_STRUCTURED.keys()):
            if lang_key not in sorted_keys:
                sorted_keys.append(lang_key)
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
                if f"{l_data['flag']} {l_key}" == selected_lang_display_with_flag:
                    target_lang_key = l_key
                    break
            if target_lang_key and target_lang_key in TTS_VOICES_STRUCTURED:
                voice_names = sorted(list(TTS_VOICES_STRUCTURED[target_lang_key]["voices"].keys()))

        current_specific_voice = self.tts_specific_voice_var.get()
        self.tts_specific_voice_combobox['values'] = voice_names

        if voice_names:
            if current_specific_voice in voice_names:
                self.tts_specific_voice_var.set(current_specific_voice)
            else:
                self.tts_specific_voice_var.set(voice_names[0])
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
            messagebox.showwarning(
                self.lm.get_string("warning_title"),
                self.lm.get_string("select_language_voice_warning",
                                   default_text="Please select a language and a voice first for preview."),
                parent=self.root
            )
            return

        voice_id_to_preview = None
        preview_text_for_tts = "Voice preview."
        target_lang_key = None

        for l_key, l_data_tts in TTS_VOICES_STRUCTURED.items():
            if f"{l_data_tts['flag']} {l_key}" == selected_lang_display_with_flag:
                target_lang_key = l_key
                break

        if target_lang_key:
            lang_data = TTS_VOICES_STRUCTURED[target_lang_key]
            if selected_voice_name_short in lang_data["voices"]:
                voice_id_to_preview = lang_data["voices"][selected_voice_name_short]
            preview_text_for_tts = lang_data.get("preview_text", preview_text_for_tts)

        if not voice_id_to_preview:
            messagebox.showerror(
                self.lm.get_string("error_title"),
                self.lm.get_string("could_not_find_voice_id_error",
                                   default_text="Could not find the ID for the selected voice."),
                parent=self.root
            )
            return

        self.preview_tts_button.configure(state=tk.DISABLED)

        def _do_preview_thread():
            temp_file = "tts_preview_temp.mp3"
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                communicate_obj = Communicate(text=preview_text_for_tts, voice=voice_id_to_preview)

                async def save_audio():
                    await communicate_obj.save(temp_file)

                loop.run_until_complete(save_audio())

                if os.path.exists(temp_file) and pygame.mixer.get_init():
                    pygame.mixer.music.load(temp_file)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)
                    pygame.mixer.music.unload()
                    time.sleep(0.1)
                    os.remove(temp_file)
                elif not pygame.mixer.get_init():
                    print("Pygame mixer not initialized, cannot play preview.")
            except Exception as e:
                print(f"Error during TTS preview: {e}")
                self.root.after(0, lambda: messagebox.showerror(
                    self.lm.get_string("error_title"),
                    self.lm.get_string("preview_failed_error", default_text="Preview failed: {e}", e=str(e)),
                    parent=self.root
                ))
            finally:
                self.root.after(0, lambda: self.preview_tts_button.configure(state=tk.NORMAL))
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as e_rem:
                        print(f"Error removing temp preview file: {e_rem}")

        Thread(target=_do_preview_thread, daemon=True).start()

    def build_ui(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        self.header_frame = ttk.Frame(self.main_frame)
        self.header_frame.pack(fill=tk.X, pady=(0, 20))
        self.header_label = ttk.Label(self.header_frame, font=self.header_font)
        self.header_label.pack(side=tk.LEFT)

        self.settings_frame = ttk.LabelFrame(self.main_frame, padding=(15, 10))
        self.settings_frame.pack(fill=tk.BOTH, expand=True)
        self.settings_frame.columnconfigure(2, weight=1)
        self.settings_frame.columnconfigure(0, weight=0)
        self.settings_frame.columnconfigure(1, weight=0)

        current_row = 0

        def create_setting_row(label_key, tooltip_key, widget_creator_func, row):
            label = ttk.Label(self.settings_frame, font=self.label_font)
            label.grid(row=row, column=0, sticky="w", pady=5, padx=(0, 2))
            help_button = ttk.Button(self.settings_frame, text="?", width=2, style="Help.TButton",
                                     command=lambda tk_key=tooltip_key: self.show_help_tooltip(tk_key))
            help_button.grid(row=row, column=1, sticky="w", padx=(0, 5))
            widget_container = widget_creator_func(self.settings_frame)
            if isinstance(widget_container, tuple) and len(widget_container) == 2 and isinstance(widget_container[0],
                                                                                                 tk.Widget):
                widget, grid_options = widget_container
                default_grid_options = {"sticky": "ew", "padx": (5, 0), "pady": 5}
                final_grid_options = {**default_grid_options, **grid_options}
                widget.grid(row=row, column=2, **final_grid_options)
            elif isinstance(widget_container, tk.Widget):
                widget = widget_container
                widget.grid(row=row, column=2, sticky="ew", padx=(5, 0), pady=5)
            else:
                widget = widget_container
                widget.grid(row=row, column=2, sticky="ew", padx=(5, 0), pady=5)
            return label, widget

        self.api_key_var = tk.StringVar()
        self.api_key_label, _ = create_setting_row("api_key_label", "api_key_tooltip",
                                                   lambda sf: ttk.Entry(sf, textvariable=self.api_key_var, width=40),
                                                   current_row);
        current_row += 1

        self.chat_length_var = tk.IntVar()
        self.chat_length_label, _ = create_setting_row("chat_length_label", "chat_length_tooltip",
                                                       lambda sf: ttk.Spinbox(sf, from_=1, to=100,
                                                                              textvariable=self.chat_length_var,
                                                                              width=10), current_row);
        current_row += 1

        self.activation_word_var = tk.StringVar()
        self.activation_word_label, _ = create_setting_row("activation_word_label", "activation_word_tooltip",
                                                           lambda sf: ttk.Entry(sf,
                                                                                textvariable=self.activation_word_var),
                                                           current_row);
        current_row += 1

        self.stop_words_var = tk.StringVar()
        self.stop_words_label, _ = create_setting_row("stop_words_label", "stop_words_tooltip",
                                                      lambda sf: ttk.Entry(sf, textvariable=self.stop_words_var),
                                                      current_row);
        current_row += 1
        self.stop_words_helper_label = ttk.Label(self.settings_frame, font=("Segoe UI", 8), foreground="gray")
        self.stop_words_helper_label.grid(row=current_row - 1, column=2, sticky="w", padx=(10, 0),
                                          pady=(25, 0))  # Adjusted position

        self.open_links_var = tk.BooleanVar()
        self.open_links_label, self.open_links_checkbutton_widget = create_setting_row(
            "open_links_label", "open_links_tooltip",
            lambda sf: ttk.Checkbutton(sf, variable=self.open_links_var), current_row);
        current_row += 1

        self.active_prompt_name_var = tk.StringVar()

        def create_prompt_selector(sf):
            prompt_selection_frame = ttk.Frame(sf)
            prompt_selection_frame.columnconfigure(0, weight=1)
            self.prompt_combobox = ttk.Combobox(prompt_selection_frame, textvariable=self.active_prompt_name_var,
                                                state="readonly", width=30)
            self.prompt_combobox.grid(row=0, column=0, sticky="ew", padx=(0, 5))
            self.manage_prompts_button = ttk.Button(prompt_selection_frame, command=self.open_prompt_manager)
            self.manage_prompts_button.grid(row=0, column=1, sticky="e")
            return prompt_selection_frame

        self.active_prompt_label, _ = create_setting_row("active_system_prompt_label", "active_system_prompt_tooltip",
                                                         create_prompt_selector, current_row);
        current_row += 1

        self.tts_language_var = tk.StringVar()
        self.tts_specific_voice_var = tk.StringVar()

        def create_tts_selector_widget(parent_frame):
            tts_frame = ttk.Frame(parent_frame)
            tts_frame.columnconfigure(0, weight=1);
            tts_frame.columnconfigure(1, weight=1)
            self.tts_language_combobox = ttk.Combobox(tts_frame, textvariable=self.tts_language_var,
                                                      state="readonly", width=20)
            self.tts_language_combobox.grid(row=0, column=0, sticky="ew", padx=(0, 5))
            self.tts_language_combobox.bind("<<ComboboxSelected>>", self._on_tts_language_selected)
            self.tts_specific_voice_combobox = ttk.Combobox(tts_frame, textvariable=self.tts_specific_voice_var,
                                                            state="disabled", width=20)
            self.tts_specific_voice_combobox.grid(row=0, column=1, sticky="ew", padx=(0, 5))
            self.preview_tts_button = ttk.Button(tts_frame, command=self._play_tts_preview,
                                                 width=12, state="disabled")
            self.preview_tts_button.grid(row=0, column=2, sticky="e", padx=(0, 0))
            return tts_frame

        self.tts_voice_label, _ = create_setting_row("tts_voice_label", "tts_voice_tooltip",
                                                     create_tts_selector_widget, current_row);
        current_row += 1

        # --- Microphone Selection ---
        self.microphone_var = tk.StringVar()
        self.microphone_label, self.microphone_combobox = create_setting_row(
            "microphone_label", "microphone_tooltip",
            lambda sf: ttk.Combobox(sf, textvariable=self.microphone_var, state="readonly", width=30),
            current_row);
        current_row += 1

        # --- Speaker Selection ---
        self.speaker_var = tk.StringVar()
        self.speaker_label, self.speaker_combobox = create_setting_row(
            "speaker_label", "speaker_tooltip",
            lambda sf: ttk.Combobox(sf, textvariable=self.speaker_var, state="readonly", width=30),
            current_row);
        current_row += 1

        self.ui_language_var = tk.StringVar()
        self.ui_language_label, self.ui_language_combobox = create_setting_row("ui_language_label",
                                                                               "ui_language_tooltip",
                                                                               lambda sf: ttk.Combobox(sf,
                                                                                                       textvariable=self.ui_language_var,
                                                                                                       state="readonly",
                                                                                                       width=30),
                                                                               current_row);
        current_row += 1
        self.ui_language_combobox.bind("<<ComboboxSelected>>", self.on_language_change)

        self.separator = ttk.Separator(self.main_frame, orient='horizontal')
        self.separator.pack(fill=tk.X, pady=(10, 10), side=tk.BOTTOM)
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=(10, 0), side=tk.BOTTOM)
        self.save_button = ttk.Button(self.button_frame, command=self.save_and_close, style="Accent.TButton")
        self.save_button.pack(side=tk.RIGHT, padx=5)
        self.cancel_button_widget = ttk.Button(self.button_frame, command=self.cancel_and_close)
        self.cancel_button_widget.pack(side=tk.RIGHT, padx=5)

    def retranslate_ui(self):
        self.root.title(self.lm.get_string("settings_window_title"))
        self.header_label.configure(text=self.lm.get_string("settings_header"))
        self.settings_frame.configure(text=self.lm.get_string("settings_group_label"))

        self.api_key_label.configure(text=self.lm.get_string("api_key_label"))
        self.chat_length_label.configure(text=self.lm.get_string("chat_length_label"))
        self.activation_word_label.configure(text=self.lm.get_string("activation_word_label"))
        self.stop_words_label.configure(text=self.lm.get_string("stop_words_label"))
        self.stop_words_helper_label.configure(text=self.lm.get_string("stop_words_helper"))
        self.open_links_label.configure(text=self.lm.get_string("open_links_label"))
        if hasattr(self, 'open_links_checkbutton_widget'):
            self.open_links_checkbutton_widget.configure(text=self.lm.get_string("open_links_checkbox_label"))
        self.active_prompt_label.configure(text=self.lm.get_string("active_system_prompt_label"))
        if hasattr(self, 'manage_prompts_button'):
            self.manage_prompts_button.configure(text=self.lm.get_string("manage_prompts_button"))
        self.tts_voice_label.configure(text=self.lm.get_string("tts_voice_label"))
        if hasattr(self, 'preview_tts_button'):
            self.preview_tts_button.configure(text=self.lm.get_string("tts_preview_button", default_text="Preview"))

        # Microphone and Speaker
        self.microphone_label.configure(text=self.lm.get_string("microphone_label", default_text="Microphone:"))
        self.speaker_label.configure(text=self.lm.get_string("speaker_label", default_text="Speaker:"))
        # Update "System Default" in combobox lists if they are already populated
        system_default_translated = self.lm.get_string("system_default_device_option", default_text="System Default")
        if hasattr(self, 'microphone_combobox') and self.microphone_combobox['values']:
            current_mic_selection = self.microphone_var.get()
            mic_values = list(self.microphone_combobox['values'])
            if mic_values[0] != system_default_translated:  # Assuming old default was at index 0
                if current_mic_selection == mic_values[0]:  # if old default was selected
                    self.microphone_var.set(system_default_translated)
                mic_values[0] = system_default_translated
                self.microphone_combobox['values'] = mic_values

        if hasattr(self, 'speaker_combobox') and self.speaker_combobox['values']:
            current_speaker_selection = self.speaker_var.get()
            speaker_values = list(self.speaker_combobox['values'])
            if speaker_values[0] != system_default_translated:  # Assuming old default was at index 0
                if current_speaker_selection == speaker_values[0]:  # if old default was selected
                    self.speaker_var.set(system_default_translated)
                speaker_values[0] = system_default_translated
                self.speaker_combobox['values'] = speaker_values

        self.ui_language_label.configure(text=self.lm.get_string("ui_language_label"))
        lang_display_names_ui = []
        sorted_ui_lang_codes = sorted(AVAILABLE_UI_LANGUAGES.keys(),
                                      key=lambda code: AVAILABLE_UI_LANGUAGES[code]['name'])
        for code in sorted_ui_lang_codes:
            lang_data = AVAILABLE_UI_LANGUAGES[code]
            lang_display_names_ui.append(f"{lang_data['flag']} {lang_data['name']}")
        if hasattr(self, 'ui_language_combobox'):
            self.ui_language_combobox['values'] = lang_display_names_ui

        self.save_button.configure(text=self.lm.get_string("save_button"))
        self.cancel_button_widget.configure(text=self.lm.get_string("cancel_button"))

        if hasattr(self, 'tts_language_combobox'):
            self.tts_language_combobox['values'] = self._get_sorted_tts_language_display_names()

    def load_settings_into_ui(self):
        self.settings = load_settings()
        self.api_key_var.set(self.settings.get("api_key", default_settings["api_key"]))
        self.chat_length_var.set(self.settings.get("chat_length", default_settings["chat_length"]))
        self.activation_word_var.set(self.settings.get("activation_word", default_settings["activation_word"]))
        self.stop_words_var.set(", ".join(self.settings.get("stop_words", default_settings["stop_words"])))
        self.open_links_var.set(
            self.settings.get("open_links_automatically", default_settings["open_links_automatically"]))

        self.refresh_prompt_options()
        current_active_prompt = self.settings.get("active_system_prompt_name", DEFAULT_SYSTEM_PROMPT_NAME)
        if current_active_prompt not in self.system_prompts:
            current_active_prompt = DEFAULT_SYSTEM_PROMPT_NAME
        self.active_prompt_name_var.set(current_active_prompt)

        if not self.tts_language_combobox['values']:
            self.tts_language_combobox['values'] = self._get_sorted_tts_language_display_names()
        current_tts_voice_id = self.settings.get("tts_voice", default_settings["tts_voice"])
        selected_lang_display, selected_voice_name = None, None
        for lang_key, lang_data in TTS_VOICES_STRUCTURED.items():
            for voice_name_short, voice_id_val in lang_data["voices"].items():
                if voice_id_val == current_tts_voice_id:
                    selected_lang_display = f"{lang_data['flag']} {lang_key}"
                    selected_voice_name = voice_name_short;
                    break
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
            self.tts_language_var.set("")
            self._update_tts_specific_voices_combobox()

        # Microphone
        mic_names = self._get_microphone_names()
        self.microphone_combobox['values'] = mic_names
        current_mic = self.settings.get("selected_microphone", default_settings["selected_microphone"])
        system_default_translated = self.lm.get_string("system_default_device_option", default_text="System Default")
        if current_mic == "System Default" and system_default_translated in mic_names:
            self.microphone_var.set(system_default_translated)
        elif current_mic in mic_names:
            self.microphone_var.set(current_mic)
        elif mic_names:  # Fallback to first item (should be System Default translated)
            self.microphone_var.set(mic_names[0])
        else:  # No mics found
            self.microphone_var.set("")
            self.microphone_combobox.configure(state="disabled")

        # Speaker
        speaker_names = self._get_speaker_names()
        self.speaker_combobox['values'] = speaker_names
        current_speaker = self.settings.get("selected_speaker", default_settings["selected_speaker"])
        if current_speaker == "System Default" and system_default_translated in speaker_names:
            self.speaker_var.set(system_default_translated)
        elif current_speaker in speaker_names:
            self.speaker_var.set(current_speaker)
        elif speaker_names:  # Fallback to first item
            self.speaker_var.set(speaker_names[0])
        else:  # No speakers found
            self.speaker_var.set("")
            self.speaker_combobox.configure(state="disabled")

        current_ui_lang_code = self.settings.get("ui_language", default_settings["ui_language"])
        if not AVAILABLE_UI_LANGUAGES: scan_available_languages()
        if not self.ui_language_combobox['values']:
            lang_display_names_ui = [
                f"{AVAILABLE_UI_LANGUAGES[code]['flag']} {AVAILABLE_UI_LANGUAGES[code]['name']}"
                for code in sorted(AVAILABLE_UI_LANGUAGES.keys(), key=lambda c: AVAILABLE_UI_LANGUAGES[c]['name'])
            ]
            self.ui_language_combobox['values'] = lang_display_names_ui
        default_ui_info = AVAILABLE_UI_LANGUAGES.get("en-US", {"name": "English (US)", "flag": "🇺🇸"})
        lang_info = AVAILABLE_UI_LANGUAGES.get(current_ui_lang_code, default_ui_info)
        ui_display_to_set = f"{lang_info['flag']} {lang_info['name']}"
        if ui_display_to_set in self.ui_language_combobox['values']:
            self.ui_language_var.set(ui_display_to_set)
        elif self.ui_language_combobox['values']:
            self.ui_language_var.set(self.ui_language_combobox['values'][0])

    def show_help_tooltip(self, tooltip_key):
        message = self.lm.get_string(tooltip_key)
        title = self.lm.get_string("tooltip_title")
        messagebox.showinfo(title, message, parent=self.root)

    def on_language_change(self, event=None):
        selected_lang_display_name_with_flag = self.ui_language_var.get()
        new_lang_code = "en-US";
        selected_lang_name_for_msg = "English (US)"
        for code, lang_data in AVAILABLE_UI_LANGUAGES.items():
            if f"{lang_data['flag']} {lang_data['name']}" == selected_lang_display_name_with_flag:
                new_lang_code = code;
                selected_lang_name_for_msg = lang_data['name'];
                break
        if new_lang_code != self.lm.current_lang_code:
            self.lm.set_language(new_lang_code)
            current_tts_lang_val = self.tts_language_var.get()
            current_tts_voice_val = self.tts_specific_voice_var.get()

            # Store current mic/speaker selection text before retranslate
            current_mic_text = self.microphone_var.get()
            current_speaker_text = self.speaker_var.get()

            self.retranslate_ui()  # This also repopulates device lists with translated "System Default"

            if selected_lang_display_name_with_flag in self.ui_language_combobox['values']:
                self.ui_language_var.set(selected_lang_display_name_with_flag)

            # Restore Mic/Speaker selections
            # The actual device names don't change, only "System Default" potentially
            system_default_translated = self.lm.get_string("system_default_device_option",
                                                           default_text="System Default")

            # If previous selection was the (old) translated "System Default", set to new translated "System Default"
            # Otherwise, try to set to the exact same device name string.
            # This logic assumes _get_microphone_names and _get_speaker_names are NOT called again in retranslate_ui
            # but they ARE because retranslate_ui calls load_settings_into_ui which calls them.
            # So, load_settings_into_ui will handle setting the correct device after retranslate_ui.
            # The retranslate_ui itself will update the 'values' of comboboxes.
            # Let's simplify: after retranslate_ui, call load_settings_into_ui to correctly set selections.
            self.load_settings_into_ui()  # This will re-populate and re-select based on new lang

            # Try to restore TTS selection (this part is fine)
            if current_tts_lang_val in self.tts_language_combobox['values']:
                self.tts_language_var.set(current_tts_lang_val)
                self._update_tts_specific_voices_combobox()
                if current_tts_voice_val in self.tts_specific_voice_combobox['values']:
                    self.tts_specific_voice_var.set(current_tts_voice_val)
                elif self.tts_specific_voice_combobox['values']:
                    self.tts_specific_voice_var.set(self.tts_specific_voice_combobox['values'][0])
            elif self.tts_language_combobox['values']:
                self.tts_language_var.set(self.tts_language_combobox['values'][0])
                self._update_tts_specific_voices_combobox()
                if self.tts_specific_voice_combobox['values']:
                    self.tts_specific_voice_var.set(self.tts_specific_voice_combobox['values'][0])

            messagebox.showinfo(self.lm.get_string("language_change_applied_title"),
                                self.lm.get_string("language_change_applied_message",
                                                   lang_name=selected_lang_name_for_msg), parent=self.root)

    def refresh_prompt_options(self):
        self.system_prompts = load_system_prompts()
        prompt_names = sorted(list(self.system_prompts.keys()))
        current_selection = self.active_prompt_name_var.get()
        if hasattr(self, 'prompt_combobox'):
            self.prompt_combobox['values'] = prompt_names
            if current_selection in prompt_names:
                self.active_prompt_name_var.set(current_selection)
            elif DEFAULT_SYSTEM_PROMPT_NAME in prompt_names:
                self.active_prompt_name_var.set(DEFAULT_SYSTEM_PROMPT_NAME)
            elif prompt_names:
                self.active_prompt_name_var.set(prompt_names[0])
            else:
                self.active_prompt_name_var.set("")

    def open_prompt_manager(self):
        manager_window = SystemPromptManagerWindow(self.root, self, self.lm)
        self.root.wait_window(manager_window)
        self.refresh_prompt_options()

    def center_window(self):
        self.root.update_idletasks()
        width, height = self.root.winfo_width(), self.root.winfo_height()
        min_w, min_h = self.root.minsize();
        width, height = max(width, min_w), max(height, min_h)
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def save_and_close(self):
        try:
            chat_length_val = self.chat_length_var.get()
        except tk.TclError:
            messagebox.showerror(self.lm.get_string("invalid_input_title"),
                                 self.lm.get_string("chat_length_integer_error"), parent=self.root);
            return
        if not isinstance(chat_length_val, int) or chat_length_val < 1:
            messagebox.showerror(self.lm.get_string("invalid_input_title"),
                                 self.lm.get_string("chat_length_positive_integer_error"), parent=self.root);
            return

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
                ui_language_code = code;
                break

        # Microphone and Speaker saving
        selected_mic_display = self.microphone_var.get()
        final_selected_mic = default_settings["selected_microphone"]
        system_default_translated = self.lm.get_string("system_default_device_option", default_text="System Default")
        if selected_mic_display == system_default_translated:
            final_selected_mic = "System Default"
        elif selected_mic_display:  # If not empty and not "System Default" (translated)
            final_selected_mic = selected_mic_display

        selected_speaker_display = self.speaker_var.get()
        final_selected_speaker = default_settings["selected_speaker"]
        if selected_speaker_display == system_default_translated:
            final_selected_speaker = "System Default"
        elif selected_speaker_display:
            final_selected_speaker = selected_speaker_display

        new_settings = {
            "api_key": self.api_key_var.get(),
            "chat_length": chat_length_val,
            "activation_word": self.activation_word_var.get(),
            "stop_words": [word.strip() for word in self.stop_words_var.get().split(",") if word.strip()],
            "open_links_automatically": self.open_links_var.get(),
            "active_system_prompt_name": self.active_prompt_name_var.get(),
            "tts_voice": final_tts_voice_id,
            "ui_language": ui_language_code,
            "selected_microphone": final_selected_mic,
            "selected_speaker": final_selected_speaker
        }

        current_saved_prompts = load_system_prompts()
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

        if not pygame.mixer.get_init():  # Ensure pygame mixer is init for standalone
            try:
                pygame.mixer.init()
            except pygame.error as e:
                print(f"Pygame mixer could not be initialized (standalone settings): {e}")

        app = ModernSettingsApp(root, lm=lm_standalone)
    except NameError as e:
        if 'sv_ttk' in str(e):
            print(f"Error initializing ModernSettingsApp (likely sv_ttk missing or import error): {e}")
            root.title("Bot Settings (Basic Fallback)")
            ttk.Label(root, text="Error loading modern theme. sv_ttk might be missing. Basic fallback UI.").pack(
                pady=20)
        else:
            print(f"A NameError occurred: {e}")
            root.title("Bot Settings (Error)")
            ttk.Label(root, text=f"Could not initialize settings UI (NameError): {e}").pack(pady=20)
        ttk.Button(root, text="Close", command=root.destroy).pack(pady=10)
    except Exception as e:
        print(f"An unexpected error occurred initializing ModernSettingsApp: {e}")
        import traceback;

        traceback.print_exc()
        root.title("Bot Settings (Error)")
        ttk.Label(root, text=f"Could not initialize settings UI: {e}").pack(pady=20)
        ttk.Button(root, text="Close", command=root.destroy).pack(pady=10)
    root.mainloop()
    if pygame.mixer.get_init(): pygame.mixer.quit()