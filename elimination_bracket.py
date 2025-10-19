import tkinter as tk
from tkinter import messagebox
import pandas as pd
from PIL import Image, ImageTk
import os

class EliminationBracketUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Copa del Mundo Sub-20 | Llaves de Eliminación")
        self.master.configure(bg="#0e1621")
        self.master.geometry("1300x700")

        self.canvas = tk.Canvas(self.master, bg="#0e1621", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.images = []  # evitar que las banderas sean recolectadas por el GC

        self.load_data()
        self.draw_trophy()

    # -----------------------------------------------------------------
    def load_data(self):
        """Lee los datos desde el Excel y construye las llaves."""
        try:
            df = pd.read_excel("partidos.xlsx")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer 'partidos.xlsx': {e}")
            return

        fases = ["Octavos", "Cuartos", "Semifinal", "Final"]
        x_positions = [150, 450, 750, 1050]
        y_start = 120
        y_spacing = 80

        for i, fase in enumerate(fases):
            subset = df[df["Fase"].str.lower() == fase.lower()]
            y = y_start
            self.canvas.create_text(x_positions[i], 50, text=fase, fill="white", font=("Arial", 12, "bold"))

            for _, row in subset.iterrows():
                self.draw_match(x_positions[i], y, row)
                y += y_spacing * 2

    # -----------------------------------------------------------------
    def draw_match(self, x, y, row):
        """Dibuja un partido con banderas, nombres y marcador."""
        eq1, eq2 = row["EquipoA"], row["EquipoB"]
        g1, g2 = row["GolesA"], row["GolesB"]

        # Cargar banderas
        bandera1 = self.load_flag(eq1)
        bandera2 = self.load_flag(eq2)

        if bandera1:
            self.canvas.create_image(x - 70, y, image=bandera1)
            self.images.append(bandera1)
        if bandera2:
            self.canvas.create_image(x - 70, y + 40, image=bandera2)
            self.images.append(bandera2)

        # Nombres
        self.canvas.create_text(x, y, text=eq1, fill="white", anchor="w", font=("Arial", 10, "bold"))
        self.canvas.create_text(x, y + 40, text=eq2, fill="white", anchor="w", font=("Arial", 10, "bold"))

        # Marcadores
        self.canvas.create_rectangle(x + 150, y - 10, x + 190, y + 10, fill="#007bff", outline="")
        self.canvas.create_rectangle(x + 150, y + 30, x + 190, y + 50, fill="#007bff", outline="")
        self.canvas.create_text(x + 170, y, text=str(g1), fill="white", font=("Arial", 10, "bold"))
        self.canvas.create_text(x + 170, y + 40, text=str(g2), fill="white", font=("Arial", 10, "bold"))

        # Línea de conexión
        self.canvas.create_line(x + 190, y + 20, x + 220, y + 20, fill="white", width=1)

    # -----------------------------------------------------------------
    def draw_trophy(self):
        """Dibuja el trofeo y los datos del partido final en el centro."""
        trophy_path = os.path.join("banderas", "trophy.png")
        if os.path.exists(trophy_path):
            trophy_img = Image.open(trophy_path).resize((80, 100))
            trophy = ImageTk.PhotoImage(trophy_img)
            self.canvas.create_image(650, 330, image=trophy)
            self.images.append(trophy)

        self.canvas.create_text(650, 450, text="Final - Estadio Nacional Julio Martínez Prádanos\n08/10/2025 - 16:30",
                                fill="white", font=("Arial", 12, "bold"), justify="center")

    # -----------------------------------------------------------------
    def load_flag(self, country_name):
        """Carga la bandera si existe, redimensionada a 40x25 px."""
        path = os.path.join("banderas", f"{country_name}.png")
        if not os.path.exists(path):
            return None
        try:
            img = Image.open(path).resize((40, 25))
            return ImageTk.PhotoImage(img)
        except Exception:
            return None
