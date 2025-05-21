# C:/Users/Theminemat/Documents/Programming/desktop_ai/agent_builder.py
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox  # Keep messagebox for showinfo, showerror, etc.
from tkinter.scrolledtext import ScrolledText
import sys
import time  # For TTS preview if added later
import asyncio  # For TTS preview if added later

# from edge_tts import Communicate # For TTS preview if added later
# import pygame # For TTS preview if added later


# Constants related to system prompts
SYSPROMPTS_FILE = "sysprompts.json"
# SYSTEM_PROMPT_SUFFIX is now dynamically generated in get_full_system_prompt
# Original for reference (will not be used directly by get_full_system_prompt anymore):
# SYSTEM_PROMPT_SUFFIX = (
#     "\n\nGenerate the reply so that a simple TTS can read it correctly. "
#     "\nYou can open links on my PC by just including them in your message without formatting; "
#     "just start links with https://. Also use this when the user asks you to search on a website like YouTube."
# )

# Define keys for agent-specific settings within the sysprompts.json structure
AGENT_SETTING_TEXT = "text"
AGENT_SETTING_ACTIVATION_WORD = "activation_word_override"
AGENT_SETTING_STOP_WORDS = "stop_words_override"
AGENT_SETTING_CHAT_LENGTH = "chat_length_override"
AGENT_SETTING_TTS_VOICE = "tts_voice_override"
AGENT_SETTING_OPEN_LINKS = "open_links_automatically_override"


def resource_path_local(relative_path):  # Eigene Definition oder Import von main
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)


