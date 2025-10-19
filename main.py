import tkinter as tk
from assigner import GroupAssigner
from phase_groups import PhaseGroupsUI
from elimination import EliminationUI
from utils import apply_style, center_fullscreen
from datetime import datetime
from informes.informes import InformesUI
from elimination_bracket import EliminationBracketUI
import pandas as pd
import os

# ====================================================
# 🟦 Encabezado institucional
# ====================================================
def crear_encabezado(ventana):
    header_frame = tk.Frame(ventana, bg="#003366", padx=10, pady=5)
    header_frame.pack(fill="x")

    asignatura = "Algoritmos y Estructuras de Datos II"
    aplicacion = "Copa del Mundo Sub-20"

    lbl_titulo = tk.Label(
        header_frame,
        text=f"{asignatura}  |  {aplicacion}",
        bg="#003366", fg="white", font=("Arial", 14, "bold")
    )
    lbl_titulo.pack(side="left", padx=10)

    lbl_hora = tk.Label(header_frame, bg="#003366", fg="white", font=("Arial", 12))
    lbl_hora.pack(side="right", padx=10)

    def actualizar_hora():
        lbl_hora.config(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        lbl_hora.after(1000, actualizar_hora)
    actualizar_hora()

# ====================================================
# 🟩 Ventana principal con menú
# ====================================================
def run_assigner_and_flow():
    root = tk.Tk()
    root.title("Copa del Mundo Sub-20")
    center_fullscreen(root)
    root.configure(bg="#f0f0f0")
    crear_encabezado(root)

    menu = tk.Frame(root, bg="#003366", padx=10, pady=10)
    menu.pack(side="left", fill="y")
    tk.Label(menu, text="Menú Principal", bg="#003366", fg="white",
             font=("Arial", 13, "bold")).pack(pady=10)

    tk.Button(menu, text="Asignar Grupos", width=20,
              command=lambda: abrir_asignacion(root)).pack(pady=5)
    tk.Button(menu, text="Fase de Grupos", width=20,
              command=lambda: abrir_fase_grupos(root)).pack(pady=5)
    tk.Button(menu, text="Informes", width=20,
              command=abrir_informe_fecha).pack(pady=5)
    tk.Button(menu, text="Llaves", width=20,
              command=abrir_llaves).pack(pady=5)
    root.mainloop()

# ====================================================
# ⚙️ Funciones de apertura
# ====================================================
def abrir_asignacion(root):
    assign_win = tk.Toplevel(root)
    crear_encabezado(assign_win)
    GroupAssigner(assign_win)
    assign_win.focus_force()

def abrir_informe_fecha():
    win = tk.Toplevel()
    crear_encabezado(win)
    InformesUI(win)
    win.focus_force()

def abrir_llaves():
    win = tk.Toplevel()
    crear_encabezado(win)
    EliminationBracketUI(win)
    win.focus_force()

def abrir_fase_grupos(root):
    grupos_path = os.path.join(os.path.dirname(__file__), "Grupos_Asignados_Sub20_2025.xlsx")
    partidos_path = os.path.join(os.path.dirname(__file__), "FIFA_Sub20_2025_FaseGrupos_Partidos.xlsx")

    if not (os.path.exists(grupos_path) and os.path.exists(partidos_path)):
        tk.messagebox.showwarning("Archivos no encontrados",
                                  "Antes de abrir la Fase de Grupos debés asignar los equipos.")
        return
    try:
        df_g = pd.read_excel(grupos_path)
        df_p = pd.read_excel(partidos_path)
    except Exception as e:
        tk.messagebox.showerror("Error", f"No se pudieron leer los archivos: {e}")
        return

    assigned_groups = {}
    for _, row in df_g.iterrows():
        g = str(row["Grupo"]).strip().upper()
        eq = str(row["Equipo"]).strip()
        assigned_groups.setdefault(g, []).append(eq)

    matches = []
    for _, row in df_p.iterrows():
        matches.append({
            "Grupo": str(row["Grupo"]).strip().upper(),
            "Jornada": int(row["Jornada"]),
            "Equipo1": str(row["Equipo1"]),
            "Equipo2": str(row["Equipo2"])
        })

    # Asegura que la ventana quede visible
    root.lift()
    root.focus_force()

    win = tk.Toplevel(root)
    crear_encabezado(win)
    PhaseGroupsUI(win, assigned_groups, matches)
    win.focus_force()

# ====================================================
# 🚀 MAIN
# ====================================================
if __name__ == "__main__":
    run_assigner_and_flow()
