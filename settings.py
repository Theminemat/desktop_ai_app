import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.font import Font
import sv_ttk  # Custom theme library for Tkinter

SETTINGS_FILE = "settings.json"

# Default settings if file is missing or invalid
default_settings = {
    "api_key": "Enter your Gemini API key here",
    "chat_length": 5,
    "activation_word": "Manfred",
    "stop_words": ["stop", "exit", "quit"],
    "open_links_automatically": True  # Neue Einstellung
}


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        # Create default settings file if it doesn't exist
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(default_settings, f, indent=4)
            print(f"'{SETTINGS_FILE}' not found. Created with default settings.")
            return default_settings.copy()
        except Exception as e:
            print(f"Error creating default settings file: {e}")
            return default_settings.copy()  # Fallback to in-memory defaults

    try:
        with open(SETTINGS_FILE, "r") as f:
            loaded = json.load(f)
            # Ensure all default keys are present
            updated = False
            for key, value in default_settings.items():
                if key not in loaded:
                    loaded[key] = value
                    updated = True
            if updated:
                print(f"'{SETTINGS_FILE}' was missing some keys. Updated with defaults.")
                # Optionally re-save the file with defaults for missing keys
                # save_settings(loaded) # Be careful with recursion or immediate messagebox here
            return loaded
    except Exception as e:
        print(f"Error loading settings: {e}. Returning default settings.")
        return default_settings.copy()


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
        messagebox.showinfo("Success", "Settings saved successfully!")
        return True  # Indicate success
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save settings:\n{e}")
        return False  # Indicate failure


