# assigner.py
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from utils import apply_style, center_fullscreen
from core import load_teams_from_excel
import os

class GroupAssigner:
    def __init__(self, master):
        self.master = master
        self.master.title("Asignación de Grupos")
        apply_style(self.master)
        center_fullscreen(self.master)

        teams = load_teams_from_excel()
        # unique sanitize
        unique = []
        for t in teams:
            if isinstance(t, str) and t.strip() and t.strip() not in unique:
                unique.append(t.strip())
        self.pool = unique
        self.groups_order = ['A','B','C','D','E','F']
        self.groups = {g: [] for g in self.groups_order}
        self.current_group_idx = 0

        self.build_ui()
        self.update_ui()

    def build_ui(self):
        header = ttk.Frame(self.master, padding=8); header.pack(fill='x')
        ttk.Label(header, text="Asignación de Grupos (click país para asignar)", style="Header.TLabel").pack()

        main = ttk.Frame(self.master, padding=12); main.pack(fill='both', expand=True)

        left = ttk.Frame(main); left.pack(side='left', fill='both', expand=True, padx=(0,12))
        ttk.Label(left, text="Países disponibles").pack(anchor='w')
        self.pool_listbox = tk.Listbox(left, font=('Segoe UI',12), selectbackground='#cfe0ff', activestyle='none')
        self.pool_listbox.pack(fill='both', expand=True)
        self.pool_listbox.bind("<Button-1>", self.on_country_click)
        for p in self.pool: self.pool_listbox.insert(tk.END, p)

        right = ttk.Frame(main); right.pack(side='right', fill='both', expand=True)
        self.group_label = ttk.Label(right, text="", style="Header.TLabel"); self.group_label.pack()
        ttk.Label(right, text="Equipos asignados:").pack(anchor='w', pady=(6,0))
        self.assigned_listbox = tk.Listbox(right, font=('Segoe UI',12), height=8); self.assigned_listbox.pack(fill='x', pady=6)

        pos_frame = ttk.Frame(right); pos_frame.pack(fill='x', pady=(6,12))
        self.position_labels = []
        for i in range(4):
            lbl = ttk.Label(pos_frame, text=f"{i+1}. ---", relief='ridge', padding=6)
            lbl.pack(side='left', expand=True, fill='x', padx=4)
            self.position_labels.append(lbl)

        ctrl = ttk.Frame(right); ctrl.pack(pady=6)
        self.prev_btn = ttk.Button(ctrl, text="<< Grupo anterior", command=self.go_prev_group); self.prev_btn.grid(row=0,column=0,padx=6)
        self.next_btn = ttk.Button(ctrl, text="Siguiente grupo >>", command=self.go_next_group); self.next_btn.grid(row=0,column=1,padx=6)

        bottom = ttk.Frame(self.master, padding=10); bottom.pack(fill='x')
        self.info_label = ttk.Label(bottom, text="Cada grupo tiene 4 equipos. Avanza automáticamente o con los botones.")
        self.info_label.pack(side='left')
        self.save_btn = ttk.Button(bottom, text="Finalizar asignación", command=self.finish_assignments, state='disabled')
        self.save_btn.pack(side='right')

    def on_country_click(self, event):
        widget = event.widget
        idx = widget.nearest(event.y)
        try:
            country = widget.get(idx)
        except Exception:
            return
        if country:
            self.assign_country(country)

    def assign_country(self, country):
        # duplicate check
        for g in self.groups:
            if country in self.groups[g]:
                messagebox.showinfo("Duplicado", f"{country} ya está en el Grupo {g}.")
                return
        cg = self.groups_order[self.current_group_idx]
        if len(self.groups[cg]) >= 4:
            messagebox.showwarning("Grupo completo", f"Grupo {cg} completo.")
            return
        self.groups[cg].append(country)
        # remove from pool and listbox
        try:
            idx = self.pool.index(country)
            self.pool.pop(idx)
        except ValueError:
            pass
        self.refresh_pool_listbox()
        self.update_assigned()
        if len(self.groups[cg]) == 4 and self.current_group_idx < len(self.groups_order)-1:
            messagebox.showinfo("Grupo completo", f"Grupo {cg} completo. Avanzando al Grupo {self.groups_order[self.current_group_idx+1]}.")
            self.current_group_idx += 1
        self.update_ui()

    def refresh_pool_listbox(self):
        self.pool_listbox.delete(0, tk.END)
        for p in self.pool: self.pool_listbox.insert(tk.END, p)

    def update_assigned(self):
        cg = self.groups_order[self.current_group_idx]
        self.assigned_listbox.delete(0, tk.END)
        for i,p in enumerate(self.groups[cg], start=1):
            self.assigned_listbox.insert(tk.END, f"{i}. {p}")
        for i in range(4):
            self.position_labels[i].config(text=f"{i+1}. {self.groups[cg][i] if i < len(self.groups[cg]) else '---'}")

    def update_ui(self):
        cg = self.groups_order[self.current_group_idx]
        self.group_label.config(text=f"Grupo {cg}")
        self.update_assigned()
        self.prev_btn.config(state='normal' if self.current_group_idx>0 else 'disabled')
        self.next_btn.config(state='normal' if self.current_group_idx < len(self.groups_order)-1 else 'disabled')
        all_full = all(len(self.groups[g])==4 for g in self.groups_order)
        self.save_btn.config(state='normal' if all_full else 'disabled')

    def go_prev_group(self):
        if self.current_group_idx>0:
            self.current_group_idx-=1; self.update_ui()

    def go_next_group(self):
        if self.current_group_idx < len(self.groups_order)-1:
            self.current_group_idx+=1; self.update_ui()

    def finish_assignments(self):
        # validation
        for g in self.groups_order:
            if len(self.groups[g]) != 4:
                messagebox.showwarning("Faltan equipos", f"Grupo {g} no tiene 4 equipos.")
                return
        # write to excel
        rows=[]
        for g in self.groups_order:
            for pos,pais in enumerate(self.groups[g], start=1):
                rows.append({'Grupo':g,'Posicion':pos,'Equipo':pais})
        df = pd.DataFrame(rows)
        out = os.path.join(os.path.dirname(__file__),'Grupos_Asignados_Sub20_2025(python genera).xlsx')
        try:
            df.to_excel(out,index=False)
        except Exception as e:
            messagebox.showerror("Error", f"No se guardaron grupos: {e}")
            return
        messagebox.showinfo("Listo", f"Grupos guardados en {os.path.basename(out)}")
        # generate matches for group stage (J1,J2,J3) and save
        matches=[]
        for g in self.groups_order:
            teams = self.groups[g]
            # J1
            matches.append({'Grupo':g,'Jornada':1,'Equipo1':teams[0],'Equipo2':teams[1]})
            matches.append({'Grupo':g,'Jornada':1,'Equipo1':teams[2],'Equipo2':teams[3]})
            # J2
            matches.append({'Grupo':g,'Jornada':2,'Equipo1':teams[0],'Equipo2':teams[2]})
            matches.append({'Grupo':g,'Jornada':2,'Equipo1':teams[3],'Equipo2':teams[1]})
            # J3
            matches.append({'Grupo':g,'Jornada':3,'Equipo1':teams[3],'Equipo2':teams[0]})
            matches.append({'Grupo':g,'Jornada':3,'Equipo1':teams[1],'Equipo2':teams[2]})
        dfm = pd.DataFrame(matches)
        outm = os.path.join(os.path.dirname(__file__),'FIFA_Sub20_2025_FaseGrupos_Partidos.xlsx')
        try:
            dfm.to_excel(outm,index=False)
        except Exception as e:
            messagebox.showerror("Error", f"No se guardaron partidos: {e}")
            return
        messagebox.showinfo("Partidos generados", f"Partidos de fase de grupos guardados en {os.path.basename(outm)}")
        # store results for caller and close window
        self.assigned_data = self.groups.copy()
        self.generated_matches = matches
        self.master.destroy()
