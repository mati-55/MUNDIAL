import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from utils import apply_style, center_fullscreen, simple_prompt
from core import Torneo, Partido, Equipo
import os

class PhaseGroupsUI:
    """
    Muestra jornadas 1..3 secuencialmente. Cada jornada lista todos los partidos
    (de todos los grupos) en una tabla editable (goles). Guardar jornada actualiza Torneo.

    Cambios realizados:
    - Al guardar una jornada se muestra la tabla de posiciones (por grupo) resultante.
    - Al editar/guardar el resultado de un partido se muestra un popup con información del partido
      y un resumen rápido de la tabla del grupo correspondiente.
    - Se añadió una ventana "Informes" que muestra 5 tipos de informes (sin banderas, usando abreviaturas):
        1) Tabla por grupo
        2) Resultados de una jornada
        3) Partidos pendientes
        4) Estadísticas por equipo
        5) Clasificados a Eliminatorias (1os, 2os y mejores 3os)
    """
    def __init__(self, master, assigned_groups, generated_matches):
        self.master = master
        self.master.title("Fase de Grupos - Jornadas")
        apply_style(self.master)
        center_fullscreen(self.master)

        self.torneo = Torneo()
        self.assigned_groups = assigned_groups
        self.generated_matches = generated_matches  # list of dicts with Grupo,Jornada,Equipo1,Equipo2
        self.current_jornada = 1
        self.max_jornada = 3

        self._load_into_torneo()
        self._build_ui()
        self._load_jornada(self.current_jornada)

    def _load_into_torneo(self):
        # add teams with ids like A1..F4 maintaining positions
        for g, lista in self.assigned_groups.items():
            for pos, pais in enumerate(lista, start=1):
                ident = f"{g}{pos}"
                eq = Equipo(ident, pais, abreviatura=pais[:3].upper(), grupo=g)
                self.torneo.agregar_equipo(eq)
        # add matches to torneo calendario
        for m in self.generated_matches:
            g = m['Grupo']; j = m['Jornada']; e1 = m['Equipo1']; e2 = m['Equipo2']
            pos1 = self.assigned_groups[g].index(e1) + 1
            pos2 = self.assigned_groups[g].index(e2) + 1
            id1 = f"{g}{pos1}"; id2 = f"{g}{pos2}"
            p = Partido(id1, id2, fecha="", hora="", fase="Fase de Grupos")
            self.torneo.agregar_partido(p)
        # close configuration to allow result registration
        self.torneo.configuracion_cerrada = True
        self.torneo.guardar_datos()

    def _build_ui(self):
        header = ttk.Frame(self.master, padding=8); header.pack(fill='x')
        ttk.Label(header, text="Fase de Grupos - Jornadas", style="Header.TLabel").pack(side='left')
        # Informes button
        ttk.Button(header, text="Informes (5 tipos)", command=self.show_reports_window).pack(side='right', padx=6)

        top = ttk.Frame(self.master, padding=8); top.pack(fill='x')
        self.jornada_label = ttk.Label(top, text=f"Jornada {self.current_jornada}"); self.jornada_label.pack(side='left')
        ttk.Button(top, text="Guardar Jornada", command=self.save_current_jornada).pack(side='right')
        ttk.Button(top, text="Avanzar Jornada", command=self.advance_jornada).pack(side='right', padx=6)

        # Treeview to list matches of current jornada
        cols = ("ID","Grupo","Equipo1","G1","vs","G2","Equipo2","Resultado")
        self.tree = ttk.Treeview(self.master, columns=cols, show='headings')
        for c in cols: self.tree.heading(c, text=c)
        self.tree.pack(fill='both', expand=True, padx=8, pady=8)

        # We will present editable entries below for selected match bulk edit
        edit_frame = ttk.Frame(self.master, padding=8); edit_frame.pack(fill='x')
        ttk.Label(edit_frame, text="Selecciona una fila y edita los goles (doble clic):").pack(side='left')
        # Shortcut: double click to edit
        self.tree.bind("<Double-1>", self._on_double_click_row)

    def _populate_tree_for_jornada(self, jornada):
        # remove all
        self.tree.delete(*self.tree.get_children())
        # Build reverse lookup for (id1,id2)->mid
        rev = {}
        for mid,p in self.torneo.calendario.items():
            rev[(p.id_equipo1,p.id_equipo2)] = mid

        for m in self.generated_matches:
            if m['Jornada'] != jornada: continue
            g = m['Grupo']
            e1name = m['Equipo1']; e2name = m['Equipo2']
            try:
                pos1 = self.assigned_groups[g].index(e1name) + 1
                pos2 = self.assigned_groups[g].index(e2name) + 1
            except ValueError:
                # if a team not found skip
                continue
            id1 = f"{g}{pos1}"; id2 = f"{g}{pos2}"
            mid = rev.get((id1,id2))
            swapped = False
            if not mid:
                mid = rev.get((id2,id1))
                swapped = True if mid else False
            p = self.torneo.calendario.get(mid) if mid else None
            e1 = self.torneo.equipos.get(id1).pais if id1 in self.torneo.equipos else id1
            e2 = self.torneo.equipos.get(id2).pais if id2 in self.torneo.equipos else id2
            if p:
                # If stored in reversed order, display accordingly
                if swapped:
                    # displayed G1 is p.goles_e2 etc.
                    g1 = p.goles_e2 if p.goles_e2 is not None else ""
                    g2 = p.goles_e1 if p.goles_e1 is not None else ""
                else:
                    g1 = p.goles_e1 if p.goles_e1 is not None else ""
                    g2 = p.goles_e2 if p.goles_e2 is not None else ""
                res = f"{p.goles_e1} : {p.goles_e2}" if p.goles_e1 is not None else "PENDIENTE"
            else:
                g1 = ""; g2 = ""; res = "PENDIENTE"
            iid = mid if mid else f"{g}_{id1}_{id2}"
            self.tree.insert("", tk.END, iid=iid, values=(mid if mid else iid, g, e1, g1, "vs", g2, e2, res))

    def _load_jornada(self, jornada):
        self.jornada_label.config(text=f"Jornada {jornada}")
        self._populate_tree_for_jornada(jornada)

    def _on_double_click_row(self, event):
        item = self.tree.selection()
        if not item: return
        mid = item[0]
        partido = self.torneo.calendario.get(mid)
        if not partido:
            messagebox.showerror("Error", "No se encontró el partido seleccionado en el calendario interno.")
            return
        # open small dialog to edit goals
        win = tk.Toplevel(self.master); win.title(f"Editar {mid}")
        win.geometry("360x160"); win.transient(self.master); win.grab_set()

        frm = ttk.Frame(win, padding=8); frm.pack(fill='both', expand=True)
        ttk.Label(frm, text=f"{self.torneo.equipos.get(partido.id_equipo1).pais}  vs  {self.torneo.equipos.get(partido.id_equipo2).pais}").pack(pady=(0,6))
        row = ttk.Frame(frm); row.pack()
        ttk.Label(row, text="Goles " + self.torneo.equipos.get(partido.id_equipo1).abreviatura).pack(side='left', padx=6)
        e1 = ttk.Entry(row, width=6); e1.pack(side='left')
        ttk.Label(row, text="Goles " + self.torneo.equipos.get(partido.id_equipo2).abreviatura).pack(side='left', padx=6)
        e2 = ttk.Entry(row, width=6); e2.pack(side='left')
        # prefill
        e1.insert(0, "" if partido.goles_e1 is None else str(partido.goles_e1))
        e2.insert(0, "" if partido.goles_e2 is None else str(partido.goles_e2))

        def save():
            try:
                g1 = int(e1.get()); g2 = int(e2.get())
            except Exception:
                messagebox.showerror("Error", "Goles deben ser enteros.")
                return
            partido.goles_e1 = g1; partido.goles_e2 = g2
            # recompute all stats from scratch to avoid double counting
            self._recompute_stats_from_results()
            self.torneo.guardar_datos()
            win.destroy()
            self._load_jornada(self.current_jornada)
            # show info summary about saved partido and group standings
            equipo1 = self.torneo.equipos.get(partido.id_equipo1)
            equipo2 = self.torneo.equipos.get(partido.id_equipo2)
            partido_info = f"{equipo1.pais}  {g1} : {g2}  {equipo2.pais}"
            # Show also updated mini tabla for this group
            grupo = equipo1.grupo
            tabla = self.torneo.calcular_tabla_posiciones(grupo)
            abla_txt = "\n".join([f"{i+1} -{t.pais} - Pts:{t.stats['Pts']}" for i,t in enumerate(tabla)])
            messagebox.showinfo("Resultado guardado", f"Partido: {partido_info}\n\nTabla actualizada Grupo {grupo}:\n{tabla_txt}")

        ttk.Button(frm, text="Guardar", command=save).pack(pady=8)

    def _recompute_stats_from_results(self):
        # reset all team stats
        for e in self.torneo.equipos.values():
            e.stats = {'PJ':0,'G':0,'E':0,'P':0,'GF':0,'GC':0,'DG':0,'Pts':0,'MaxAvance':'Fase de Grupos'}
        # iterate all partidos and update stats for those with goles != None
        for mid,p in self.torneo.calendario.items():
            if p.goles_e1 is None or p.goles_e2 is None:
                continue
            e1 = self.torneo.equipos.get(p.id_equipo1); e2 = self.torneo.equipos.get(p.id_equipo2)
            if not e1 or not e2: continue
            e1.stats['PJ'] += 1; e2.stats['PJ'] +=1
            e1.stats['GF'] += p.goles_e1; e1.stats['GC'] += p.goles_e2
            e2.stats['GF'] += p.goles_e2; e2.stats['GC'] += p.goles_e1
            if p.goles_e1 > p.goles_e2:
                e1.stats['G'] +=1; e2.stats['P'] +=1; e1.stats['Pts'] +=3
            elif p.goles_e1 < p.goles_e2:
                e2.stats['G'] +=1; e1.stats['P'] +=1; e2.stats['Pts'] +=3
            else:
                e1.stats['E'] +=1; e2.stats['E'] +=1; e1.stats['Pts'] +=1; e2.stats['Pts'] +=1
            e1.stats['DG'] = e1.stats['GF'] - e1.stats['GC']
            e2.stats['DG'] = e2.stats['GF'] - e2.stats['GC']

    def save_current_jornada(self):
        # iterate tree rows and store goles to torneo calendario
        for iid in self.tree.get_children():
            vals = self.tree.item(iid)['values']
            mid = vals[0]
            try:
                g1 = vals[3]
                g2 = vals[5]
                if g1 == "" or g2 == "" or g1 is None or g2 is None:
                    continue
                p = self.torneo.calendario.get(mid)
                if p:
                    p.goles_e1 = int(g1); p.goles_e2 = int(g2)
            except Exception:
                continue
        # recompute stats
        self._recompute_stats_from_results()
        self.torneo.guardar_datos()
        messagebox.showinfo("Guardado", f"Jornada {self.current_jornada} guardada.")
        # after saving jornada, show standings window so user pueda ver cómo quedó la tabla
        self.show_standings_window()

    def advance_jornada(self):
        if self.current_jornada < self.max_jornada:
            # Ensure at least all matches of current jornada have results before advancing
            all_filled = True
            for m in self.generated_matches:
                if m['Jornada'] != self.current_jornada: continue
                g = m['Grupo']; e1name = m['Equipo1']; e2name = m['Equipo2']
                pos1 = self.assigned_groups[g].index(e1name)+1; pos2 = self.assigned_groups[g].index(e2name)+1
                id1 = f"{g}{pos1}"; id2 = f"{g}{pos2}"
                found = False
                for mid,p in self.torneo.calendario.items():
                    if (p.id_equipo1==id1 and p.id_equipo2==id2) or (p.id_equipo1==id2 and p.id_equipo2==id1):
                        if p.goles_e1 is None or p.goles_e2 is None:
                            all_filled = False
                        found = True
                        break
                if not found:
                    all_filled = False
            if not all_filled:
                if not messagebox.askyesno("Advertencia", "Algunos partidos aún no tienen resultados. ¿Desea avanzar igual?"):
                    return
            self.current_jornada += 1
            if self.current_jornada > self.max_jornada:
                messagebox.showinfo("Fase de grupos finalizada", "Todas las jornadas completadas.\nAhora puede continuar a las fases eliminatorias.")
                # Show final standings for all groups
                self.show_standings_window(all_groups=True)
                self.master.destroy()
                return
            self._load_jornada(self.current_jornada)
        else:
            messagebox.showinfo("Info", "Última jornada. Al avanzar se cerrará la fase de grupos.")
            # final standings
            self.show_standings_window(all_groups=True)
            self.master.destroy()

    # ----------------- Informes / Tablas -----------------
    def show_standings_window(self, all_groups=False):
        """
        Muestra una ventana con las tablas de posiciones.
        Si all_groups True muestra todas las tablas en un notebook; si False muestra selector de grupo.
        """
        win = tk.Toplevel(self.master); win.title("Tablas de Posiciones")
        win.geometry("800x500"); win.transient(self.master); win.grab_set()
        frm = ttk.Frame(win, padding=8); frm.pack(fill='both', expand=True)
        groups = sorted(set(e.grupo for e in self.torneo.equipos.values()))
        if all_groups:
            nb = ttk.Notebook(frm); nb.pack(fill='both', expand=True)
            for g in groups:
                tab = ttk.Frame(nb); nb.add(tab, text=f"Grupo {g}")
                tree = ttk.Treeview(tab, columns=("Pos","Abrev","Equipo","PJ","G","E","P","GF","GC","DG","Pts"), show='headings')
                for c in ("Pos","Abrev","Equipo","PJ","G","E","P","GF","GC","DG","Pts"):
                    tree.heading(c, text=c)
                tree.pack(fill='both', expand=True)
                tabla = self.torneo.calcular_tabla_posiciones(g)
                for i,t in enumerate(tabla, start=1):
                    tree.insert("", tk.END, values=(i, t.abreviatura, t.pais, t.stats['PJ'], t.stats['G'], t.stats['E'], t.stats['P'], t.stats['GF'], t.stats['GC'], t.stats['DG'], t.stats['Pts']))
        else:
            top = ttk.Frame(frm); top.pack(fill='x')
            ttk.Label(top, text="Seleccione grupo:").pack(side='left')
            grp_var = tk.StringVar(value=groups[0] if groups else "")
            grp_cb = ttk.Combobox(top, values=groups, textvariable=grp_var, state='readonly')
            grp_cb.pack(side='left', padx=6)
            tree = ttk.Treeview(frm, columns=("Pos","Abrev","Equipo","PJ","G","E","P","GF","GC","DG","Pts"), show='headings')
            for c in ("Pos","Abrev","Equipo","PJ","G","E","P","GF","GC","DG","Pts"):
                tree.heading(c, text=c)
            tree.pack(fill='both', expand=True)

            def load_selected(_=None):
                tree.delete(*tree.get_children())
                g = grp_var.get()
                if not g: return
                tabla = self.torneo.calcular_tabla_posiciones(g)
                for i,t in enumerate(tabla, start=1):
                    tree.insert("", tk.END, values=(i, t.abreviatura, t.pais, t.stats['PJ'], t.stats['G'], t.stats['E'], t.stats['P'], t.stats['GF'], t.stats['GC'], t.stats['DG'], t.stats['Pts']))
            grp_cb.bind("<<ComboboxSelected>>", load_selected)
            load_selected()

    def show_reports_window(self):
        """
        Ventana con 5 tipos de informe:
        1) Tabla por grupo
        2) Resultados Jornada
        3) Partidos pendientes
        4) Estadísticas por equipo
        5) Clasificados a Eliminatorias (1os,2os,mejores 3os)
        """
        win = tk.Toplevel(self.master); win.title("Informes")
        win.geometry("900x550"); win.transient(self.master); win.grab_set()
        container = ttk.Frame(win, padding=8); container.pack(fill='both', expand=True)

        left = ttk.Frame(container); left.pack(side='left', fill='y', padx=(0,8))
        reports = [
            "1 - Tabla por grupo",
            "2 - Resultados Jornada",
            "3 - Partidos pendientes",
            "4 - Estadísticas por equipo",
            "5 - Clasificados a Eliminatorias"
        ]
        rpt_var = tk.StringVar(value=reports[0])
        lb = tk.Listbox(left, listvariable=tk.StringVar(value=reports), height=len(reports))
        lb.pack(fill='y')
        # display area
        right = ttk.Frame(container); right.pack(side='right', fill='both', expand=True)
        cols = ("A","B")  # placeholder
        tree = ttk.Treeview(right, show='headings'); tree.pack(fill='both', expand=True)

        # controls for auxiliary selection
        ctrl = ttk.Frame(left); ctrl.pack(fill='x', pady=8)
        ttk.Label(ctrl, text="Jornada:").pack(side='left')
        jornada_spin = ttk.Spinbox(ctrl, from_=1, to=self.max_jornada, width=4); jornada_spin.set(str(self.current_jornada))
        jornada_spin.pack(side='left', padx=4)
        ttk.Label(ctrl, text="Grupo:").pack(side='left', padx=(8,0))
        groups = sorted(set(e.grupo for e in self.torneo.equipos.values()))
        grp_cb = ttk.Combobox(ctrl, values=groups, state='readonly'); grp_cb.set(groups[0] if groups else "")
        grp_cb.pack(side='left', padx=4)

        def clear_tree(columns):
            tree.delete(*tree.get_children())
            tree["columns"] = columns
            for c in columns:
                tree.heading(c, text=c)
                tree.column(c, width=120, anchor='center')

        def load_report(event=None):
            sel_idx = lb.curselection()
            if not sel_idx:
                report = reports[0]
            else:
                report = reports[sel_idx[0]]
            if report.startswith("1"):
                # Tabla por grupo (usa grupo seleccionado)
                g = grp_cb.get()
                if not g:
                    messagebox.showwarning("Seleccionar grupo", "Seleccione un grupo en el control izquierdo.")
                    return
                cols = ("Pos","Abrev","Equipo","PJ","G","E","P","GF","GC","DG","Pts")
                clear_tree(cols)
                tabla = self.torneo.calcular_tabla_posiciones(g)
                for i,t in enumerate(tabla, start=1):
                    tree.insert("", tk.END, values=(i,t.abreviatura,t.pais,t.stats['PJ'],t.stats['G'],t.stats['E'],t.stats['P'],t.stats['GF'],t.stats['GC'],t.stats['DG'],t.stats['Pts']))
            elif report.startswith("2"):
                # Resultados Jornada
                j = int(jornada_spin.get())
                cols = ("Grupo","Equipo1","Abrev1","G1","vs","G2","Abrev2","Equipo2")
                clear_tree(cols)
                for m in self.generated_matches:
                    if m['Jornada'] != j: continue
                    g = m['Grupo']; e1 = m['Equipo1']; e2 = m['Equipo2']
                    pos1 = self.assigned_groups[g].index(e1)+1; pos2 = self.assigned_groups[g].index(e2)+1
                    id1 = f"{g}{pos1}"; id2 = f"{g}{pos2}"
                    p = None
                    # find partido
                    for mid,part in self.torneo.calendario.items():
                        if (part.id_equipo1==id1 and part.id_equipo2==id2) or (part.id_equipo1==id2 and part.id_equipo2==id1):
                            p = part; break
                    if p:
                        # Determine mapping to display correct G1/G2 relative to e1/e2
                        if p.id_equipo1 == id1:
                            g1 = p.goles_e1 if p.goles_e1 is not None else ""
                            g2 = p.goles_e2 if p.goles_e2 is not None else ""
                        else:
                            g1 = p.goles_e2 if p.goles_e2 is not None else ""
                            g2 = p.goles_e1 if p.goles_e1 is not None else ""
                    else:
                        g1 = ""; g2 = ""
                    ab1 = self._get_abbr_by_pais(e1); ab2 = self._get_abbr_by_pais(e2)
                    tree.insert("", tk.END, values=(g,e1,ab1,g1,"vs",g2,ab2,e2))
            elif report.startswith("3"):
                # Partidos pendientes
                cols = ("ID","Grupo","Equipo1","Abrev1","Equipo2","Abrev2")
                clear_tree(cols)
                for mid,p in self.torneo.calendario.items():
                    if p.goles_e1 is None or p.goles_e2 is None:
                        e1 = self.torneo.equipos.get(p.id_equipo1).pais; e2 = self.torneo.equipos.get(p.id_equipo2).pais
                        ab1 = self.torneo.equipos.get(p.id_equipo1).abreviatura; ab2 = self.torneo.equipos.get(p.id_equipo2).abreviatura
                        tree.insert("", tk.END, values=(mid,p.fase,e1,ab1,e2,ab2))
            elif report.startswith("4"):
                # Estadísticas por equipo (global)
                cols = ("ID","Abrev","Equipo","Grupo","PJ","G","E","P","GF","GC","DG","Pts")
                clear_tree(cols)
                for id,e in sorted(self.torneo.equipos.items()):
                    t = e
                    tree.insert("", tk.END, values=(id,t.abreviatura,t.pais,t.grupo,t.stats['PJ'],t.stats['G'],t.stats['E'],t.stats['P'],t.stats['GF'],t.stats['GC'],t.stats['DG'],t.stats['Pts']))
            else:
                # Clasificados a Eliminatorias: top2 por grupo + mejores 3os (4)
                cols = ("Tipo","Abrev","Equipo","Grupo","Pts","DG","GF")
                clear_tree(cols)
                groups = sorted(set(e.grupo for e in self.torneo.equipos.values()))
                firsts=[]; seconds=[]; thirds=[]
                for g in groups:
                    tabla = self.torneo.calcular_tabla_posiciones(g)
                    if len(tabla) >= 1: firsts.append(tabla[0])
                    if len(tabla) >= 2: seconds.append(tabla[1])
                    if len(tabla) >= 3: thirds.append(tabla[2])
                for t in firsts:
                    tree.insert("", tk.END, values=("1º", t.abreviatura, t.pais, t.grupo, t.stats['Pts'], t.stats['DG'], t.stats['GF']))
                for t in seconds:
                    tree.insert("", tk.END, values=("2º", t.abreviatura, t.pais, t.grupo, t.stats['Pts'], t.stats['DG'], t.stats['GF']))
                thirds_sorted = sorted(thirds, key=lambda t: (t.stats['Pts'], t.stats['DG'], t.stats['GF']), reverse=True)
                for i,t in enumerate(thirds_sorted[:4], start=1):
                    tree.insert("", tk.END, values=(f"3º (mejor {i})", t.abreviatura, t.pais, t.grupo, t.stats['Pts'], t.stats['DG'], t.stats['GF']))

        lb.bind("<<ListboxSelect>>", load_report)
        # initial load
        load_report()

    def _get_abbr_by_pais(self, pais):
        for id,e in self.torneo.equipos.items():
            if e.pais == pais:
                return e.abreviatura
        return pais[:3].upper() if pais else ""

