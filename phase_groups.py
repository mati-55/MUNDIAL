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
    # ================== Helpers de fechas/horarios y standings ==================

    def _normalize_col(self, s):
        return str(s).strip().lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")

    def _parse_date_strict(self, s):
        # Acepta "dd/mm/yyyy" o "yyyy-mm-dd"
        from datetime import datetime
        if s is None or (isinstance(s, float) and pd.isna(s)):
            return None
        if isinstance(s, (pd.Timestamp, )):
            return s.date()
        ss = str(s).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(ss, fmt).date()
            except Exception:
                pass
        return None

    def _parse_time_flexible(self, s):
        # Devuelve texto HH:MM (no forzamos datetime)
        if s is None or (isinstance(s, float) and pd.isna(s)):
            return ""
        ss = str(s).strip()
        # Si viene como Timestamp, etc:
        try:
            # pandas puede traer horas como Timestamp; lo convertimos a HH:MM
            t = pd.to_datetime(ss, errors='coerce')
            if pd.notna(t):
                return t.strftime("%H:%M")
        except Exception:
            pass
        # Si ya está en texto HH:MM u otro; devolvemos tal cual:
        return ss

    def _torneo_date_bounds(self):
        from datetime import datetime
        # core.Torneo guarda strings 'YYYY-MM-DD'
        start = pd.to_datetime(self.torneo.fecha_inicio).date()
        end = pd.to_datetime(self.torneo.fecha_fin).date()
        return start, end

    def _date_in_range(self, d):
        if d is None: return False
        start, end = self._torneo_date_bounds()
        return start <= d <= end

    def _load_group_schedule_df(self):
        """
        Lee 'FIFA_Sub20_2025_FaseGrupos partidos.xlsx' (o el alternativo con '_Partidos.xlsx')
        y devuelve un DataFrame con columnas normalizadas:
        ['grupo','equipo1','equipo2','fecha','hora']  (fecha: date, hora: HH:MM string)
        """
        base = os.path.dirname(__file__)
        candidates = [
            os.path.join(base, "FIFA_Sub20_2025_FaseGrupos partidos.xlsx"),
            os.path.join(base, "FIFA_Sub20_2025_FaseGrupos_Partidos.xlsx"),
        ]
        path = None
        for c in candidates:
            if os.path.exists(c):
                path = c
                break
        if not path:
            return pd.DataFrame(columns=["grupo","equipo1","equipo2","fecha","hora"])

        df = pd.read_excel(path)
        # map columns
        cols = {self._normalize_col(c): c for c in df.columns}
        # buscadores flexibles
        def pick(*names):
            for n in names:
                nn = self._normalize_col(n)
                if nn in cols:
                    return cols[nn]
            return None
        c_grupo = pick("grupo")
        c_e1    = pick("equipo1","e1","local","pais1")
        c_e2    = pick("equipo2","e2","visitante","pais2")
        c_fecha = pick("fecha","dia","fechajuego")
        c_hora  = pick("hora","horario","inicio")

        out = []
        for _,r in df.iterrows():
            grupo  = str(r.get(c_grupo,"")).strip().upper() if c_grupo else ""
            e1     = str(r.get(c_e1,"")).strip()
            e2     = str(r.get(c_e2,"")).strip()
            fecha  = self._parse_date_strict(r.get(c_fecha))
            hora   = self._parse_time_flexible(r.get(c_hora))
            if grupo and e1 and e2 and fecha:
                out.append({"grupo":grupo,"equipo1":e1,"equipo2":e2,"fecha":fecha,"hora":hora})
        return pd.DataFrame(out)

    def _load_elim_schedule_df(self):
        """
        Lee 'fechas_fase_eliminatoria.xlsx' y devuelve DF normalizado:
        ['fase','fecha','hora'] (una fila por partido programado en esa fase).
        El emparejamiento a partidos concretos se hace por orden.
        """
        base = os.path.dirname(__file__)
        path = os.path.join(base, "fechas_fase_eliminatoria.xlsx")
        if not os.path.exists(path):
            return pd.DataFrame(columns=["fase","fecha","hora"])
        df = pd.read_excel(path)
        cols = {self._normalize_col(c): c for c in df.columns}
        def pick(*names):
            for n in names:
                nn = self._normalize_col(n)
                if nn in cols:
                    return cols[nn]
            return None
        c_fase  = pick("fase","etapa")
        c_fecha = pick("fecha","dia")
        c_hora  = pick("hora","horario","inicio")
        out = []
        for _,r in df.iterrows():
            fase  = str(r.get(c_fase,"")).strip().capitalize()
            fecha = self._parse_date_strict(r.get(c_fecha))
            hora  = self._parse_time_flexible(r.get(c_hora))
            if fase and fecha:
                # Normalizar nombres esperados
                if fase.lower().startswith("oct"):  fase = "Octavos"
                elif fase.lower().startswith("cua"): fase = "Cuartos"
                elif "semi" in fase.lower():        fase = "Semifinal"
                elif "final" == fase.lower():       fase = "Final"
                elif "gran final" in fase.lower():  fase = "Final"
                out.append({"fase":fase,"fecha":fecha,"hora":hora})
        # Garantizar orden
        return pd.DataFrame(out)

    def _match_datetime_group(self, id1, id2):
        """
        Dado un partido de fase de grupos por IDs (A1, B3,...), retorna (fecha, hora)
        buscándolo en el Excel de grupos: matchea por grupo y por nombres de países.
        """
        df = getattr(self, "_df_grp_sched", None)
        if df is None:
            df = self._load_group_schedule_df()
            self._df_grp_sched = df

        e1 = self.torneo.equipos.get(id1)
        e2 = self.torneo.equipos.get(id2)
        if not e1 or not e2:
            return (None, "")

        g = (e1.grupo or e2.grupo or "").upper()
        pais1 = e1.pais; pais2 = e2.pais

        # buscar fila (pais1,pais2) o (pais2,pais1)
        q = df[(df["grupo"]==g) &
               (((df["equipo1"]==pais1)&(df["equipo2"]==pais2)) |
                ((df["equipo1"]==pais2)&(df["equipo2"]==pais1)))]
        if len(q) == 0:
            return (None, "")
        # si hay varios, tomar el primero
        r = q.iloc[0]
        return (r["fecha"], r["hora"])

    def _match_datetime_elim(self, fase, ordinal_en_fase):
        """
        Retorna (fecha,hora) a partir del Excel de eliminatorias, asignando por 'ordinal_en_fase' (1-based).
        """
        df = getattr(self, "_df_elim_sched", None)
        if df is None:
            df = self._load_elim_schedule_df()
            self._df_elim_sched = df
        pool = df[df["fase"]==fase].reset_index(drop=True)
        if len(pool)==0: return (None,"")
        idx = min(max(ordinal_en_fase-1,0), len(pool)-1)
        r = pool.iloc[idx]
        return (r["fecha"], r["hora"])

    def _standings_as_of_date(self, cutoff_date):
        """
        Devuelve {grupo: {equipo_id: stats_temp}} usando SOLO partidos de FASE DE GRUPOS
        cuya fecha (por Excel de grupos) sea <= cutoff_date.
        No altera self.torneo (trabaja en copia).
        """
        # Inicializar estructura
        tmp = {}
        for id,e in self.torneo.equipos.items():
            if e.grupo:
                tmp.setdefault(e.grupo, {})
                tmp[e.grupo][id] = {'PJ':0,'G':0,'E':0,'P':0,'GF':0,'GC':0,'DG':0,'Pts':0}

        # iterar todos los partidos de fase de grupos
        for mid,p in self.torneo.calendario.items():
            if p.fase != "Fase de Grupos":
                continue
            # Fecha del partido desde Excel de grupos:
            fecha,_ = self._match_datetime_group(p.id_equipo1, p.id_equipo2)
            if fecha is None or fecha > cutoff_date:
                continue
            if p.goles_e1 is None or p.goles_e2 is None:
                # si no hay resultado, no cuenta para la tabla hasta ese día
                continue
            g1 = p.id_equipo1; g2 = p.id_equipo2
            e1 = self.torneo.equipos.get(g1); e2 = self.torneo.equipos.get(g2)
            if not e1 or not e2: continue
            g = e1.grupo
            # acumular
            tmp[g][g1]['PJ'] += 1; tmp[g][g2]['PJ'] += 1
            tmp[g][g1]['GF'] += p.goles_e1; tmp[g][g1]['GC'] += p.goles_e2
            tmp[g][g2]['GF'] += p.goles_e2; tmp[g][g2]['GC'] += p.goles_e1
            if p.goles_e1 > p.goles_e2:
                tmp[g][g1]['G']+=1; tmp[g][g2]['P']+=1; tmp[g][g1]['Pts']+=3
            elif p.goles_e1 < p.goles_e2:
                tmp[g][g2]['G']+=1; tmp[g][g1]['P']+=1; tmp[g][g2]['Pts']+=3
            else:
                tmp[g][g1]['E']+=1; tmp[g][g2]['E']+=1; tmp[g][g1]['Pts']+=1; tmp[g][g2]['Pts']+=1
            tmp[g][g1]['DG'] = tmp[g][g1]['GF'] - tmp[g][g1]['GC']
            tmp[g][g2]['DG'] = tmp[g][g2]['GF'] - tmp[g][g2]['GC']

        # devolver ordenado por grupo con lista de filas ordenadas
        out = {}
        for g,table in tmp.items():
            rows = []
            for id,st in table.items():
                eq = self.torneo.equipos[id]
                rows.append((id, eq.abreviatura, eq.pais, st))
            rows.sort(key=lambda x: (x[3]['Pts'], x[3]['DG'], x[3]['GF']), reverse=True)
            out[g] = rows
        return out

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
            tabla_txt = "\n".join([f"{i+1} -{t.pais} - Pts:{t.stats['Pts']}" for i,t in enumerate(tabla)])
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
        Nueva versión de Informes:
        Paso 1: elegir el tipo de informe
        Paso 2: ingresar datos específicos según el tipo seleccionado
        """
        # ---------- PRIMERA VENTANA: ELECCIÓN DEL INFORME ----------
        select_win = tk.Toplevel(self.master)
        select_win.title("Seleccionar tipo de informe")
        select_win.geometry("700x400")
        select_win.transient(self.master)
        select_win.grab_set()

        ttk.Label(select_win, text="Seleccione el tipo de informe que desea generar:",
                  style="Header.TLabel").pack(pady=10)

        opciones = [
            ("1 - Partidos por Fecha",
             "Muestra todos los partidos de esa fecha (fase de grupos y eliminatorias)."),
            ("2 - Tabla del Grupo a una Fecha",
             "Muestra la tabla de posiciones de un grupo específico hasta una fecha dada."),
            ("3 - Recorrido del País hasta una Fecha",
             "Muestra todos los partidos jugados por un país hasta una fecha."),
            ("4 - Partido más cercano del País a una Fecha",
             "Muestra el partido más cercano (por fecha) de ese país, con horario y fase."),
            ("5 - Todas las Tablas a una Fecha",
             "Muestra la tabla completa de todos los grupos hasta esa fecha.")
        ]

        informe_var = tk.StringVar(value=opciones[0][0])

        frame_radios = ttk.Frame(select_win, padding=10)
        frame_radios.pack(fill='x')

        for val, desc in opciones:
            rb = ttk.Radiobutton(frame_radios, text=val, variable=informe_var, value=val)
            rb.pack(anchor='w', pady=4)
            ttk.Label(frame_radios, text=desc, wraplength=600).pack(anchor='w', padx=30)

        def continuar():
            tipo = informe_var.get()[0]
            select_win.destroy()
            self._abrir_informe_detallado(int(tipo))

        ttk.Button(select_win, text="Continuar", command=continuar).pack(pady=12)
        ttk.Button(select_win, text="Cancelar", command=select_win.destroy).pack()

    # ---------- SEGUNDA VENTANA ----------
    def _abrir_informe_detallado(self, tipo):
        """
        Abre la ventana de entrada de datos según el tipo de informe seleccionado.
        """
        win = tk.Toplevel(self.master)
        win.title(f"Informe {tipo}")
        win.geometry("1000x600")
        win.transient(self.master)
        win.grab_set()

        container = ttk.Frame(win, padding=8)
        container.pack(fill='both', expand=True)

        left = ttk.Frame(container)
        left.pack(side='left', fill='y', padx=(0, 10))
        right = ttk.Frame(container)
        right.pack(side='right', fill='both', expand=True)

        ttk.Label(left, text=f"Informe {tipo}", style="Header.TLabel").pack(anchor='w', pady=(0, 10))

        frm_inputs = ttk.Frame(left)
        frm_inputs.pack(fill='x', pady=10)

        ttk.Label(frm_inputs, text="Fecha (dd/mm/aaaa):").grid(row=0, column=0, sticky='w', pady=3)
        fecha_entry = ttk.Entry(frm_inputs, width=16)
        fecha_entry.grid(row=0, column=1, sticky='w')

        ttk.Label(frm_inputs, text="Grupo:").grid(row=1, column=0, sticky='w', pady=3)
        grupos = sorted(set(e.grupo for e in self.torneo.equipos.values() if e.grupo))
        grupo_cb = ttk.Combobox(frm_inputs, values=grupos, state='readonly', width=6)
        if grupos:
            grupo_cb.set(grupos[0])
        grupo_cb.grid(row=1, column=1, sticky='w')

        ttk.Label(frm_inputs, text="País:").grid(row=2, column=0, sticky='w', pady=3)
        paises = sorted(e.pais for e in self.torneo.equipos.values())
        pais_cb = ttk.Combobox(frm_inputs, values=paises, state='readonly', width=24)
        if paises:
            pais_cb.set(paises[0])
        pais_cb.grid(row=2, column=1, sticky='w')

        # Deshabilitar campos según tipo
        def ajustar_campos():
            fecha_entry.config(state='disabled')
            grupo_cb.config(state='disabled')
            pais_cb.config(state='disabled')
            if tipo in (1, 5):
                fecha_entry.config(state='normal')
            elif tipo == 2:
                fecha_entry.config(state='normal')
                grupo_cb.config(state='normal')
            elif tipo in (3, 4):
                fecha_entry.config(state='normal')
                pais_cb.config(state='normal')
        ajustar_campos()

        ttk.Button(left, text="Generar Informe", command=lambda: generar()).pack(pady=10, fill='x')

        tree = ttk.Treeview(right, show='headings')
        tree.pack(fill='both', expand=True)

        def clear_tree(columns):
            tree.delete(*tree.get_children())
            tree["columns"] = columns
            for c in columns:
                tree.heading(c, text=c)
                tree.column(c, anchor='center', width=120)

        def generar():
            fecha_str = fecha_entry.get().strip()
            grupo = grupo_cb.get().strip()
            pais = pais_cb.get().strip()
            fecha = self._parse_date_strict(fecha_str) if fecha_str else None

            # --- Validaciones según tipo ---
            if tipo in (1, 2, 3, 4, 5) and not fecha:
                messagebox.showwarning("Fecha requerida", "Debe ingresar una fecha válida.")
                return

            if tipo == 2 and not grupo:
                messagebox.showwarning("Grupo requerido", "Debe seleccionar un grupo.")
                return

            if tipo in (3, 4) and not pais:
                messagebox.showwarning("País requerido", "Debe seleccionar un país.")
                return

            # --- Ejecución de informes ---
            if tipo == 1:
                self._informe_partidos_por_fecha(tree, fecha)
            elif tipo == 2:
                self._informe_tabla_grupo_fecha(tree, grupo, fecha)
            elif tipo == 3:
                self._informe_recorrido_pais(tree, pais, fecha)
            elif tipo == 4:
                self._informe_partido_mas_cercano(tree, pais, fecha)
            elif tipo == 5:
                self._informe_todas_tablas_fecha(tree, fecha)

    
    def _get_abbr_by_pais(self, pais):
        for id,e in self.torneo.equipos.items():
            if e.pais == pais:
                return e.abreviatura
        return pais[:3].upper() if pais else ""
