import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.font import Font
import sv_ttk  # Custom theme library for Tkinter

SETTINGS_FILE = "settings.json"

# Default settings if file is missing or invalid
default_settings = {
    "api_key": "",
    "chat_length": 10,
    "activation_word": "heybot",
    "stop_words": ["stop", "exit", "quit"]
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
        self.root.title("Bot Settings")

        # --- Set window icon ---
        try:
            icon_path = "icon.ico"  # Changed to .ico
            # Check if the icon file exists
            if os.path.exists(icon_path):
                # Use iconbitmap for .ico files
                self.root.iconbitmap(default=icon_path)
            else:
                print(f"Warning: Icon file '{icon_path}' not found for settings window.")
        except tk.TclError as e:
            # This can happen if the .ico file is not found, format is not supported, or other Tcl issues
            print(f"Warning: Could not load icon '{icon_path}' for settings window (TclError): {e}")
        except Exception as e:
            # Catch any other unexpected errors during icon loading
            print(f"Warning: An unexpected error occurred while setting icon for settings window: {e}")

        # Set minimum window size
        self.root.minsize(500, 400)

        # Apply Sun Valley theme (modern theme for tkinter)
        sv_ttk.set_theme("dark")  # Options: "light" or "dark"

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

        # --- API Key ---
        ttk.Label(
            settings_frame,
            text="API Key:",
            font=self.label_font
        ).grid(row=0, column=0, sticky="w", pady=10)

        self.api_key_var = tk.StringVar(value=self.settings.get("api_key", default_settings["api_key"]))
        api_key_entry = ttk.Entry(
            settings_frame,
            textvariable=self.api_key_var,
            width=40
        )
        api_key_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=10)

        # --- Chat Length ---
        ttk.Label(
            settings_frame,
            text="Chat Length:",
            font=self.label_font
        ).grid(row=1, column=0, sticky="w", pady=10)

        self.chat_length_var = tk.IntVar(value=self.settings.get("chat_length", default_settings["chat_length"]))
        chat_length_spinbox = ttk.Spinbox(
            settings_frame,
            from_=1,
            to=100,
            textvariable=self.chat_length_var,
            width=10
        )
        chat_length_spinbox.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=10)

        # --- Activation Word ---
        ttk.Label(
            settings_frame,
            text="Activation Word:",
            font=self.label_font
        ).grid(row=2, column=0, sticky="w", pady=10)

        self.activation_word_var = tk.StringVar(
            value=self.settings.get("activation_word", default_settings["activation_word"]))
        activation_word_entry = ttk.Entry(
            settings_frame,
            textvariable=self.activation_word_var
        )
        activation_word_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=10)

        # --- Stop Words ---
        ttk.Label(
            settings_frame,
            text="Stop Words:",
            font=self.label_font
        ).grid(row=3, column=0, sticky="w", pady=10)

        stop_words_str = ", ".join(self.settings.get("stop_words", default_settings["stop_words"]))
        self.stop_words_var = tk.StringVar(value=stop_words_str)
        stop_words_entry = ttk.Entry(
            settings_frame,
            textvariable=self.stop_words_var
        )
        stop_words_entry.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=10)
        ttk.Label(
            settings_frame,
            text="Separate words with commas",
            font=("Segoe UI", 8),
            foreground="gray"
        ).grid(row=4, column=1, sticky="w", padx=(10, 0))

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        # Create a separator above buttons
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=(10, 20))

        # Save and Cancel buttons
        save_button = ttk.Button(
            button_frame,
            text="Save Settings",
            command=self.save_and_close,  # Changed command
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

        # Ensure the window is modal if it's a Toplevel
        if isinstance(self.root, tk.Toplevel):
            self.root.grab_set()
            self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)  # Ensure X button works

    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        # Ensure width and height are not zero if window not fully rendered yet
        if width < 500: width = 500
        if height < 400: height = 400

        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def save_and_close(self):  # Renamed method for clarity
        try:
            # Validate chat_length before creating the dictionary
            chat_length_val = self.chat_length_var.get()
            if not isinstance(chat_length_val, int) or chat_length_val < 1:
                messagebox.showerror("Invalid Input", "Chat length must be a positive integer.")
                return  # Keep window open

            new_settings = {
                "api_key": self.api_key_var.get(),
                "chat_length": chat_length_val,
                "activation_word": self.activation_word_var.get(),
                "stop_words": [word.strip() for word in self.stop_words_var.get().split(",") if word.strip()]
            }

            # The save_settings function shows its own messagebox (success/error)
            # and returns True on success, False on failure.
            if save_settings(new_settings):
                self.root.destroy()  # Close the window only if save was successful
        except tk.TclError:  # Handles if chat_length_var.get() fails due to non-integer input in Spinbox
            messagebox.showerror("Invalid Input", "Chat length must be an integer.")
        except ValueError:  # Should be caught by TclError or explicit check, but as a fallback
            messagebox.showerror("Invalid Input", "Chat length must be an integer.")


if __name__ == "__main__":
    # You need to install sv_ttk library: pip install sv-ttk
    root = tk.Tk()
    # To test icon functionality when running settings.py directly,
    # ensure 'icon.ico' is in the same directory.
    # If sv_ttk is not installed, this will raise an error.
    try:
        app = ModernSettingsApp(root)
    except Exception as e:
        print(f"Error initializing ModernSettingsApp (likely sv_ttk missing or theme error): {e}")
        print("Please ensure 'sv_ttk' is installed: pip install sv-ttk")
        # Fallback to basic Tkinter if sv_ttk fails, for testing core logic
        root.title("Bot Settings (Basic Fallback)")
        tk.Label(root, text="Error loading modern theme. Basic fallback UI.").pack(pady=20)
        tk.Button(root, text="Close", command=root.destroy).pack(pady=10)

    root.mainloop()