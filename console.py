# C:/Users/Theminemat/Documents/Programming/manfred desktop ai/console.py
import tkinter as tk
from tkinter import messagebox, scrolledtext
from collections import deque
import sys
import os

# --- Console Globals ---
MAX_CONSOLE_LINES = 2000  # Max lines to keep in the console log cache
console_log_cache = deque(maxlen=MAX_CONSOLE_LINES)
_console_window_text_widget = None  # Reference to the ScrolledText widget in the console window
_console_window_instance = None  # Reference to the ConsoleWindow instance

# Original stream references, will be set by init_output_redirection
_original_sys_stdout = None
_original_sys_stderr = None
_stdout_redirector = None
_stderr_redirector = None

def resource_path_local(relative_path): # Eigene Definition oder Import von main
     try:
         base_path = sys._MEIPASS
     except Exception:
         base_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
     return os.path.join(base_path, relative_path)



def get_console_text_widget_instance():
    global _console_window_text_widget
    return _console_window_text_widget


def get_console_window_instance():
    global _console_window_instance
    return _console_window_instance


class OutputRedirector:
    def __init__(self, original_stream, cache_deque_ref, text_widget_ref_func):
        self.original_stream = original_stream
        self.cache = cache_deque_ref
        self.get_text_widget = text_widget_ref_func

    def write(self, text):
        if self.original_stream:
            try:
                self.original_stream.write(text)
                self.original_stream.flush()
            except Exception:  # pragma: no cover
                # Ignore errors writing to original stream if it's closed/problematic
                # This can happen during shutdown if original_stream is already closed
                if not (isinstance(self.original_stream,
                                   (type(sys.stdout), type(sys.stderr))) and self.original_stream.closed):
                    pass  # Avoid printing if it's a standard stream that's closed

        self.cache.append(text)
        text_widget = self.get_text_widget()
        if text_widget and text_widget.winfo_exists():
            try:
                # Ensure UI update is done in the main thread via the widget's master's 'after'
                text_widget.master.after(0, self._update_text_widget_safely, text, text_widget)
            except (tk.TclError, AttributeError):  # Widget might be destroyed or not fully initialized
                pass

    def _update_text_widget_safely(self, text, widget_instance):
        # This method is called by 'after' and runs in the main Tkinter thread
        if widget_instance and widget_instance.winfo_exists():
            current_state = widget_instance.cget("state")
            widget_instance.configure(state=tk.NORMAL)
            widget_instance.insert(tk.END, text)
            widget_instance.see(tk.END)
            widget_instance.configure(state=current_state)

    def flush(self):
        if self.original_stream:
            try:
                self.original_stream.flush()
            except Exception:  # pragma: no cover
                pass


def init_output_redirection():
    global _original_sys_stdout, _original_sys_stderr, _stdout_redirector, _stderr_redirector
    global console_log_cache  # Ensure it's using the global deque from this module

    if _original_sys_stdout is None:  # Initialize only once
        _original_sys_stdout = sys.stdout
        _original_sys_stderr = sys.stderr

        _stdout_redirector = OutputRedirector(_original_sys_stdout, console_log_cache, get_console_text_widget_instance)
        _stderr_redirector = OutputRedirector(_original_sys_stderr, console_log_cache, get_console_text_widget_instance)

        sys.stdout = _stdout_redirector
        sys.stderr = _stderr_redirector
        print("Console output redirection initialized.")


class ConsoleWindow(tk.Toplevel):
    def __init__(self, master, cache_deque_ref, lang_manager):
        global _console_window_text_widget, _console_window_instance
        super().__init__(master)
        self.lm = lang_manager
        self.title(self.lm.get_string("console_window_title", default_text="Application Console"))
        self.geometry("800x500")
        try:
            icon_path = resource_path_local("icon.ico")
            if os.path.exists(icon_path): self.iconbitmap(default=icon_path)
        except Exception as e:
            # This print will go through the redirector
            print(f"Warning: Could not set icon for console window: {e}")

        self.cache = cache_deque_ref
        _console_window_instance = self  # Set global instance reference

        self.text_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, state=tk.DISABLED, height=20)
        self.text_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        _console_window_text_widget = self.text_area  # Set global reference for redirector

        self.text_area.configure(state=tk.NORMAL)
        self.text_area.insert(tk.END, "".join(list(self.cache)))
        self.text_area.see(tk.END)
        self.text_area.configure(state=tk.DISABLED)

        button_frame = tk.Frame(self)
        button_frame.pack(fill=tk.X, pady=5, padx=5)

        try:
            from tkinter import ttk
            clear_button = ttk.Button(button_frame,
                                      text=self.lm.get_string("console_clear_button", default_text="Clear"),
                                      command=self.clear_console)
        except ImportError:
            clear_button = tk.Button(button_frame,
                                     text=self.lm.get_string("console_clear_button", default_text="Clear"),
                                     command=self.clear_console)
        clear_button.pack(side=tk.RIGHT)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.center_window()

    def clear_console(self):
        self.cache.clear()
        if _console_window_text_widget and _console_window_text_widget.winfo_exists():
            _console_window_text_widget.configure(state=tk.NORMAL)
            _console_window_text_widget.delete('1.0', tk.END)
            _console_window_text_widget.configure(state=tk.DISABLED)
        # This print will also go to the (now empty) console
        print("Console display cleared by user.")

    def on_close(self):
        global _console_window_text_widget, _console_window_instance
        _console_window_text_widget = None
        _console_window_instance = None
        self.destroy()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')


def show_console_window(parent_tk_master, lang_manager_instance):
    global _console_window_instance, console_log_cache  # console_log_cache is from this module

    if _console_window_instance and _console_window_instance.winfo_exists():
        _console_window_instance.lift()
        _console_window_instance.focus_force()
        return

    actual_master_for_console = None
    if parent_tk_master and parent_tk_master.winfo_exists():
        actual_master_for_console = parent_tk_master
    else:
        # This print will go through the redirector
        print("Parent (overlay) not found or destroyed, trying to create console as standalone/on default root.")
        try:
            if tk._default_root and tk._default_root.winfo_exists():
                actual_master_for_console = tk._default_root
            else:
                # No good parent, show error if lang_manager_instance is available
                if lang_manager_instance:
                    messagebox.showerror(
                        lang_manager_instance.get_string("error_title", default_text="Error"),
                        lang_manager_instance.get_string("overlay_not_available_error",
                                                         default_text="Main application window not available to host the console.")
                        # Parent for messagebox is None as we don't have a good one
                    )
                else:  # Cannot even show a localized messagebox
                    messagebox.showerror("Error", "Main application window not available to host the console.")
                return
        except Exception as e:
            print(f"Error determining parent for console window: {e}")
            if lang_manager_instance:
                messagebox.showerror(
                    lang_manager_instance.get_string("error_title", default_text="Error"),
                    lang_manager_instance.get_string("overlay_not_available_error",
                                                     default_text="Cannot open console: main window context lost.")
                )
            else:
                messagebox.showerror("Error", "Cannot open console: main window context lost.")
            return

    # _console_window_instance is set inside ConsoleWindow's __init__
    ConsoleWindow(actual_master_for_console, console_log_cache, lang_manager_instance)
