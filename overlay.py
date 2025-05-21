import tkinter as tk
import os
import numpy as np


# Kein 'from threading import Event' hier, da es übergeben wird
def resource_path_local(relative_path):  # Eigene Definition oder Import von main
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)

class ModernOverlay(tk.Tk):
    def __init__(self, speech_stop_event_ref):  # speech_stop_event wird jetzt übergeben
        super().__init__()
        self.speech_stop_event = speech_stop_event_ref  # Referenz speichern

        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.9)
        self.config(bg='#0D1117')

        # --- Set Overlay Icon ---
        try:
            overlay_icon_path = resource_path_local("icon.ico")
            if os.path.exists(overlay_icon_path):
                self.iconbitmap(default=overlay_icon_path)
            else:
                print(f"Warning: Icon file '{overlay_icon_path}' not found for overlay window.")
        except tk.TclError as e:
            print(f"Warning: Could not load icon '{overlay_icon_path}' for overlay window (TclError): {e}")
        except Exception as e:
            print(f"Warning: An unexpected error occurred while setting icon for overlay window: {e}")

        self.corner_radius = 20
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = 280
        height = 80
        x_pos = screen_width - width - 20
        y_pos = screen_height - height - 50
        self.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

        self.canvas = tk.Canvas(self, width=width, height=height, bg='#0D1117', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.create_rectangle(self.corner_radius, 0, width - self.corner_radius, height, fill='#0D1117',
                                     outline='')
        self.canvas.create_rectangle(0, self.corner_radius, width, height - self.corner_radius, fill='#0D1117',
                                     outline='')
        self.canvas.create_arc(0, 0, self.corner_radius * 2, self.corner_radius * 2, start=90, extent=90,
                               fill='#0D1117', outline='')
        self.canvas.create_arc(width - self.corner_radius * 2, 0, width, self.corner_radius * 2, start=0, extent=90,
                               fill='#0D1117', outline='')
        self.canvas.create_arc(0, height - self.corner_radius * 2, self.corner_radius * 2, height, start=180, extent=90,
                               fill='#0D1117', outline='')
        self.canvas.create_arc(width - self.corner_radius * 2, height - self.corner_radius * 2, width, height,
                               start=270, extent=90, fill='#0D1117', outline='')

        self.border = self.canvas.create_rectangle(2, 2, width - 2, height - 2, outline='#1E90FF', width=2)

        self.mode = None
        self.orb_size = 36
        self.orb_x = 40
        self.orb_y = height // 2

        gradient = []
        for i in range(100):
            r = int(0 + (64 * i / 100))
            g = int(170 + (50 * i / 100))
            b = int(210 + (45 * i / 100))
            gradient.append(f'#{r:02x}{g:02x}{b:02x}')
        self.gradient = gradient

        self.orb_id = self.canvas.create_oval(
            self.orb_x - self.orb_size // 2, self.orb_y - self.orb_size // 2,
            self.orb_x + self.orb_size // 2, self.orb_y + self.orb_size // 2,
            fill='#10AFCF', width=0)
        self.highlight_id = self.canvas.create_oval(
            self.orb_x - self.orb_size // 3, self.orb_y - self.orb_size // 3,
            self.orb_x - 2, self.orb_y - 2,
            fill='white', width=0)

        self.font = ("Segoe UI", 14, "bold")
        self.text_id = self.canvas.create_text(
            self.orb_x + self.orb_size // 2 + 20, height // 2,
            anchor='w', text="", fill='#10DFFF', font=self.font)

        self.particles = []
        self.max_particles = 15
        self.pulse_direction = 1
        self.pulse_size = 0
        self.pulse_speed = 0.05
        self.pulse_max = 10
        self.listening_speed = 0.05
        self.speaking_speed = 0.12
        self.particle_chance = 0.05

        self.canvas.bind("<Button-1>", self.on_click)
        self.withdraw()
        self.after(20, self._animate)

    def on_click(self, event):
        if self.mode == 'speaking':
            self.speech_stop_event.set()  # Verwendet die übergebene Referenz

    def set_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        if mode == 'listening':
            self.canvas.itemconfig(self.orb_id, fill='#10EFCF')
            self.canvas.itemconfig(self.text_id, text="Höre zu...", fill='#10EFCF')
            self.canvas.itemconfig(self.border, outline='#10EFCF')
            self.pulse_speed = self.listening_speed
            self.particle_chance = 0.05
            self.show()
        elif mode == 'speaking':
            self.canvas.itemconfig(self.orb_id, fill='#10AFCF')
            self.canvas.itemconfig(self.text_id, text="Spreche...", fill='#10DFFF')
            self.canvas.itemconfig(self.border, outline='#1E90FF')
            self.pulse_speed = self.speaking_speed
            self.particle_chance = 0.2
            self.speech_stop_event.clear()  # Hier wird das Event auch gecleart
            self.show()
        else:
            self.hide()
        self.particles = []

    def show(self):
        if not self.winfo_viewable():
            self.deiconify()

    def hide(self):
        if self.winfo_viewable():
            self.withdraw()

    def _create_particle(self):
        if len(self.particles) >= self.max_particles: return
        angle = np.random.uniform(0, 2 * np.pi)
        speed = np.random.uniform(0.5, 2.0)
        if self.mode == 'speaking': speed *= 1.5
        size = np.random.uniform(2, 6)
        distance = np.random.uniform(0, 10)
        x = self.orb_x + distance * np.cos(angle)
        y = self.orb_y + distance * np.sin(angle)
        colors = ['#10AFCF', '#1E90FF', '#00CED1', '#48D1CC', '#20B2AA']
        color = np.random.choice(colors)
        particle = {
            'id': self.canvas.create_oval(x - size / 2, y - size / 2, x + size / 2, y + size / 2, fill=color, width=0),
            'dx': speed * np.cos(angle), 'dy': speed * np.sin(angle),
            'ttl': np.random.uniform(10, 30), 'fade': np.random.uniform(0.92, 0.98)}
        self.particles.append(particle)

    def _update_particles(self):
        particles_to_remove = []
        for i, p in enumerate(self.particles):
            self.canvas.move(p['id'], p['dx'], p['dy'])
            p['ttl'] -= 1
            if p['ttl'] <= 0:
                particles_to_remove.append(i)
                self.canvas.delete(p['id'])
            else:
                x1, y1, x2, y2 = self.canvas.coords(p['id'])
                width, height = x2 - x1, y2 - y1
                new_width, new_height = width * p['fade'], height * p['fade']
                center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
                self.canvas.coords(p['id'], center_x - new_width / 2, center_y - new_height / 2,
                                   center_x + new_width / 2, center_y + new_height / 2)
        for i in sorted(particles_to_remove, reverse=True):
            self.particles.pop(i)

    def _animate(self):
        self.pulse_size += self.pulse_speed * self.pulse_direction
        if self.pulse_size > self.pulse_max or self.pulse_size < 0:
            self.pulse_direction *= -1
        size = self.orb_size + self.pulse_size
        self.canvas.coords(self.orb_id, self.orb_x - size // 2, self.orb_y - size // 2,
                           self.orb_x + size // 2, self.orb_y + size // 2)
        highlight_size = size * 0.6
        self.canvas.coords(self.highlight_id, self.orb_x - highlight_size // 2,
                           self.orb_y - highlight_size // 2, self.orb_x, self.orb_y)

        if self.mode == 'listening':
            pulse_factor = abs(self.pulse_size / self.pulse_max)
            color_idx = int(20 + pulse_factor * 30)
            self.canvas.itemconfig(self.orb_id, fill=self.gradient[color_idx])
            if np.random.random() < self.particle_chance: self._create_particle()
        elif self.mode == 'speaking':
            pulse_factor = abs(self.pulse_size / self.pulse_max)
            color_idx = int(40 + pulse_factor * 50)
            self.canvas.itemconfig(self.orb_id, fill=self.gradient[min(99, color_idx)])
            if np.random.random() < self.particle_chance: self._create_particle()

        self._update_particles()
        self.after(20, self._animate)


# Optional: Testblock für overlay.py, falls du es isoliert testen möchtest
if __name__ == '__main__':
    from threading import Event

    # Ein Dummy-Event für Testzwecke
    dummy_speech_stop_event = Event()

    app = ModernOverlay(dummy_speech_stop_event)
    app.set_mode('listening')  # Zum Testen direkt einen Modus setzen


    def toggle_mode():
        if app.mode == 'listening':
            app.set_mode('speaking')
        else:
            app.set_mode('listening')
        app.after(3000, toggle_mode)  # Alle 3 Sekunden Modus wechseln


    app.after(3000, toggle_mode)
    app.mainloop()