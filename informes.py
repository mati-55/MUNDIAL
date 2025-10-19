#informes
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import os
from utils import apply_style, center_fullscreen
from core import Torneo

class InformesUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Informes del Torneo")
        apply_style(self.master)
        center_fullscreen(self.master)

        self.torneo = Torneo()

        self._build_ui()

    # ============================ INTERFAZ ============================
    def _build_ui(self):
        top = ttk.Frame(self.master, padding=8)
        top.pack(fill='x')

        ttk.Label(top, text="📊 Informes del Torneo", style="Header.TLabel").pack(side='left', padx=10)

        # 🔹 Botón para volver al menú principal
        ttk.Button(top, text="Volver al menú principal", command=self.volver_menu).pack(side='right', padx=(4, 0))

        body = ttk.Frame(self.master, padding=10)
        body.pack(fill='both', expand=True)

        ttk.Label(body, text="Seleccione el tipo de informe que desea ver:", font=('Segoe UI', 11, 'bold')).pack(pady=(10, 5))

        ttk.Button(body, text="1️⃣ Tabla general de posiciones", width=35,
                   command=self.informe_posiciones).pack(pady=6)
        ttk.Button(body, text="2️⃣ Resultados de la fase de grupos", width=35,
                   command=self.informe_resultados_grupos).pack(pady=6)
        ttk.Button(body, text="3️⃣ Máximos goleadores", width=35,
                   command=self.informe_goleadores).pack(pady=6)
        ttk.Button(body, text="4️⃣ Rendimiento por confederación", width=35,
                   command=self.informe_confederaciones).pack(pady=6)
        ttk.Button(body, text="5️⃣ Equipos con más tarjetas", width=35,
                   command=self.informe_tarjetas).pack(pady=6)

    # ============================ INFORMES ============================
    def informe_posiciones(self):
        """Muestra la tabla general de posiciones de todos los grupos."""
        try:
            data = []
            for g in sorted(self.torneo.grupos):
                tabla = self.torneo.calcular_tabla_posiciones(g)
                for i, e in enumerate(tabla, start=1):
                    data.append([
                        g, i, e.pais, e.stats['PJ'], e.stats['G'], e.stats['E'], e.stats['P'],
                        e.stats['GF'], e.stats['GC'], e.stats['DG'], e.stats['Pts']
                    ])

            if not data:
                messagebox.showinfo("Sin datos", "No hay datos cargados aún.")
                return

            df = pd.DataFrame(data, columns=["Grupo", "Pos", "Equipo", "PJ", "G", "E", "P", "GF", "GC", "DG", "Pts"])
            self._mostrar_tabla(df, "Tabla General de Posiciones")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el informe: {e}")

    def informe_resultados_grupos(self):
        """Muestra los resultados registrados de la fase de grupos."""
        data = []
        for p in self.torneo.calendario.values():
            if p.fase != "Fase de Grupos":
                continue
            e1 = self.torneo.equipos.get(p.id_equipo1)
            e2 = self.torneo.equipos.get(p.id_equipo2)
            if not e1 or not e2:
                continue
            res = f"{p.goles_e1} - {p.goles_e2}" if p.goles_e1 is not None else "Pendiente"
            data.append([e1.grupo, e1.pais, e2.pais, res])

        if not data:
            messagebox.showinfo("Sin datos", "No se registraron resultados aún.")
            return

        df = pd.DataFrame(data, columns=["Grupo", "Equipo 1", "Equipo 2", "Resultado"])
        self._mostrar_tabla(df, "Resultados de la Fase de Grupos")

    def informe_goleadores(self):
        """Muestra los equipos con más goles a favor."""
        data = []
        for e in self.torneo.equipos.values():
            data.append([e.pais, e.stats['GF'], e.stats['Pts']])
        df = pd.DataFrame(data, columns=["Equipo", "Goles a favor", "Puntos"]).sort_values(by="Goles a favor", ascending=False)
        self._mostrar_tabla(df, "Equipos con más goles")

    def informe_confederaciones(self):
        """Ejemplo: rendimiento por confederación (si existe en datos)."""
        conf_data = {}
        for e in self.torneo.equipos.values():
            conf = e.confederacion or "Desconocida"
            conf_data.setdefault(conf, {"PJ": 0, "G": 0, "E": 0, "P": 0, "Pts": 0})
            conf_data[conf]["PJ"] += e.stats["PJ"]
            conf_data[conf]["G"] += e.stats["G"]
            conf_data[conf]["E"] += e.stats["E"]
            conf_data[conf]["P"] += e.stats["P"]
            conf_data[conf]["Pts"] += e.stats["Pts"]

        rows = [[c, v["PJ"], v["G"], v["E"], v["P"], v["Pts"]] for c, v in conf_data.items()]
        df = pd.DataFrame(rows, columns=["Confederación", "PJ", "G", "E", "P", "Pts"])
        self._mostrar_tabla(df, "Rendimiento por Confederación")

    def informe_tarjetas(self):
        """Ejemplo: equipos con más tarjetas (si se cargan en core.Partido)."""
        data = []
        for e in self.torneo.equipos.values():
            ta = e.stats.get("TA", 0)
            tr = e.stats.get("TR", 0)
            data.append([e.pais, ta, tr])
        df = pd.DataFrame(data, columns=["Equipo", "Tarj. Amarillas", "Tarj. Rojas"])
        self._mostrar_tabla(df, "Equipos con más tarjetas")

    # ============================ UTILIDAD ============================
    def _mostrar_tabla(self, df, titulo):
        """Muestra un DataFrame en una ventana."""
        win = tk.Toplevel(self.master)
        win.title(titulo)
        win.geometry("900x500")
        win.transient(self.master)
        win.focus_force()

        frm = ttk.Frame(win, padding=8)
        frm.pack(fill='both', expand=True)

        cols = list(df.columns)
        tree = ttk.Treeview(frm, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor='center')
        for _, row in df.iterrows():
            tree.insert('', tk.END, values=list(row))
        tree.pack(fill='both', expand=True)

        scrollbar = ttk.Scrollbar(frm, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')

    # ============================ VOLVER AL MENÚ ============================
    def volver_menu(self):
        """Cierra esta ventana y regresa al menú principal sin perder datos."""
        try:
            self.torneo.guardar_datos()
        except Exception:
            pass
        self.master.destroy()
