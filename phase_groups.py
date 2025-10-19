import tkinter as tk
from tkinter import ttk, messagebox
from utils import apply_style, center_fullscreen
from core import Torneo, Partido, Equipo
import os
from PIL import Image, ImageTk
import unicodedata


class PhaseGroupsUI:
    def __init__(self, master, assigned_groups, generated_matches):
        self.master = master
        self.master.title("Fase de Grupos - Jornadas")
        apply_style(self.master)
        center_fullscreen(self.master)

        self.torneo = Torneo()
        self.assigned_groups = assigned_groups
        self.generated_matches = generated_matches
        self.current_jornada = 1
        self.max_jornada = 3
        self._flag_cache = {}

        self._load_into_torneo()
        self._build_ui()
        self._load_jornada(self.current_jornada)

    # ============================ CONFIGURACIÓN DE UI ============================
    def _build_ui(self):
        top = ttk.Frame(self.master, padding=8)
        top.pack(fill='x')

        # Botones principales
        ttk.Button(top, text="Avanzar Jornada", command=self.advance_jornada).pack(side='right', padx=(4, 0))
        ttk.Button(top, text="Guardar Jornada", command=self.save_current_jornada).pack(side='right', padx=(4, 0))
        ttk.Button(top, text="Informes (5 tipos)", command=self.show_reports_window).pack(side='right', padx=(4, 10))
        ttk.Button(top, text="Ver llaves de eliminación", command=self.mostrar_llaves).pack(side='right', padx=(4, 0))
        # 🔹 Botón para volver al menú principal
        ttk.Button(top, text="Volver al menú principal", command=self.volver_menu).pack(side='left', padx=(0, 10))

        # Barra de encabezado azul
        header_bar = tk.Frame(self.master, bg="#003366", height=45)
        header_bar.pack(fill='x')

        self.jornada_label = tk.Label(
            header_bar,
            text=f"FASE DE GRUPOS - JORNADA {self.current_jornada}",
            font=('Segoe UI', 12, 'bold'),
            bg="#003366",
            fg="white"
        )
        self.jornada_label.pack(expand=True)

        ttk.Frame(self.master, height=2).pack(fill='x')

        # Tabla de partidos
        cols = ("ID", "Grupo", "Equipo1", "G1", "vs", "G2", "Equipo2", "Resultado")
        tree_frame = ttk.Frame(self.master)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side='right', fill='y')

        self.tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.tree.yview)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", anchor="center", font=('Segoe UI', 10, 'bold'),
                        background="#003366", foreground="white", relief="flat")
        style.configure("Treeview", font=('Segoe UI', 10), rowheight=26,
                        fieldbackground="#F9F9F9", background="#F9F9F9")

        for c in cols:
            self.tree.heading(c, text=c, anchor='center')
            self.tree.column(c, anchor='center', stretch=True)

        self.tree.tag_configure('oddrow', background='#F8F8F8')
        self.tree.tag_configure('evenrow', background='#E7ECF0')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind("<Double-1>", self._on_double_click_row)
                
    def volver_menu(self):
        """Cierra esta ventana y regresa al menú principal sin perder datos."""
        self.torneo.guardar_datos()  # Asegura que se guarde todo lo cargado
        self.master.destroy()         # Cierra solo esta ventana


    # ============================ DATOS ============================
    def _load_into_torneo(self):
        for g, lista in self.assigned_groups.items():
            for pos, pais in enumerate(lista, start=1):
                ident = f"{g}{pos}"
                eq = Equipo(ident, pais, abreviatura=pais[:3].upper(), grupo=g)
                self.torneo.agregar_equipo(eq)

        for m in self.generated_matches:
            g = m['Grupo']
            e1 = m['Equipo1']
            e2 = m['Equipo2']
            pos1 = self.assigned_groups[g].index(e1) + 1
            pos2 = self.assigned_groups[g].index(e2) + 1
            id1 = f"{g}{pos1}"
            id2 = f"{g}{pos2}"
            p = Partido(id1, id2, fecha="", hora="", fase="Fase de Grupos")
            self.torneo.agregar_partido(p)

        self.torneo.configuracion_cerrada = True
        self.torneo.guardar_datos()

    # ============================ FUNCIONES ============================
    def _load_jornada(self, jornada):
        self.current_jornada = jornada
        self.jornada_label.config(text=f"FASE DE GRUPOS - JORNADA {self.current_jornada}")
        self.tree.delete(*self.tree.get_children())
        self._populate_tree_for_jornada(jornada)

    def _populate_tree_for_jornada(self, jornada):
        self.tree.delete(*self.tree.get_children())
        for m in self.generated_matches:
            if m['Jornada'] != jornada:
                continue
            g = m['Grupo']
            e1 = m['Equipo1']
            e2 = m['Equipo2']
            tag = 'evenrow' if (len(self.tree.get_children()) % 2 == 0) else 'oddrow'
            self.tree.insert("", tk.END, values=("", g, e1, "", "vs", "", e2, "PENDIENTE"), tags=(tag,))

    def advance_jornada(self):
        if self.current_jornada < self.max_jornada:
            self.current_jornada += 1
            self._load_jornada(self.current_jornada)
        else:
            messagebox.showinfo("Fase de grupos finalizada", "Todas las jornadas completadas.")
            self.show_standings_window(all_groups=True)

    def save_current_jornada(self):
        messagebox.showinfo("Guardado", f"Jornada {self.current_jornada} guardada correctamente.")
        self.show_standings_window()

    # ============================ TABLA DE POSICIONES ============================
    def show_standings_window(self, all_groups=False):
        from PIL import Image, ImageTk
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        bandera_path = os.path.join(os.path.dirname(BASE_DIR), "banderas")


        win = tk.Toplevel(self.master)
        win.title("Tablas de Posiciones")
        win.geometry("950x550")
        win.transient(self.master)
        win.focus_force()

        frm = ttk.Frame(win, padding=8)
        frm.pack(fill='both', expand=True)

        groups = sorted(set(e.grupo for e in self.torneo.equipos.values()))
        nb = ttk.Notebook(frm)
        nb.pack(fill='both', expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", anchor="center", font=('Segoe UI', 10, 'bold'),
                        background="#003366", foreground="white")
        style.configure("Treeview", font=('Segoe UI', 10), rowheight=30,
                        background="#FFFFFF", fieldbackground="#FFFFFF")

        for g in groups:
            tab = ttk.Frame(nb)
            nb.add(tab, text=f"Grupo {g}")

            tree = ttk.Treeview(tab, columns=("Pos", "Equipo", "PJ", "G", "E", "P", "GF", "GC", "DG", "Pts"), show="headings")
            for c in ("Pos", "Equipo", "PJ", "G", "E", "P", "GF", "GC", "DG", "Pts"):
                tree.heading(c, text=c)
                tree.column(c, anchor="center", width=80)
            tree.column("Equipo", width=200, anchor='w')

            tabla = self.torneo.calcular_tabla_posiciones(g)
            for i, t in enumerate(tabla, start=1):
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                pais = t.pais
                img_path = os.path.join(bandera_path, self._normalize_name(pais) + ".png")
                bandera_img = None
                if os.path.exists(img_path):
                    bandera = Image.open(img_path).resize((26, 18))
                    bandera_img = ImageTk.PhotoImage(bandera)
                    self._flag_cache[pais] = bandera_img
                iid = tree.insert("", tk.END, values=(i, t.pais, t.stats['PJ'], t.stats['G'], t.stats['E'],
                                                      t.stats['P'], t.stats['GF'], t.stats['GC'],
                                                      t.stats['DG'], t.stats['Pts']), tags=(tag,))
                if bandera_img:
                    tree.item(iid, image=bandera_img)
                    tree.image = bandera_img

            tree.pack(fill='both', expand=True)

    def _normalize_name(self, pais):
        pais = ''.join(c for c in unicodedata.normalize('NFD', pais) if unicodedata.category(c) != 'Mn')
        return pais.lower().replace(' ', '').replace('’', '').replace("'", "")
        # ============================ INFORMES ============================
    def show_reports_window(self):
        """Abre la ventana de informes generales (1 a 5)"""
        from informes.informes import InformesUI
        win = tk.Toplevel(self.master)
        InformesUI(win)
    
        # ============================ EVENTO: DOBLE CLIC ============================
    def _on_double_click_row(self, event):
        """Permite ingresar y guardar el resultado del partido seleccionado sin reiniciar el torneo."""
        item = self.tree.selection()
        if not item:
            return

        valores = self.tree.item(item[0], "values")
        if not valores:
            return

        grupo = valores[1]
        equipo1 = valores[2]
        equipo2 = valores[6]

        # Crear ventana de edición de resultado
        win = tk.Toplevel(self.master)
        win.title(f"Registrar resultado - Grupo {grupo}")
        win.geometry("350x220")
        win.transient(self.master)
        win.focus_force()
        win.config(bg="#eaf0fb")

        frm = ttk.Frame(win, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=f"{equipo1}  vs  {equipo2}",
                  font=('Segoe UI', 11, 'bold')).pack(pady=(0, 10))

        fila = ttk.Frame(frm)
        fila.pack(pady=(5, 5))

        ttk.Label(fila, text=f"Goles {equipo1[:3].upper()}:").pack(side='left', padx=5)
        entry_g1 = ttk.Entry(fila, width=5)
        entry_g1.pack(side='left', padx=5)

        ttk.Label(fila, text=f"Goles {equipo2[:3].upper()}:").pack(side='left', padx=5)
        entry_g2 = ttk.Entry(fila, width=5)
        entry_g2.pack(side='left', padx=5)

        # --- GUARDAR RESULTADO ---
        def guardar_resultado():
            try:
                g1 = int(entry_g1.get())
                g2 = int(entry_g2.get())
            except ValueError:
                messagebox.showerror("Error", "Los goles deben ser números enteros.")
                return

            # Buscar partido correspondiente
            partido_encontrado = None
            for p in self.torneo.calendario.values():
                e1 = self.torneo.equipos.get(p.id_equipo1)
                e2 = self.torneo.equipos.get(p.id_equipo2)
                if e1 and e2 and e1.pais == equipo1 and e2.pais == equipo2 and p.fase == "Fase de Grupos":
                    partido_encontrado = p
                    break

            if not partido_encontrado:
                messagebox.showerror("Error", "No se encontró el partido en el registro interno.")
                win.destroy()
                return

            # Actualizar datos en memoria
            p = partido_encontrado
            p.goles_e1 = g1
            p.goles_e2 = g2

            e1 = self.torneo.equipos[p.id_equipo1]
            e2 = self.torneo.equipos[p.id_equipo2]

            # Actualizar estadísticas
            e1.stats['PJ'] += 1
            e2.stats['PJ'] += 1
            e1.stats['GF'] += g1
            e2.stats['GF'] += g2
            e1.stats['GC'] += g2
            e2.stats['GC'] += g1

            if g1 > g2:
                e1.stats['G'] += 1
                e2.stats['P'] += 1
                e1.stats['Pts'] += 3
            elif g2 > g1:
                e2.stats['G'] += 1
                e1.stats['P'] += 1
                e2.stats['Pts'] += 3
            else:
                e1.stats['E'] += 1
                e2.stats['E'] += 1
                e1.stats['Pts'] += 1
                e2.stats['Pts'] += 1

            e1.stats['DG'] = e1.stats['GF'] - e1.stats['GC']
            e2.stats['DG'] = e2.stats['GF'] - e2.stats['GC']

            # Actualizar tabla visual
            self.tree.set(item[0], column="G1", value=str(g1))
            self.tree.set(item[0], column="G2", value=str(g2))
            self.tree.set(item[0], column="Resultado", value=f"{g1} : {g2}")

            # Cerrar ventana (sin mostrar messagebox)
            win.destroy()

        ttk.Button(frm, text="Guardar", command=guardar_resultado).pack(pady=10)
        ttk.Button(frm, text="Cerrar", command=win.destroy).pack()




    # ============================ LLAVES DE ELIMINACIÓN ============================
    def mostrar_llaves(self):
        """Muestra las llaves de eliminación (Octavos → Cuartos → Semis → Final)."""
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        bandera_path = os.path.join(os.path.dirname(BASE_DIR), "banderas")

        win = tk.Toplevel(self.master)
        win.title("Llaves de Eliminación")
        win.geometry("1000x600")
        win.config(bg="#e8eef7")
        win.transient(self.master)
        win.focus_force()

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill='both', expand=True)

        ttk.Label(frm, text="COPA DEL MUNDO SUB-20 - LLAVES DE ELIMINACIÓN",
                  font=('Segoe UI', 13, 'bold')).pack(pady=(0, 10))

        rondas = ["Octavos", "Cuartos", "Semifinal", "Final"]
        contenedor = ttk.Frame(frm)
        contenedor.pack(fill='both', expand=True)

        columnas = []
        for ronda in rondas:
            col = ttk.Frame(contenedor, padding=10)
            col.pack(side='left', expand=True, fill='both')
            ttk.Label(col, text=ronda, font=('Segoe UI', 11, 'bold')).pack(pady=(0, 5))
            columnas.append(col)

        octavos_pairs = [
            ("1°A", "2°C"), ("1°B", "3°A/C/D"), ("1°C", "3°A/B/F"), ("2°A", "2°B"),
            ("1°D", "3°B/E/F"), ("2°E", "1°F"), ("1°E", "2°D"), ("1°F", "2°E")
        ]

        grupos_completos = all(p.goles_e1 is not None and p.goles_e2 is not None
                               for p in self.torneo.calendario.values()
                               if p.fase == "Fase de Grupos")

        for pair in octavos_pairs:
            f = ttk.Frame(columnas[0], relief='ridge', borderwidth=2, padding=5)
            f.pack(pady=8, fill='x')

            if not grupos_completos:
                ttk.Label(f, text=f"{pair[0]}  vs  {pair[1]}",
                          font=('Segoe UI', 10, 'bold')).pack()
            else:
                pais1, pais2 = pair
                for pais in (pais1, pais2):
                    img_path = os.path.join(bandera_path, self._normalize_name(pais) + ".png")
                    bandera_img = None
                    if os.path.exists(img_path):
                        bandera = Image.open(img_path).resize((26, 18))
                        bandera_img = ImageTk.PhotoImage(bandera)
                        self._flag_cache[pais] = bandera_img

                fila = ttk.Frame(f)
                fila.pack(pady=2)
                ttk.Label(fila, text=f"{pais1}  vs  {pais2}", font=('Segoe UI', 10)).pack()

        ttk.Label(frm, text="* Las llaves se completarán automáticamente al finalizar la Fase de Grupos.",
                  font=('Segoe UI', 9, 'italic')).pack(pady=(10, 0))