class ModernSettingsApp:
    def __init__(self, root):
        self.root = root
        # --- Set window icon ---
        # Moved to be one of the first operations after root is assigned,
        # to ensure it's set as early as possible for the window.
        # This uses 'icon.ico' for the window/taskbar icon.
        try:
            icon_path = "icon.ico"
            if os.path.exists(icon_path):
                self.root.iconbitmap(default=icon_path)
            else:
                # Diese Warnung ist wichtig, wenn das Icon nicht gefunden wird.
                print(f"Warning: Icon file '{icon_path}' not found. Settings window will use default icon.")
        except tk.TclError as e:
            # Diese Fehlermeldung hilft bei Problemen mit dem Icon-Format oder Tkinter.
            print(f"Warning: Could not load icon '{icon_path}' for settings window (TclError): {e}")
        except Exception as e:
            # Fängt andere unerwartete Fehler beim Laden des Icons ab.
            print(f"Warning: An unexpected error occurred while setting icon for settings window: {e}")

        self.root.title("Bot Settings") # Title can be set after icon

        # Set minimum window size
        self.root.minsize(500, 450) # Increased height slightly for new setting

        # Apply Sun Valley theme (modern theme for tkinter)
        try:
            sv_ttk.set_theme("dark")  # Options: "light" or "dark"
        except Exception as e:
            print(f"Warning: Could not set sv_ttk theme: {e}. Using default Tkinter theme.")


        # Create custom fonts
        self.header_font = Font(family="Segoe UI", size=16, weight="bold")
        self.label_font = Font(family="Segoe UI", size=10)
        self.button_font = Font(family="Segoe UI", size=10, weight="bold")

        self.settings = load_settings()

        # Create main frame with padding
        main_frame = ttk.Frame(root, padding=(20, 20, 20, 20))
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        header_label = ttk.Label(
            header_frame,
            text="Bot Configuration",
            font=self.header_font
        )
        header_label.pack(side=tk.LEFT)

        # Settings container
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding=(15, 10))
        settings_frame.pack(fill=tk.BOTH, expand=True)

        # Grid layout for settings
        settings_frame.columnconfigure(1, weight=1)

        current_row = 0

        # --- API Key ---
        ttk.Label(
            settings_frame,
            text="API Key:",
            font=self.label_font
        ).grid(row=current_row, column=0, sticky="w", pady=10)

        self.api_key_var = tk.StringVar(value=self.settings.get("api_key", default_settings["api_key"]))
        api_key_entry = ttk.Entry(
            settings_frame,
            textvariable=self.api_key_var,
            width=40
        )
        api_key_entry.grid(row=current_row, column=1, sticky="ew", padx=(10, 0), pady=10)
        current_row += 1

        # --- Chat Length ---
        ttk.Label(
            settings_frame,
            text="Chat Length:",
            font=self.label_font
        ).grid(row=current_row, column=0, sticky="w", pady=10)

        self.chat_length_var = tk.IntVar(value=self.settings.get("chat_length", default_settings["chat_length"]))
        chat_length_spinbox = ttk.Spinbox(
            settings_frame,
            from_=1,
            to=100,
            textvariable=self.chat_length_var,
            width=10
        )
        chat_length_spinbox.grid(row=current_row, column=1, sticky="w", padx=(10, 0), pady=10)
        current_row += 1

        # --- Activation Word ---
        ttk.Label(
            settings_frame,
            text="Activation Word:",
            font=self.label_font
        ).grid(row=current_row, column=0, sticky="w", pady=10)

        self.activation_word_var = tk.StringVar(
            value=self.settings.get("activation_word", default_settings["activation_word"]))
        activation_word_entry = ttk.Entry(
            settings_frame,
            textvariable=self.activation_word_var
        )
        activation_word_entry.grid(row=current_row, column=1, sticky="ew", padx=(10, 0), pady=10)
        current_row += 1

        # --- Stop Words ---
        ttk.Label(
            settings_frame,
            text="Stop Words:",
            font=self.label_font
        ).grid(row=current_row, column=0, sticky="w", pady=10)

        stop_words_str = ", ".join(self.settings.get("stop_words", default_settings["stop_words"]))
        self.stop_words_var = tk.StringVar(value=stop_words_str)
        stop_words_entry = ttk.Entry(
            settings_frame,
            textvariable=self.stop_words_var
        )
        stop_words_entry.grid(row=current_row, column=1, sticky="ew", padx=(10, 0), pady=10)
        current_row += 1
        ttk.Label(
            settings_frame,
            text="Separate words with commas",
            font=("Segoe UI", 8), # Smaller font for hint
            foreground="gray" # Muted color for hint
        ).grid(row=current_row, column=1, sticky="w", padx=(10, 0))
        current_row += 1


        # --- Open Links Automatically ---
        ttk.Label(
            settings_frame,
            text="Open Links in Browser:",
            font=self.label_font
        ).grid(row=current_row, column=0, sticky="w", pady=10)

        self.open_links_var = tk.BooleanVar(
            value=self.settings.get("open_links_automatically", default_settings["open_links_automatically"])
        )
        open_links_checkbutton = ttk.Checkbutton(
            settings_frame,
            variable=self.open_links_var,
            text="Automatically open detected links"
        )
        open_links_checkbutton.grid(row=current_row, column=1, sticky="w", padx=(10,0), pady=10)
        current_row += 1


        # Buttons frame
        # Create a separator above buttons for better visual separation
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=(10, 10), before=settings_frame, side=tk.BOTTOM) # Pack separator before buttons

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0), side=tk.BOTTOM) # Buttons at the very bottom


        # Save and Cancel buttons
        save_button = ttk.Button(
            button_frame,
            text="Save Settings",
            command=self.save_and_close,
            style="Accent.TButton"  # Sun Valley theme accent button
        )
        save_button.pack(side=tk.RIGHT, padx=5)

        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.root.destroy
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)

        # Center the window
        self.center_window()

        # Ensure the window is modal if it's a Toplevel (e.g., opened from main app)
        if isinstance(self.root, tk.Toplevel):
            self.root.grab_set()  # Makes the window modal
            self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)  # Ensure X button closes modal window

    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks() # Process pending Tkinter events to get correct window size
        width = self.root.winfo_width()
        height = self.root.winfo_height()

        min_w, min_h = self.root.minsize()
        if width < min_w: width = min_w
        if height < min_h: height = min_h

        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def save_and_close(self):
        try:
            # Validate chat_length before creating the dictionary
            chat_length_val = self.chat_length_var.get() # This can raise TclError if not int
            # The isinstance check is somewhat redundant due to TclError catch but good for clarity
            if not isinstance(chat_length_val, int) or chat_length_val < 1:
                messagebox.showerror("Invalid Input", "Chat length must be a positive integer.")
                return

            new_settings = {
                "api_key": self.api_key_var.get(),
                "chat_length": chat_length_val,
                "activation_word": self.activation_word_var.get(),
                "stop_words": [word.strip() for word in self.stop_words_var.get().split(",") if word.strip()],
                "open_links_automatically": self.open_links_var.get() # Speichern der neuen Einstellung
            }

            if save_settings(new_settings): # save_settings shows its own success/error messagebox
                self.root.destroy() # Close window only if save was successful
        except tk.TclError: # Catches errors from .get() if spinbox/entry has invalid content for IntVar
            messagebox.showerror("Invalid Input", "Chat length must be a valid integer.")
        except ValueError: # Should ideally be caught by TclError for IntVar, but as a fallback
            messagebox.showerror("Invalid Input", "Chat length must be an integer (ValueError).")


if __name__ == "__main__":
    # This block is for testing settings.py directly.
    # You need to install sv_ttk library: pip install sv-ttk
    root = tk.Tk()

    # --- Set icon for the main Tk() window if run directly ---
    try:
        icon_path_main = "icon.ico"
        if os.path.exists(icon_path_main):
            root.iconbitmap(default=icon_path_main)
            print(f"Main window icon set to '{icon_path_main}' for direct execution.")
        else:
            print(f"Warning: Icon file '{icon_path_main}' not found for main window (direct execution).")
    except Exception as e:
        print(f"Warning: Could not set main window icon (direct execution): {e}")


    try:
        app = ModernSettingsApp(root)
    except NameError as e: # sv_ttk might not be defined if import failed
        print(f"Error initializing ModernSettingsApp (likely sv_ttk missing or import error): {e}")
        print("Please ensure 'sv_ttk' is installed: pip install sv-ttk")
        root.title("Bot Settings (Basic Fallback)")
        ttk.Label(root, text="Error loading modern theme. sv_ttk might be missing. Basic fallback UI.").pack(pady=20)
        ttk.Button(root, text="Close", command=root.destroy).pack(pady=10)
    except Exception as e:
        print(f"An unexpected error occurred initializing ModernSettingsApp: {e}")
        root.title("Bot Settings (Error)")
        ttk.Label(root, text=f"Could not initialize settings UI: {e}").pack(pady=20)
        ttk.Button(root, text="Close", command=root.destroy).pack(pady=10)

    root.mainloop()