class CustomAskYesNoDialog(tk.Toplevel):
    def __init__(self, parent, title, message, lm):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.lm = lm
        self.result = False  # Default to False (No)

        self.grab_set()  # Make modal

        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(expand=True, fill=tk.BOTH)

        message_label = ttk.Label(main_frame, text=message, wraplength=350, justify=tk.LEFT)
        message_label.pack(pady=(0, 20))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        # Spacer to push buttons to the right
        spacer = ttk.Frame(button_frame)
        spacer.pack(side=tk.LEFT, expand=True)

        self.no_button = ttk.Button(
            button_frame,
            text=self.lm.get_string("no_button_text", default_text="No"),
            command=self._on_no
        )
        self.no_button.pack(side=tk.RIGHT, padx=(5, 0))

        self.yes_button = ttk.Button(
            button_frame,
            text=self.lm.get_string("yes_button_text", default_text="Yes"),
            command=self._on_yes,
            style="Accent.TButton"
        )
        self.yes_button.pack(side=tk.RIGHT)

        self.protocol("WM_DELETE_WINDOW", self._on_no)  # Treat close as "No"
        self.bind("<Escape>", lambda e: self._on_no())  # Escape key as "No"

        # Centering logic
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_req_width = self.winfo_reqwidth()
        dialog_req_height = self.winfo_reqheight()
        x_pos = parent_x + (parent_width // 2) - (dialog_req_width // 2)
        y_pos = parent_y + (parent_height // 2) - (dialog_req_height // 2)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        if x_pos + dialog_req_width > screen_width: x_pos = screen_width - dialog_req_width
        if y_pos + dialog_req_height > screen_height: y_pos = screen_height - dialog_req_height
        if x_pos < 0: x_pos = 0
        if y_pos < 0: y_pos = 0

        self.geometry(f'+{x_pos}+{y_pos}')
        self.yes_button.focus_set()

    def _on_yes(self):
        self.result = True
        self.destroy()

    def _on_no(self):
        self.result = False
        self.destroy()

    def show(self):
        self.deiconify()  # Ensure window is visible
        self.wait_window()  # Block execution until window is destroyed
        return self.result


def load_system_prompts(default_prompt_name, default_prompt_text):
    default_agent_config = {
        AGENT_SETTING_TEXT: default_prompt_text,
        AGENT_SETTING_ACTIVATION_WORD: None,
        AGENT_SETTING_STOP_WORDS: None,
        AGENT_SETTING_CHAT_LENGTH: None,
        AGENT_SETTING_TTS_VOICE: None,
        AGENT_SETTING_OPEN_LINKS: None,
    }

    if not os.path.exists(SYSPROMPTS_FILE):
        try:
            with open(SYSPROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump({default_prompt_name: default_agent_config}, f, indent=4, ensure_ascii=False)
            print(f"'{SYSPROMPTS_FILE}' not found. Created with default system prompt structure.")
            return {default_prompt_name: default_agent_config}
        except Exception as e:
            print(f"Error creating default system prompts file: {e}")
            return {default_prompt_name: default_agent_config}

    try:
        with open(SYSPROMPTS_FILE, "r", encoding="utf-8") as f:
            prompts = json.load(f)
            if not isinstance(prompts, dict) or not prompts:
                raise ValueError("Invalid format or empty prompts file.")

            migrated = False
            for name, data in prompts.items():
                if isinstance(data, str):  # Old format: value is just the prompt text
                    prompts[name] = {
                        AGENT_SETTING_TEXT: data,
                        AGENT_SETTING_ACTIVATION_WORD: None,
                        AGENT_SETTING_STOP_WORDS: None,
                        AGENT_SETTING_CHAT_LENGTH: None,
                        AGENT_SETTING_TTS_VOICE: None,
                        AGENT_SETTING_OPEN_LINKS: None,
                    }
                    migrated = True
                elif isinstance(data, dict):  # New format, ensure all keys exist
                    updated_data = False
                    if AGENT_SETTING_TEXT not in data:  # Should not happen if migrated from string
                        data[
                            AGENT_SETTING_TEXT] = default_prompt_text if name == default_prompt_name else "Missing prompt text."
                        updated_data = True
                    for key in [AGENT_SETTING_ACTIVATION_WORD, AGENT_SETTING_STOP_WORDS,
                                AGENT_SETTING_CHAT_LENGTH, AGENT_SETTING_TTS_VOICE,
                                AGENT_SETTING_OPEN_LINKS]:
                        if key not in data:
                            data[key] = None
                            updated_data = True
                    if updated_data:
                        migrated = True  # Mark for saving if any key was added

            if default_prompt_name not in prompts:
                prompts[default_prompt_name] = default_agent_config.copy()
                migrated = True
            elif not isinstance(prompts[default_prompt_name], dict) or AGENT_SETTING_TEXT not in prompts[
                default_prompt_name]:
                # Ensure default prompt is correctly structured if it existed but was malformed
                prompts[default_prompt_name] = default_agent_config.copy()
                if isinstance(prompts[default_prompt_name], str):  # if it was a string before
                    prompts[default_prompt_name][AGENT_SETTING_TEXT] = prompts[default_prompt_name]
                migrated = True

            if migrated:
                _save_prompts_internal(prompts)
                print(f"System prompts in '{SYSPROMPTS_FILE}' were migrated/updated to new structure and saved.")
            return prompts
    except Exception as e:
        print(f"Error loading system prompts: {e}. Returning default prompt structure.")
        return {default_prompt_name: default_agent_config.copy()}


def _save_prompts_internal(prompts_dict):
    """Internal save without UI, for use within load_system_prompts."""
    try:
        with open(SYSPROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(prompts_dict, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving system prompts internally: {e}")
        return False


def save_system_prompts(prompts_dict, lm):  # lm can be None
    try:
        with open(SYSPROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(prompts_dict, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        if lm:  # lm might be None if called from a context without LanguageManager
            messagebox.showerror(lm.get_string("error_title"), lm.get_string("failed_to_save_prompts_error", e=e),
                                 parent=lm.get_active_window_for_messagebox())
        else:
            messagebox.showerror("Error", f"Failed to save system prompts:\n{e}")
        return False


def get_full_system_prompt(prompt_name, all_prompts_data,
                           global_activation_word, global_open_links_setting,
                           default_prompt_text_if_missing,
                           effective_tts_voice_id, tts_voices_structured_data):  # Added new parameters
    agent_config = all_prompts_data.get(prompt_name, {})
    if not isinstance(agent_config, dict):  # Should not happen with new load_system_prompts
        base_text = default_prompt_text_if_missing
        activation_word_to_use = global_activation_word
        effective_open_links = global_open_links_setting
    else:
        base_text = agent_config.get(AGENT_SETTING_TEXT, default_prompt_text_if_missing)
        agent_specific_activation_word = agent_config.get(AGENT_SETTING_ACTIVATION_WORD)
        activation_word_to_use = agent_specific_activation_word if agent_specific_activation_word else global_activation_word

        # Determine effective open_links setting for this agent
        agent_specific_open_links = agent_config.get(AGENT_SETTING_OPEN_LINKS)  # This can be True, False, or None
        if agent_specific_open_links is None:
            effective_open_links = global_open_links_setting
        else:
            effective_open_links = agent_specific_open_links

    base_text = base_text.replace("{name}", activation_word_to_use)

    # Construct the dynamic suffix parts
    tts_instruction_part = "\n\nGenerate the reply so that a simple TTS can read it correctly."

    language_instruction_part = ""
    if effective_tts_voice_id and tts_voices_structured_data:
        found_language_name = None
        for lang_key, lang_data in tts_voices_structured_data.items():
            if "voices" in lang_data:
                for voice_short_name, voice_id_val in lang_data["voices"].items():
                    if voice_id_val == effective_tts_voice_id:
                        found_language_name = lang_key.split(' (')[
                            0]  # Extracts "English" from "English (US)", "German" from "German"
                        break
            if found_language_name:
                break

        if found_language_name:
            language_instruction_part = f"\nSpeak in fluent {found_language_name}."

    links_instruction_part = ""
    if effective_open_links:
        links_instruction_part = "\nYou can open links on the users computer by just putting them somewhere in your response with https:// if the user ask you to google something you can also open it with url parameters."
    else:
        links_instruction_part = "\nYou can't open links on the users computer because he has this setting disabled."

    dynamic_suffix = tts_instruction_part + language_instruction_part + links_instruction_part
    return base_text + dynamic_suffix


class SystemPromptManagerWindow(tk.Toplevel):
    def __init__(self, master_widget, app_instance, lm, default_prompt_name_const, default_prompt_text_const):
        super().__init__(master_widget)
        self.parent_app = app_instance  # This is ModernSettingsApp instance
        self.lm = lm
        self.DEFAULT_SYSTEM_PROMPT_NAME = default_prompt_name_const
        self.DEFAULT_SYSTEM_PROMPT_TEXT = default_prompt_text_const
        self.TTS_VOICES_STRUCTURED = self.parent_app.TTS_VOICES_STRUCTURED  # Get from parent_app

        self.grab_set()
        self.prompts_dict = load_system_prompts(self.DEFAULT_SYSTEM_PROMPT_NAME, self.DEFAULT_SYSTEM_PROMPT_TEXT)

        self.title(self.lm.get_string("prompt_manager_title"))
        self.minsize(750, 600)

        # Main PanedWindow for resizable layout
        paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Left Panel (Prompts List) ---
        left_panel_frame = ttk.Frame(paned_window, padding=(0, 0, 5, 0))  # Add padding to the right
        paned_window.add(left_panel_frame, weight=1)

        self.prompts_list_label = ttk.Label(left_panel_frame, font=self.parent_app.label_font)
        self.prompts_list_label.pack(anchor="w", pady=(0, 5))
        self.prompts_listbox = tk.Listbox(left_panel_frame, exportselection=False, height=15)
        self.prompts_listbox.pack(fill=tk.BOTH, expand=True)
        self.prompts_listbox.bind("<<ListboxSelect>>", self.on_prompt_select)

        list_actions_frame = ttk.Frame(left_panel_frame)
        list_actions_frame.pack(fill=tk.X, pady=5)

        self.new_button = ttk.Button(list_actions_frame, command=self.new_prompt)
        self.new_button.pack(side=tk.LEFT, padx=2)
        self.duplicate_button = ttk.Button(list_actions_frame, command=self.duplicate_prompt)
        self.duplicate_button.pack(side=tk.LEFT, padx=2)
        self.delete_button = ttk.Button(list_actions_frame, command=self.delete_prompt)
        self.delete_button.pack(side=tk.LEFT, padx=2)

        # --- Right Panel (Prompt Details and Agent Settings) ---
        right_panel_scrollable_frame_container = ttk.Frame(paned_window)
        paned_window.add(right_panel_scrollable_frame_container, weight=3)

        # Create a canvas and a scrollbar for the right panel
        canvas = tk.Canvas(right_panel_scrollable_frame_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_panel_scrollable_frame_container, orient="vertical", command=canvas.yview)
        self.right_panel = ttk.Frame(canvas, padding=5)  # This frame will contain all widgets

        self.right_panel.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.create_window((0, 0), window=self.right_panel, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.right_panel.columnconfigure(1, weight=1)  # Make entry/widget column expandable

        # Prompt Name
        self.prompt_name_label_widget = ttk.Label(self.right_panel, font=self.parent_app.label_font)
        self.prompt_name_label_widget.grid(row=0, column=0, sticky="w", pady=(0, 2), padx=(0, 5))
        self.prompt_name_var = tk.StringVar()
        self.prompt_name_entry = ttk.Entry(self.right_panel, textvariable=self.prompt_name_var, state=tk.DISABLED)
        self.prompt_name_entry.grid(row=0, column=1, sticky="ew", pady=(0, 10))

        # Prompt Text
        self.prompt_text_label_widget = ttk.Label(self.right_panel, font=self.parent_app.label_font)
        self.prompt_text_label_widget.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.prompt_text_widget = ScrolledText(self.right_panel, wrap=tk.WORD, height=8, state=tk.DISABLED,
                                               relief=tk.SOLID, borderwidth=1)
        self.prompt_text_widget.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        self.style_scrolled_text()

        # Agent Specific Settings Group
        agent_settings_frame = ttk.LabelFrame(self.right_panel, padding=(10, 5))
        agent_settings_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 10))
        agent_settings_frame.columnconfigure(1, weight=1)

        self.agent_settings_label = agent_settings_frame  # For retranslate

        current_row_agent = 0

        # Helper for agent settings
        def create_agent_setting_row(parent, label_key, widget_creator, row, tooltip_key=None, default_val_func=None):
            label = ttk.Label(parent, text=self.lm.get_string(label_key) + ":", font=self.parent_app.label_font)
            label.grid(row=row, column=0, sticky="w", pady=3, padx=(0, 5))

            widget = widget_creator(parent)
            widget.grid(row=row, column=1, sticky="ew", pady=3)

            if default_val_func:  # Add placeholder for global default
                placeholder_text = self.lm.get_string("agent_builder_global_default_placeholder",
                                                      default_text="Global: {value}")
                global_default_val = default_val_func()
                # For boolean, display True/False
                if isinstance(global_default_val, bool):
                    global_default_val = str(global_default_val)
                elif isinstance(global_default_val, list):
                    global_default_val = ", ".join(global_default_val)

                default_label = ttk.Label(parent, text=placeholder_text.format(value=global_default_val),
                                          font=("Segoe UI", 8), foreground="gray")
                default_label.grid(row=row, column=2, sticky="w", padx=(5, 0))
            return label, widget

        # Agent Activation Word
        self.agent_activation_word_var = tk.StringVar()
        _, self.agent_activation_word_entry = create_agent_setting_row(
            agent_settings_frame, "activation_word_label",
            lambda p: ttk.Entry(p, textvariable=self.agent_activation_word_var, state=tk.DISABLED),
            current_row_agent, default_val_func=lambda: self.parent_app.settings.get("activation_word",
                                                                                     self.parent_app.default_settings[
                                                                                         "activation_word"])
        )
        current_row_agent += 1

        # Agent Stop Words
        self.agent_stop_words_var = tk.StringVar()
        _, self.agent_stop_words_entry = create_agent_setting_row(
            agent_settings_frame, "stop_words_label",
            lambda p: ttk.Entry(p, textvariable=self.agent_stop_words_var, state=tk.DISABLED),
            current_row_agent, default_val_func=lambda: ", ".join(
                self.parent_app.settings.get("stop_words", self.parent_app.default_settings["stop_words"]))
        )
        # Helper text for stop words
        self.agent_stop_words_helper_label = ttk.Label(agent_settings_frame, font=("Segoe UI", 8), foreground="gray")
        self.agent_stop_words_helper_label.grid(row=current_row_agent, column=1, sticky="w", padx=(3, 0),
                                                pady=(20, 0))  # Below entry
        current_row_agent += 1

        # Agent Chat Length
        self.agent_chat_length_var = tk.StringVar()  # Use StringVar to allow empty for global default
        _, self.agent_chat_length_spinbox = create_agent_setting_row(
            agent_settings_frame, "chat_length_label",
            lambda p: ttk.Spinbox(p, from_=1, to=100, textvariable=self.agent_chat_length_var, width=8,
                                  state=tk.DISABLED),
            current_row_agent, default_val_func=lambda: self.parent_app.settings.get("chat_length",
                                                                                     self.parent_app.default_settings[
                                                                                         "chat_length"])
        )
        current_row_agent += 1

        # Agent Open Links Automatically
        self.agent_open_links_var = tk.StringVar(value="global")  # "global", "true", "false"
        open_links_frame = ttk.Frame(agent_settings_frame)
        self.agent_open_links_rb_global = ttk.Radiobutton(open_links_frame, variable=self.agent_open_links_var,
                                                          value="global", state=tk.DISABLED)
        self.agent_open_links_rb_yes = ttk.Radiobutton(open_links_frame, variable=self.agent_open_links_var,
                                                       value="true", state=tk.DISABLED)
        self.agent_open_links_rb_no = ttk.Radiobutton(open_links_frame, variable=self.agent_open_links_var,
                                                      value="false", state=tk.DISABLED)

        self.agent_open_links_rb_global.pack(side=tk.LEFT, padx=2)
        self.agent_open_links_rb_yes.pack(side=tk.LEFT, padx=2)
        self.agent_open_links_rb_no.pack(side=tk.LEFT, padx=2)

        _, _ = create_agent_setting_row(
            agent_settings_frame, "open_links_label",
            lambda p: open_links_frame,
            current_row_agent, default_val_func=lambda: self.parent_app.settings.get("open_links_automatically",
                                                                                     self.parent_app.default_settings[
                                                                                         "open_links_automatically"])
        )
        current_row_agent += 1

        # Agent TTS Voice Override
        self.agent_tts_language_var = tk.StringVar()
        self.agent_tts_specific_voice_var = tk.StringVar()

        def create_agent_tts_selector(parent):
            tts_frame = ttk.Frame(parent)
            tts_frame.columnconfigure(0, weight=1);
            tts_frame.columnconfigure(1, weight=1)

            self.agent_tts_language_label_widget = ttk.Label(tts_frame)  # For retranslate
            self.agent_tts_language_label_widget.grid(row=0, column=0, sticky="w", padx=(0, 5))

            self.agent_tts_language_combobox = ttk.Combobox(tts_frame, textvariable=self.agent_tts_language_var,
                                                            state="disabled", width=20)
            self.agent_tts_language_combobox.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=(0, 5))
            self.agent_tts_language_combobox.bind("<<ComboboxSelected>>", self._on_agent_tts_language_selected)

            self.agent_tts_specific_voice_label_widget = ttk.Label(tts_frame)  # For retranslate
            self.agent_tts_specific_voice_label_widget.grid(row=0, column=1, sticky="w", padx=(0, 5))

            self.agent_tts_specific_voice_combobox = ttk.Combobox(tts_frame,
                                                                  textvariable=self.agent_tts_specific_voice_var,
                                                                  state="disabled", width=20)
            self.agent_tts_specific_voice_combobox.grid(row=1, column=1, sticky="ew", pady=(0, 5))
            # Preview button could be added here if desired
            return tts_frame

        _, self.agent_tts_widget_frame = create_agent_setting_row(
            agent_settings_frame, "tts_voice_label",  # Use same key, context implies override
            create_agent_tts_selector,
            current_row_agent, default_val_func=lambda: self.parent_app.settings.get("tts_voice",
                                                                                     self.parent_app.default_settings[
                                                                                         "tts_voice"])
        )
        current_row_agent += 1

        # Edit Actions (Save/Cancel for the entire prompt including agent settings)
        edit_actions_frame = ttk.Frame(self.right_panel)
        edit_actions_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
        self.save_button_editor = ttk.Button(edit_actions_frame, command=self.save_edited_prompt, state=tk.DISABLED)
        self.save_button_editor.pack(side=tk.LEFT, padx=2)
        self.cancel_button_editor = ttk.Button(edit_actions_frame, command=self.cancel_edit, state=tk.DISABLED)
        self.cancel_button_editor.pack(side=tk.LEFT, padx=2)

        # Bottom Frame (Close Manager)
        bottom_frame = ttk.Frame(self, padding=(10, 10, 10, 0))  # Reduced top padding
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.close_manager_button = ttk.Button(bottom_frame, command=self.close_manager, style="Accent.TButton")
        self.close_manager_button.pack(side=tk.RIGHT)

        self.retranslate_ui()
        self.populate_prompts_listbox()
        self.selected_prompt_original_name = None
        self.protocol("WM_DELETE_WINDOW", self.close_manager)

        self.after(100, lambda: self.right_panel.event_generate("<Configure>"))  # Ensure scrollregion is set up

    def _get_agent_tts_language_display_names_with_global(self):
        # Get base sorted names from parent app's method (if it exists and is callable)
        # or replicate logic if parent_app doesn't have _get_sorted_tts_language_display_names
        base_names = []
        if hasattr(self.parent_app, '_get_sorted_tts_language_display_names') and callable(
                self.parent_app._get_sorted_tts_language_display_names):
            base_names = self.parent_app._get_sorted_tts_language_display_names()
        else:  # Fallback: replicate minimal sorting for TTS languages
            english_keys = [k for k, data in self.TTS_VOICES_STRUCTURED.items() if data["code"].startswith("en-")]
            sorted_keys = []
            for eng_key in sorted(english_keys):
                if eng_key not in sorted_keys: sorted_keys.append(eng_key)
            for lang_key in sorted(self.TTS_VOICES_STRUCTURED.keys()):
                if lang_key not in sorted_keys: sorted_keys.append(lang_key)
            base_names = [f"{self.TTS_VOICES_STRUCTURED[key]['flag']} {key}" for key in sorted_keys]

        return [
            self.lm.get_string("agent_builder_tts_use_global", default_text="-- Use Global Default --")] + base_names

    def _on_agent_tts_language_selected(self, event=None):
        self._update_agent_tts_specific_voices_combobox()
        if self.agent_tts_specific_voice_combobox['values'] and not self.agent_tts_specific_voice_var.get():
            self.agent_tts_specific_voice_var.set(self.agent_tts_specific_voice_combobox['values'][0])
        elif not self.agent_tts_specific_voice_combobox['values']:
            self.agent_tts_specific_voice_var.set("")

    def _update_agent_tts_specific_voices_combobox(self):
        selected_lang_display_with_flag = self.agent_tts_language_var.get()
        voice_names = []

        if selected_lang_display_with_flag == self.lm.get_string("agent_builder_tts_use_global",
                                                                 default_text="-- Use Global Default --"):
            # "Use Global Default" selected for language
            self.agent_tts_specific_voice_var.set("")
            self.agent_tts_specific_voice_combobox['values'] = []
            self.agent_tts_specific_voice_combobox.configure(state="disabled")
            return

        if selected_lang_display_with_flag:
            target_lang_key = None
            for l_key, l_data in self.TTS_VOICES_STRUCTURED.items():
                if f"{l_data['flag']} {l_key}" == selected_lang_display_with_flag:
                    target_lang_key = l_key
                    break
            if target_lang_key and target_lang_key in self.TTS_VOICES_STRUCTURED:
                voice_names = sorted(list(self.TTS_VOICES_STRUCTURED[target_lang_key]["voices"].keys()))

        current_specific_voice = self.agent_tts_specific_voice_var.get()
        self.agent_tts_specific_voice_combobox['values'] = voice_names

        if voice_names:
            if current_specific_voice in voice_names:
                self.agent_tts_specific_voice_var.set(current_specific_voice)
            else:
                self.agent_tts_specific_voice_var.set(voice_names[0])
            self.agent_tts_specific_voice_combobox.configure(state="readonly")
        else:
            self.agent_tts_specific_voice_var.set("")
            self.agent_tts_specific_voice_combobox.configure(state="disabled")

    def style_scrolled_text(self):
        # (Same as before, simplified for brevity in this diff)
        style = ttk.Style()
        try:
            is_dark_theme = 'dark' in style.theme_use().lower() if hasattr(style, 'theme_use') else False
            bg_color = style.lookup('TEntry', 'fieldbackground') if style.lookup('TEntry', 'fieldbackground') else (
                "#2b2b2b" if is_dark_theme else "white")
            fg_color = style.lookup('TEntry', 'foreground') if style.lookup('TEntry', 'foreground') else (
                "#cccccc" if is_dark_theme else "black")
            self.prompt_text_widget.configure(bg=bg_color, fg=fg_color, insertbackground=fg_color)
        except Exception:  # Fallback
            self.prompt_text_widget.configure(bg="white", fg="black", insertbackground="black")

    def retranslate_ui(self):
        self.title(self.lm.get_string("prompt_manager_title"))
        self.prompts_list_label.configure(text=self.lm.get_string("prompts_list_label"))
        self.new_button.configure(text=self.lm.get_string("new_prompt_button"))
        self.duplicate_button.configure(text=self.lm.get_string("duplicate_prompt_button"))
        self.delete_button.configure(text=self.lm.get_string("delete_prompt_button"))
        self.prompt_name_label_widget.configure(text=self.lm.get_string("prompt_name_label"))
        self.prompt_text_label_widget.configure(text=self.lm.get_string("prompt_text_label"))

        self.agent_settings_label.configure(text=self.lm.get_string("agent_builder_specific_settings_label",
                                                                    default_text="Agent-Specific Overrides (leave blank/default to use global settings)"))

        # Retranslate labels for agent settings (assuming they are attributes of self)
        # Example for activation word, repeat for others:
        # self.agent_activation_word_label.configure(text=self.lm.get_string("activation_word_label") + ":")
        # For radio buttons:
        self.agent_open_links_rb_global.configure(
            text=self.lm.get_string("agent_builder_use_global_rb", default_text="Global"))
        self.agent_open_links_rb_yes.configure(text=self.lm.get_string("yes_button_text", default_text="Yes"))
        self.agent_open_links_rb_no.configure(text=self.lm.get_string("no_button_text", default_text="No"))

        self.agent_tts_language_label_widget.configure(
            text=self.lm.get_string("tts_language_label", default_text="TTS Language:"))
        self.agent_tts_specific_voice_label_widget.configure(text=self.lm.get_string("tts_voice_label",
                                                                                     default_text="TTS Voice:"))  # Or a more specific "Specific Voice:"
        if hasattr(self, 'agent_tts_language_combobox'):  # Repopulate with translated "Use Global"
            self.agent_tts_language_combobox['values'] = self._get_agent_tts_language_display_names_with_global()

        self.save_button_editor.configure(text=self.lm.get_string("save_changes_button"))
        self.cancel_button_editor.configure(text=self.lm.get_string("cancel_edit_button"))
        self.close_manager_button.configure(text=self.lm.get_string("close_manager_button"))
        self.agent_stop_words_helper_label.configure(text=self.lm.get_string("stop_words_helper"))

        current_save_button_text = self.save_button_editor.cget("text")
        expected_save_changes_text = self.lm.get_string("save_changes_button")
        if current_save_button_text != expected_save_changes_text and self.selected_prompt_original_name is None:
            self.save_button_editor.configure(text=self.lm.get_string("save_new_prompt_button"))

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

        agent_config = self.prompts_dict.get(prompt_name, {})
        if not isinstance(agent_config, dict):  # Should be handled by load_system_prompts
            agent_config = {AGENT_SETTING_TEXT: str(agent_config)}  # Basic fallback

        self.prompt_name_var.set(prompt_name)
        self.prompt_text_widget.configure(state=tk.NORMAL)
        self.prompt_text_widget.delete("1.0", tk.END)
        self.prompt_text_widget.insert("1.0", agent_config.get(AGENT_SETTING_TEXT, ""))

        # Populate agent-specific fields
        self.agent_activation_word_var.set(agent_config.get(AGENT_SETTING_ACTIVATION_WORD) or "")

        stop_words_list = agent_config.get(AGENT_SETTING_STOP_WORDS)
        self.agent_stop_words_var.set(", ".join(stop_words_list) if stop_words_list else "")

        chat_len = agent_config.get(AGENT_SETTING_CHAT_LENGTH)
        self.agent_chat_length_var.set(str(chat_len) if chat_len is not None else "")

        open_links_override = agent_config.get(AGENT_SETTING_OPEN_LINKS)
        if open_links_override is True:
            self.agent_open_links_var.set("true")
        elif open_links_override is False:
            self.agent_open_links_var.set("false")
        else:
            self.agent_open_links_var.set("global")

        # TTS Override
        self.agent_tts_language_combobox['values'] = self._get_agent_tts_language_display_names_with_global()
        tts_voice_override = agent_config.get(AGENT_SETTING_TTS_VOICE)
        if tts_voice_override:
            selected_lang_display, selected_voice_name = None, None
            for lang_key, lang_data in self.TTS_VOICES_STRUCTURED.items():
                for voice_name_short, voice_id_val in lang_data["voices"].items():
                    if voice_id_val == tts_voice_override:
                        selected_lang_display = f"{lang_data['flag']} {lang_key}"
                        selected_voice_name = voice_name_short
                        break
                if selected_lang_display: break

            if selected_lang_display and selected_lang_display in self.agent_tts_language_combobox['values']:
                self.agent_tts_language_var.set(selected_lang_display)
                self._update_agent_tts_specific_voices_combobox()
                if selected_voice_name and selected_voice_name in self.agent_tts_specific_voice_combobox['values']:
                    self.agent_tts_specific_voice_var.set(selected_voice_name)
            else:  # Fallback to global if specific voice not found
                self.agent_tts_language_var.set(
                    self.lm.get_string("agent_builder_tts_use_global", default_text="-- Use Global Default --"))
        else:
            self.agent_tts_language_var.set(
                self.lm.get_string("agent_builder_tts_use_global", default_text="-- Use Global Default --"))
        self._update_agent_tts_specific_voices_combobox()

        self.enable_editing_fields()
        if prompt_name == self.DEFAULT_SYSTEM_PROMPT_NAME:
            self.prompt_name_entry.configure(state=tk.DISABLED)
        # else: self.prompt_name_entry.configure(state=tk.NORMAL) # Handled by enable_editing_fields
        self.save_button_editor.configure(text=self.lm.get_string("save_changes_button"))

    def enable_editing_fields(self):
        self.prompt_name_entry.configure(state=tk.NORMAL)  # Default state
        self.prompt_text_widget.configure(state=tk.NORMAL)
        self.save_button_editor.configure(state=tk.NORMAL)
        self.cancel_button_editor.configure(state=tk.NORMAL)

        # Enable agent-specific fields
        self.agent_activation_word_entry.configure(state=tk.NORMAL)
        self.agent_stop_words_entry.configure(state=tk.NORMAL)
        self.agent_chat_length_spinbox.configure(state=tk.NORMAL)  # Or "readonly" if you prefer
        self.agent_open_links_rb_global.configure(state=tk.NORMAL)
        self.agent_open_links_rb_yes.configure(state=tk.NORMAL)
        self.agent_open_links_rb_no.configure(state=tk.NORMAL)
        self.agent_tts_language_combobox.configure(state="readonly")
        # agent_tts_specific_voice_combobox state is handled by _update_agent_tts_specific_voices_combobox

    def disable_editing_fields(self):
        self.prompt_name_var.set("")
        self.prompt_text_widget.delete("1.0", tk.END);
        self.prompt_text_widget.configure(state=tk.DISABLED)
        self.prompt_name_entry.configure(state=tk.DISABLED)
        self.save_button_editor.configure(state=tk.DISABLED)
        self.cancel_button_editor.configure(state=tk.DISABLED)
        self.selected_prompt_original_name = None

        # Disable agent-specific fields and clear them
        self.agent_activation_word_var.set("");
        self.agent_activation_word_entry.configure(state=tk.DISABLED)
        self.agent_stop_words_var.set("");
        self.agent_stop_words_entry.configure(state=tk.DISABLED)
        self.agent_chat_length_var.set("");
        self.agent_chat_length_spinbox.configure(state=tk.DISABLED)
        self.agent_open_links_var.set("global")
        self.agent_open_links_rb_global.configure(state=tk.DISABLED)
        self.agent_open_links_rb_yes.configure(state=tk.DISABLED)
        self.agent_open_links_rb_no.configure(state=tk.DISABLED)

        self.agent_tts_language_var.set(
            self.lm.get_string("agent_builder_tts_use_global", default_text="-- Use Global Default --"))
        self.agent_tts_specific_voice_var.set("")
        self.agent_tts_language_combobox.configure(state="disabled")
        self.agent_tts_specific_voice_combobox.configure(state="disabled", values=[])

    def new_prompt(self):
        self.prompts_listbox.selection_clear(0, tk.END)
        self.selected_prompt_original_name = None

        self.prompt_name_var.set(self.lm.get_string("new_prompt_default_name", default_text="New Prompt Name"))
        self.prompt_text_widget.configure(state=tk.NORMAL)
        self.prompt_text_widget.delete("1.0", tk.END)
        self.prompt_text_widget.insert("1.0", self.lm.get_string("new_prompt_default_text",
                                                                 default_text="Enter prompt text here..."))

        # Clear agent-specific fields to "use global"
        self.agent_activation_word_var.set("")
        self.agent_stop_words_var.set("")
        self.agent_chat_length_var.set("")  # Empty means use global
        self.agent_open_links_var.set("global")
        self.agent_tts_language_var.set(
            self.lm.get_string("agent_builder_tts_use_global", default_text="-- Use Global Default --"))
        self._update_agent_tts_specific_voices_combobox()  # This will disable specific voice

        self.enable_editing_fields()
        self.prompt_name_entry.focus()
        self.save_button_editor.configure(text=self.lm.get_string("save_new_prompt_button"))

    def save_edited_prompt(self):
        new_name = self.prompt_name_var.get().strip()
        prompt_text_content = self.prompt_text_widget.get("1.0", tk.END).strip()

        if not new_name:
            messagebox.showerror(self.lm.get_string("error_title"), self.lm.get_string("prompt_name_empty_error"),
                                 parent=self)
            return
        if not prompt_text_content:
            messagebox.showerror(self.lm.get_string("error_title"), self.lm.get_string("prompt_text_empty_error"),
                                 parent=self)
            return

        # Get agent-specific settings
        act_word_override = self.agent_activation_word_var.get().strip() or None
        stop_words_str = self.agent_stop_words_var.get().strip()
        stop_words_override = [w.strip() for w in stop_words_str.split(",") if w.strip()] or None

        chat_len_str = self.agent_chat_length_var.get().strip()
        chat_len_override = None
        if chat_len_str:
            try:
                chat_len_override = int(chat_len_str)
                if chat_len_override <= 0:
                    messagebox.showerror(self.lm.get_string("invalid_input_title"),
                                         self.lm.get_string("chat_length_positive_integer_error"), parent=self)
                    return
            except ValueError:
                messagebox.showerror(self.lm.get_string("invalid_input_title"),
                                     self.lm.get_string("chat_length_integer_error"), parent=self)
                return

        open_links_val = self.agent_open_links_var.get()
        open_links_override = None
        if open_links_val == "true":
            open_links_override = True
        elif open_links_val == "false":
            open_links_override = False

        tts_voice_override = None
        selected_tts_lang_display = self.agent_tts_language_var.get()
        selected_tts_voice_short = self.agent_tts_specific_voice_var.get()
        if selected_tts_lang_display != self.lm.get_string("agent_builder_tts_use_global",
                                                           default_text="-- Use Global Default --") and selected_tts_voice_short:
            target_lang_key = None
            for l_key, l_data in self.TTS_VOICES_STRUCTURED.items():
                if f"{l_data['flag']} {l_key}" == selected_tts_lang_display:
                    target_lang_key = l_key;
                    break
            if target_lang_key and selected_tts_voice_short in self.TTS_VOICES_STRUCTURED[target_lang_key]["voices"]:
                tts_voice_override = self.TTS_VOICES_STRUCTURED[target_lang_key]["voices"][selected_tts_voice_short]

        agent_config_payload = {
            AGENT_SETTING_TEXT: prompt_text_content,
            AGENT_SETTING_ACTIVATION_WORD: act_word_override,
            AGENT_SETTING_STOP_WORDS: stop_words_override,
            AGENT_SETTING_CHAT_LENGTH: chat_len_override,
            AGENT_SETTING_OPEN_LINKS: open_links_override,
            AGENT_SETTING_TTS_VOICE: tts_voice_override
        }

        is_new_prompt = self.selected_prompt_original_name is None
        is_renaming = not is_new_prompt and new_name != self.selected_prompt_original_name

        if is_new_prompt or is_renaming:
            if new_name in self.prompts_dict:
                messagebox.showerror(self.lm.get_string("error_title"),
                                     self.lm.get_string("prompt_name_exists_error", new_name=new_name), parent=self)
                return
            if is_renaming:
                if self.selected_prompt_original_name == self.DEFAULT_SYSTEM_PROMPT_NAME:
                    messagebox.showerror(self.lm.get_string("error_title"),
                                         self.lm.get_string("cannot_rename_default_prompt_error"), parent=self)
                    self.prompt_name_var.set(self.DEFAULT_SYSTEM_PROMPT_NAME)
                    return
                del self.prompts_dict[self.selected_prompt_original_name]
        elif self.selected_prompt_original_name == self.DEFAULT_SYSTEM_PROMPT_NAME and new_name != self.DEFAULT_SYSTEM_PROMPT_NAME:  # Trying to rename default
            messagebox.showerror(self.lm.get_string("error_title"),
                                 self.lm.get_string("cannot_rename_default_prompt_error"), parent=self)
            self.prompt_name_var.set(self.DEFAULT_SYSTEM_PROMPT_NAME)
            return

        self.prompts_dict[new_name] = agent_config_payload
        self.populate_prompts_listbox()
        try:
            idx = list(sorted(self.prompts_dict.keys())).index(new_name)
            self.prompts_listbox.selection_set(idx)
            self.prompts_listbox.see(idx)
            self.on_prompt_select()  # Reload the saved data into fields
        except ValueError:
            self.disable_editing_fields()

        messagebox.showinfo(self.lm.get_string("success_title"),
                            self.lm.get_string("prompt_saved_success", new_name=new_name), parent=self)

    def cancel_edit(self):
        if self.selected_prompt_original_name:  # Was editing an existing prompt
            self.on_prompt_select()  # Reloads original data for that prompt
        else:  # Was creating a new prompt
            self.disable_editing_fields()

    def delete_prompt(self):
        if not self.prompts_listbox.curselection():
            messagebox.showwarning(self.lm.get_string("warning_title"),
                                   self.lm.get_string("no_prompt_selected_delete_warning"), parent=self)
            return
        selected_index = self.prompts_listbox.curselection()[0]
        prompt_name = self.prompts_listbox.get(selected_index)
        if prompt_name == self.DEFAULT_SYSTEM_PROMPT_NAME:
            messagebox.showerror(self.lm.get_string("error_title"),
                                 self.lm.get_string("cannot_delete_default_prompt_error"), parent=self)
            return

        dialog_title = self.lm.get_string("confirm_delete_prompt_title")
        dialog_message = self.lm.get_string("confirm_delete_prompt_message", prompt_name=prompt_name)

        confirm_dialog = CustomAskYesNoDialog(self, dialog_title, dialog_message, self.lm)
        if confirm_dialog.show():
            if prompt_name in self.prompts_dict:
                del self.prompts_dict[prompt_name]
                self.populate_prompts_listbox()
                self.disable_editing_fields()
                messagebox.showinfo(self.lm.get_string("success_title"),
                                    self.lm.get_string("prompt_deleted_success", prompt_name=prompt_name), parent=self)
                # If the deleted prompt was the active one in settings, reset settings' active prompt to default
                if self.parent_app.active_prompt_name_var.get() == prompt_name:
                    self.parent_app.active_prompt_name_var.set(self.DEFAULT_SYSTEM_PROMPT_NAME)
                    # Also update the underlying settings dict in parent_app if it's directly accessible
                    if hasattr(self.parent_app, 'settings') and isinstance(self.parent_app.settings, dict):
                        self.parent_app.settings["active_system_prompt_name"] = self.DEFAULT_SYSTEM_PROMPT_NAME

    def duplicate_prompt(self):
        if not self.prompts_listbox.curselection():
            messagebox.showwarning(self.lm.get_string("warning_title"),
                                   self.lm.get_string("no_prompt_selected_duplicate_warning"), parent=self)
            return
        selected_index = self.prompts_listbox.curselection()[0]
        original_name = self.prompts_listbox.get(selected_index)
        original_agent_config = self.prompts_dict.get(original_name)
        if not original_agent_config or not isinstance(original_agent_config, dict): return  # Should not happen

        copy_suffix = self.lm.get_string("prompt_copy_suffix", default_text=" (copy)")
        copy_num_suffix_template = self.lm.get_string("prompt_copy_num_suffix", default_text=" (copy {num})")

        copy_num = 1
        new_name = f"{original_name}{copy_suffix}"
        while new_name in self.prompts_dict:
            copy_num += 1
            new_name = f"{original_name}{copy_num_suffix_template.format(num=copy_num)}"

        self.prompts_dict[
            new_name] = original_agent_config.copy()  # Deep copy if it contained mutable types, but current structure is fine with .copy()
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
        # Save prompts before closing
        if save_system_prompts(self.prompts_dict, self.lm):
            # Refresh options in the parent settings window (ModernSettingsApp)
            self.parent_app.refresh_prompt_options()
            self.destroy()