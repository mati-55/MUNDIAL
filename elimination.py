# elimination.py
import tkinter as tk
from tkinter import ttk, messagebox
from utils import apply_style, center_fullscreen
from core import Torneo, Partido, Equipo
import pandas as pd
import os

class EliminationUI:
    """
    Gestiona octavos, cuartos, semis y final.
    Recibe Torneo ya con resultados de fase de grupos para calcular clasificados.
    Avance entre fases con botones manuales.
    """
    def __init__(self, master, torneo: Torneo):
        self.master = master
        self.master.title("Fases Eliminatorias")
        apply_style(self.master)
        center_fullscreen(self.master)
        self.torneo = torneo
        self.current_phase = 'Octavos'
        self.phases_order = ['Octavos','Cuartos','Semifinal','Final']
        # storage for matches per phase
        self.phase_matches = {p: [] for p in self.phases_order}
        # calculate qualifiers
        self.qualifiers = self._calculate_qualifiers()
        # generate octavos according to reglamento (simplified common mapping)
        self._generate_octavos()
        self.build_ui()
        self.load_phase(self.current_phase)

    def _calculate_qualifiers(self):
        # take top 2 from each group
        groups = sorted(set(e.grupo for e in self.torneo.equipos.values()))
        firsts = []; seconds = []; thirds = []
        for g in groups:
            tabla = self.torneo.calcular_tabla_posiciones(g)
            if len(tabla) >= 1: firsts.append(tabla[0].pais)
            if len(tabla) >= 2: seconds.append(tabla[1].pais)
            if len(tabla) >= 3: thirds.append({'pais':tabla[2].pais,'grupo':g,'stats':tabla[2].stats})
        # choose best 4 thirds by Pts, DG, GF
        thirds_sorted = sorted(thirds, key=lambda t: (t['stats']['Pts'], t['stats']['DG'], t['stats']['GF']), reverse=True)
        best_thirds = [t['pais'] for t in thirds_sorted[:4]]
        return {'1os': firsts, '2os': seconds, '3os_best': best_thirds}

    def _generate_octavos(self):
        # This mapping MUST respect regla III — here we use a typical mapping placeholder:
        # Example mapping (needs to be adapted to your PDF exact mapping if different)
        # We'll create 8 matches by combining firsts/seconds/thirds_best in a reasonable order
        f = self.qualifiers['1os']; s = self.qualifiers['2os']; t = self.qualifiers['3os_best']
        # We'll fill octavos as pairs. NOTE: for production adapt to exact mapping
        teams_order = []
        # choose a simple deterministic pairing for demonstration:
        # 1A vs 3C, 1B vs 3D, 1C vs 3A, 1D vs 3B, 1E vs 2F, 1F vs 2E, 2A vs 2C, 2B vs 2D
        # need mapping group->team id (search team by pais)
        group_map = {}
        for id, e in self.torneo.equipos.items():
            group_map.setdefault(e.grupo, []).append(e)
        # helper search: find identifier by pais
        def find_id_by_pais(pais):
            for id,e in self.torneo.equipos.items():
                if e.pais == pais:
                    return id
            return None
        pairs = []
        # simplistic pairs using available lists (may not exactly match PDF mapping)
        # fill from firsts and seconds
        # pair first 4 firsts with best thirds if available
        for i in range(min(4,len(f))):
            a = find_id_by_pais(f[i])
            b = find_id_by_pais(self.qualifiers['3os_best'][i]) if i < len(self.qualifiers['3os_best']) else None
            if a and b: pairs.append((a,b))
        # remaining pairs use other firsts vs seconds
        j = 4
        while len(pairs) < 8 and j < len(f):
            a = find_id_by_pais(f[j])
            # pair with a second not yet used
            for sec in s:
                b = find_id_by_pais(sec)
                if b and (a,b) not in pairs:
                    pairs.append((a,b)); break
            j += 1
        # fallback: pair any available not same
        ids = list(self.torneo.equipos.keys())
        i=0
        while len(pairs) < 8 and i+1 < len(ids):
            if (ids[i],ids[i+1]) not in pairs:
                pairs.append((ids[i],ids[i+1]))
            i+=2
        # create Partido objects
        for a,b in pairs:
            p = Partido(a,b,fecha="",hora="",fase="Octavos")
            mid = self.torneo.agregar_partido(p)
            self.phase_matches['Octavos'].append(mid)

    def build_ui(self):
        header = ttk.Frame(self.master,padding=8); header.pack(fill='x')
        ttk.Label(header, text="Fases Eliminatorias", style="Header.TLabel").pack()
        top = ttk.Frame(self.master,padding=8); top.pack(fill='x')
        self.phase_label = ttk.Label(top, text=self.current_phase); self.phase_label.pack(side='left')
        ttk.Button(top, text="Guardar Fase", command=self.save_phase).pack(side='right')
        ttk.Button(top, text="Continuar (siguiente fase)", command=self.next_phase).pack(side='right', padx=6)

        cols = ("ID","Fase","Equipo1","G1","vs","G2","Equipo2","Resultado")
        self.tree = ttk.Treeview(self.master, columns=cols, show='headings')
        for c in cols: self.tree.heading(c, text=c)
        self.tree.pack(fill='both', expand=True, padx=8, pady=8)
        self.tree.bind("<Double-1>", self._on_double_click)

    def load_phase(self, phase):
        self.phase_label.config(text=phase)
        self.tree.delete(*self.tree.get_children())
        # show matches that have p.fase == phase
        for mid,p in self.torneo.calendario.items():
            if p.fase != phase: continue
            e1 = self.torneo.equipos.get(p.id_equipo1).pais
            e2 = self.torneo.equipos.get(p.id_equipo2).pais
            res = f"{p.goles_e1} : {p.goles_e2}" if p.goles_e1 is not None else "PENDIENTE"
            self.tree.insert("", tk.END, iid=mid, values=(mid,p.fase,e1,p.goles_e1 if p.goles_e1 is not None else "", "vs", p.goles_e2 if p.goles_e2 is not None else "", e2, res))

    def _on_double_click(self, event):
        sel = self.tree.selection()
        if not sel: return
        mid = sel[0]; p = self.torneo.calendario.get(mid)
        if not p: return
        win = tk.Toplevel(self.master); win.title(f"Resultado {mid}")
        win.geometry("360x140"); win.transient(self.master); win.grab_set()
        e1 = ttk.Entry(win, width=6); e1.pack(pady=6)
        e2 = ttk.Entry(win, width=6); e2.pack(pady=6)
        e1.insert(0, "" if p.goles_e1 is None else str(p.goles_e1))
        e2.insert(0, "" if p.goles_e2 is None else str(p.goles_e2))
        def save():
            try:
                g1 = int(e1.get()); g2 = int(e2.get())
            except:
                messagebox.showerror("Error", "Goles deben ser enteros.")
                return
            p.goles_e1 = g1; p.goles_e2 = g2
            # recompute simple stats and save
            self.torneo.guardar_datos()
            win.destroy()
            self.load_phase(self.current_phase)
        ttk.Button(win, text="Guardar", command=save).pack(pady=8)

    def save_phase(self):
        # nothing extra needed: partidos ya guardados al editar. Save JSON and export excel
        self.torneo.guardar_datos()
        # export current phase to excel
        rows=[]
        for mid,p in self.torneo.calendario.items():
            if p.fase != self.current_phase: continue
            e1 = self.torneo.equipos.get(p.id_equipo1).pais; e2 = self.torneo.equipos.get(p.id_equipo2).pais
            rows.append({'ID':mid,'Fase':p.fase,'Equipo1':e1,'G1':p.goles_e1,'G2':p.goles_e2,'Equipo2':e2})
        out = os.path.join(os.path.dirname(__file__), f"Resultados_{self.current_phase}.xlsx")
        try:
            pd.DataFrame(rows).to_excel(out,index=False)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")
            return
        messagebox.showinfo("Guardado", f"Fase {self.current_phase} guardada y exportada.")

    def next_phase(self):
        idx = self.phases_order.index(self.current_phase)
        if idx < len(self.phases_order)-1:
            # confirm
            if not messagebox.askyesno("Confirmar", f"¿Desea avanzar a la siguiente fase ({self.phases_order[idx+1]})?"):
                return
            # compute winners from current phase to produce next phase matches (simple pairing sequential)
            winners = []
            for mid,p in list(self.torneo.calendario.items()):
                if p.fase != self.current_phase: continue
                if p.goles_e1 is None or p.goles_e2 is None:
                    messagebox.showwarning("Faltan resultados", "Hay partidos sin resultado. Complete antes de avanzar.")
                    return
                if p.goles_e1 > p.goles_e2: winners.append(p.id_equipo1)
                else: winners.append(p.id_equipo2)
            # pair winners sequentially
            next_phase = self.phases_order[idx+1]
            pairs=[]
            i=0
            while i+1 < len(winners):
                pairs.append((winners[i], winners[i+1])); i+=2
            # create Partido for next phase
            for a,b in pairs:
                pp = Partido(a,b,fecha="",hora="",fase=next_phase)
                self.torneo.agregar_partido(pp)
            self.current_phase = next_phase
            self.torneo.guardar_datos()
            self.load_phase(self.current_phase)
        else:
            messagebox.showinfo("Info", "Ya estás en la última fase.")
