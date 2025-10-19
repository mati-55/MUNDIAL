# utils.py
import tkinter as tk
from tkinter import ttk
import os

def apply_style(root):
    style = ttk.Style(root)
    for th in ('clam','alt','default'):
        try:
            style.theme_use(th); break
        except Exception:
            pass
    primary = "#1565c0"
    light = "#eaf2ff"
    style.configure("TFrame", background=light)
    style.configure("TLabel", background=light, font=('Segoe UI', 11))
    style.configure("Header.TLabel", font=('Segoe UI', 14, 'bold'), background=light)
    style.configure("TButton", font=('Segoe UI', 10, 'bold'), padding=6)
    style.map("TButton", foreground=[('active','white')], background=[('active',primary),('!disabled',primary)])
    return style

def center_fullscreen(root):
    root.update_idletasks()
    if os.name == 'nt':
        root.state('zoomed')
    else:
        root.attributes('-fullscreen', True)

def small_center(root, w, h):
    ws = root.winfo_screenwidth(); hs = root.winfo_screenheight()
    x = (ws // 2) - (w // 2); y = (hs // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

def simple_prompt(root, title, prompt):
    win = tk.Toplevel(root)
    win.title(title)
    win.transient(root)
    win.focus_force()  # 🔹 Enfoca la ventana sin bloquear
    win.geometry("420x120")

    # posiciona centrado respecto al root
    x = root.winfo_x() + 50
    y = root.winfo_y() + 50
    win.geometry(f"+{x}+{y}")

    ttk.Label(win, text=prompt).pack(pady=8)
    entry = ttk.Entry(win, width=48)
    entry.pack(pady=6)

    val = {'text': None}

    def ok():
        val['text'] = entry.get()
        win.destroy()
        root.focus_force()  # vuelve el foco a la ventana principal

    ttk.Button(win, text="OK", command=ok).pack(pady=6)

    # ✅ Eliminamos grab_set y wait_window (que bloqueaban)
    # devolvemos el valor cuando se presione OK
    def get_value():
        return val['text']

    return get_value

