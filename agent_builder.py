# C:/Users/Theminemat/Documents/Programming/manfred desktop ai/agent_builder.py
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox  # Keep messagebox for showinfo, showerror, etc.
from tkinter.scrolledtext import ScrolledText
import sys

# Constants related to system prompts
SYSPROMPTS_FILE = "sysprompts.json"
SYSTEM_PROMPT_SUFFIX = (
    "\n\nGenerate the reply so that a simple TTS can read it correctly. "
    "\nYou can open links on my PC by just including them in your message without formatting; "
    "just start links with https://. Also use this when the user asks you to search on a website like YouTube."
)


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
    if not os.path.exists(SYSPROMPTS_FILE):
        try:
            with open(SYSPROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump({default_prompt_name: default_prompt_text}, f, indent=4, ensure_ascii=False)
            print(f"'{SYSPROMPTS_FILE}' not found. Created with default system prompt.")
            return {default_prompt_name: default_prompt_text}
        except Exception as e:
            print(f"Error creating default system prompts file: {e}")
            return {default_prompt_name: default_prompt_text}

    try:
        with open(SYSPROMPTS_FILE, "r", encoding="utf-8") as f:
            prompts = json.load(f)
            if not isinstance(prompts, dict) or not prompts:
                raise ValueError("Invalid format or empty prompts file.")
            if default_prompt_name not in prompts:
                prompts[default_prompt_name] = default_prompt_text
                _save_prompts_internal(prompts)  # Internal save without messagebox
                print(f"Default system prompt was missing from '{SYSPROMPTS_FILE}'. Added and saved.")
            return prompts
    except Exception as e:
        print(f"Error loading system prompts: {e}. Returning default prompt.")
        return {default_prompt_name: default_prompt_text}


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
            messagebox.showerror(lm.get_string("error_title"), lm.get_string("failed_to_save_prompts_error", e=e))
        else:
            messagebox.showerror("Error", f"Failed to save system prompts:\n{e}")
        return False


def get_full_system_prompt(prompt_name, all_prompts, activation_word, default_prompt_text_if_missing):
    base_text = all_prompts.get(prompt_name, default_prompt_text_if_missing)
    base_text = base_text.replace("{name}", activation_word)
    return base_text + SYSTEM_PROMPT_SUFFIX


class SystemPromptManagerWindow(tk.Toplevel):
    def __init__(self, master_widget, app_instance, lm, default_prompt_name_const, default_prompt_text_const):
        super().__init__(master_widget)
        self.parent_app = app_instance
        self.lm = lm
        self.DEFAULT_SYSTEM_PROMPT_NAME = default_prompt_name_const
        self.DEFAULT_SYSTEM_PROMPT_TEXT = default_prompt_text_const

        self.grab_set()
        self.prompts_dict = load_system_prompts(self.DEFAULT_SYSTEM_PROMPT_NAME, self.DEFAULT_SYSTEM_PROMPT_TEXT)

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
        self.save_button_editor = ttk.Button(edit_actions_frame, command=self.save_edited_prompt, state=tk.DISABLED)
        self.save_button_editor.pack(side=tk.LEFT, padx=2)
        self.cancel_button_editor = ttk.Button(edit_actions_frame, command=self.cancel_edit, state=tk.DISABLED)
        self.cancel_button_editor.pack(side=tk.LEFT, padx=2)

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
            is_dark_theme = False
            if 'sv_ttk' in sys.modules:
                try:
                    current_theme = sys.modules['sv_ttk'].get_theme()
                    if current_theme.lower() == "dark":
                        is_dark_theme = True
                except (AttributeError, tk.TclError):
                    pass

            bg_color_text_widget = style.lookup('TEntry', 'fieldbackground')
            fg_color_text_widget = style.lookup('TEntry', 'foreground')

            if not bg_color_text_widget:
                bg_color_text_widget = style.lookup('TFrame', 'background') or ("#2b2b2b" if is_dark_theme else "white")
            if not fg_color_text_widget:
                fg_color_text_widget = style.lookup('TFrame', 'foreground') or ("#cccccc" if is_dark_theme else "black")

            self.prompt_text_widget.configure(bg=bg_color_text_widget, fg=fg_color_text_widget,
                                              insertbackground=fg_color_text_widget)
        except Exception as e:
            print(f"Error styling ScrolledText: {e}. Using defaults.")
            is_dark_theme_fallback = 'sv_ttk' in sys.modules
            safe_bg, safe_fg = ("#2b2b2b", "#cccccc") if is_dark_theme_fallback else ("white", "black")
            self.prompt_text_widget.configure(bg=safe_bg, fg=safe_fg, insertbackground=safe_fg)

    def retranslate_ui(self):
        self.title(self.lm.get_string("prompt_manager_title"))
        self.prompts_list_label.configure(text=self.lm.get_string("prompts_list_label"))
        self.new_button.configure(text=self.lm.get_string("new_prompt_button"))
        self.duplicate_button.configure(text=self.lm.get_string("duplicate_prompt_button"))
        self.delete_button.configure(text=self.lm.get_string("delete_prompt_button"))
        self.prompt_name_label_widget.configure(text=self.lm.get_string("prompt_name_label"))
        self.prompt_text_label_widget.configure(text=self.lm.get_string("prompt_text_label"))
        self.save_button_editor.configure(text=self.lm.get_string("save_changes_button"))
        self.cancel_button_editor.configure(text=self.lm.get_string("cancel_edit_button"))
        self.close_manager_button.configure(text=self.lm.get_string("close_manager_button"))

        current_save_button_text = self.save_button_editor.cget("text")
        expected_save_changes_text = self.lm.get_string("save_changes_button")

        if current_save_button_text != expected_save_changes_text and \
                self.selected_prompt_original_name is None:
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
        self.prompt_name_var.set(prompt_name)
        self.prompt_text_widget.configure(state=tk.NORMAL)
        self.prompt_text_widget.delete("1.0", tk.END)
        self.prompt_text_widget.insert("1.0", self.prompts_dict.get(prompt_name, ""))
        self.enable_editing_fields()
        if prompt_name == self.DEFAULT_SYSTEM_PROMPT_NAME:
            self.prompt_name_entry.configure(state=tk.DISABLED)
        else:
            self.prompt_name_entry.configure(state=tk.NORMAL)
        self.save_button_editor.configure(text=self.lm.get_string("save_changes_button"))

    def enable_editing_fields(self):
        self.prompt_name_entry.configure(state=tk.NORMAL)
        self.prompt_text_widget.configure(state=tk.NORMAL)
        self.save_button_editor.configure(state=tk.NORMAL)
        self.cancel_button_editor.configure(state=tk.NORMAL)

    def disable_editing_fields(self):
        self.prompt_name_var.set("")
        self.prompt_text_widget.delete("1.0", tk.END)
        self.prompt_name_entry.configure(state=tk.DISABLED)
        self.prompt_text_widget.configure(state=tk.DISABLED)
        self.save_button_editor.configure(state=tk.DISABLED)
        self.cancel_button_editor.configure(state=tk.DISABLED)
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
        self.save_button_editor.configure(text=self.lm.get_string("save_new_prompt_button"))

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
                if self.selected_prompt_original_name == self.DEFAULT_SYSTEM_PROMPT_NAME:
                    messagebox.showerror(self.lm.get_string("error_title"),
                                         self.lm.get_string("cannot_rename_default_prompt_error"), parent=self)
                    self.prompt_name_var.set(self.DEFAULT_SYSTEM_PROMPT_NAME)
                    return
                del self.prompts_dict[self.selected_prompt_original_name]

        elif self.selected_prompt_original_name == self.DEFAULT_SYSTEM_PROMPT_NAME and new_name != self.DEFAULT_SYSTEM_PROMPT_NAME:
            messagebox.showerror(self.lm.get_string("error_title"),
                                 self.lm.get_string("cannot_rename_default_prompt_error"), parent=self)
            self.prompt_name_var.set(self.DEFAULT_SYSTEM_PROMPT_NAME)
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
        if prompt_name == self.DEFAULT_SYSTEM_PROMPT_NAME:
            messagebox.showerror(self.lm.get_string("error_title"),
                                 self.lm.get_string("cannot_delete_default_prompt_error"), parent=self)
            return

        dialog_title = self.lm.get_string("confirm_delete_prompt_title")
        dialog_message = self.lm.get_string("confirm_delete_prompt_message", prompt_name=prompt_name)

        confirm_dialog = CustomAskYesNoDialog(self, dialog_title, dialog_message, self.lm)
        if confirm_dialog.show():  # This will block until dialog is closed
            if prompt_name in self.prompts_dict:
                del self.prompts_dict[prompt_name]
                self.populate_prompts_listbox()
                self.disable_editing_fields()
                messagebox.showinfo(self.lm.get_string("success_title"),
                                    self.lm.get_string("prompt_deleted_success", prompt_name=prompt_name), parent=self)
                if self.parent_app.active_prompt_name_var.get() == prompt_name:
                    self.parent_app.active_prompt_name_var.set(self.DEFAULT_SYSTEM_PROMPT_NAME)
                    if hasattr(self.parent_app, 'settings') and isinstance(self.parent_app.settings, dict):
                        self.parent_app.settings["active_system_prompt_name"] = self.DEFAULT_SYSTEM_PROMPT_NAME

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