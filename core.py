# core.py
import os
import json
from dataclasses import dataclass, field
from typing import Dict
import pandas as pd
from tkinter import messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

@dataclass
class Equipo:
    identificador: str
    pais: str
    abreviatura: str = ""
    confederacion: str = ""
    grupo: str = ""
    stats: dict = field(default_factory=lambda: {
        'PJ': 0, 'G': 0, 'E': 0, 'P': 0,
        'GF': 0, 'GC': 0, 'DG': 0, 'Pts': 0,
        'MaxAvance': 'Fase de Grupos'
    })

    def to_dict(self):
        return {
            'identificador': self.identificador,
            'pais': self.pais,
            'abreviatura': self.abreviatura or self.pais[:3].upper(),
            'confederacion': self.confederacion,
            'grupo': self.grupo,
            'stats': self.stats
        }

@dataclass
class Partido:
    id_equipo1: str
    id_equipo2: str
    fecha: str = ""
    hora: str = ""
    fase: str = "Fase de Grupos"
    goles_e1: int = None
    goles_e2: int = None
    tarj_ama_e1: int = 0
    tarj_ama_e2: int = 0
    tarj_roja_e1: int = 0
    tarj_roja_e2: int = 0
    jugador_stats: list = field(default_factory=list)

    def to_dict(self):
        return self.__dict__

class Torneo:
    def __init__(self, nombre="Copa Mundial Sub-20 de la FIFA Chile 2025"):
        self.nombre = nombre
        self.pais_sede = "Chile"
        self.fecha_inicio = "2025-09-27"
        self.fecha_fin = "2025-10-19"
        self.configuracion_cerrada = False
        self.equipos: Dict[str, Equipo] = {}
        self.grupos = set()
        self.calendario: Dict[str, Partido] = {}
        self._match_id_counter = 1
        self.FILENAME = os.path.join(SCRIPT_DIR, 'torneo_data.json') #en enta parte crea la BD digamos
        self.cargar_datos()

    def agregar_equipo(self, equipo: Equipo):
        self.equipos[equipo.identificador] = equipo
        if equipo.grupo:
            self.grupos.add(equipo.grupo)

    def agregar_equipo_dict(self, d):
        e = Equipo(d['identificador'], d['pais'], d.get('abreviatura',''), d.get('confederacion',''), d.get('grupo',''))
        self.agregar_equipo(e)

    def agregar_partido(self, partido: Partido):
        match_id = f"M{self._match_id_counter:03d}"
        self.calendario[match_id] = partido
        self._match_id_counter += 1
        return match_id

    def cerrar_configuracion(self):
        self.configuracion_cerrada = True
        self.guardar_datos()

    def registrar_resultado(self, match_id, goles_e1, goles_e2, ta1=0, ta2=0, tr1=0, tr2=0):
        if not self.configuracion_cerrada:
            messagebox.showerror("Error", "Debe cerrar la configuración antes de registrar resultados.")
            return False
        partido = self.calendario.get(match_id)
        if not partido:
            messagebox.showerror("Error", f"Partido {match_id} no encontrado.")
            return False

        partido.goles_e1 = goles_e1
        partido.goles_e2 = goles_e2
        partido.tarj_ama_e1 = ta1
        partido.tarj_ama_e2 = ta2
        partido.tarj_roja_e1 = tr1
        partido.tarj_roja_e2 = tr2

        e1 = self.equipos.get(partido.id_equipo1)
        e2 = self.equipos.get(partido.id_equipo2)
        if not e1 or not e2:
            messagebox.showerror("Error", "Equipos del partido no encontrados en torneo.")
            return False

        e1.stats['PJ'] += 1
        e2.stats['PJ'] += 1
        e1.stats['GF'] += goles_e1
        e2.stats['GF'] += goles_e2
        e1.stats['GC'] += goles_e2
        e2.stats['GC'] += goles_e1

        if goles_e1 > goles_e2:
            e1.stats['G'] += 1; e2.stats['P'] += 1; e1.stats['Pts'] += 3
        elif goles_e1 < goles_e2:
            e2.stats['G'] += 1; e1.stats['P'] += 1; e2.stats['Pts'] += 3
        else:
            e1.stats['E'] += 1; e2.stats['E'] += 1; e1.stats['Pts'] += 1; e2.stats['Pts'] += 1

        e1.stats['DG'] = e1.stats['GF'] - e1.stats['GC']
        e2.stats['DG'] = e2.stats['GF'] - e2.stats['GC']

        self.guardar_datos()
        return True

    def calcular_tabla_posiciones(self, grupo_id):
        equipos_grupo = [e for e in self.equipos.values() if e.grupo == grupo_id]
        tabla_ordenada = sorted(equipos_grupo, key=lambda e: (e.stats['Pts'], e.stats['DG'], e.stats['GF']), reverse=True)
        return tabla_ordenada

    def guardar_datos(self):
        data = {
            'torneo': {
                'nombre': self.nombre,
                'pais_sede': self.pais_sede,
                'fecha_inicio': self.fecha_inicio,
                'fecha_fin': self.fecha_fin,
                'configuracion_cerrada': self.configuracion_cerrada,
                '_match_id_counter': self._match_id_counter
            },
            'equipos': {id: e.to_dict() for id, e in self.equipos.items()},
            'calendario': {id: p.to_dict() for id, p in self.calendario.items()}
        }
        try:
            with open(self.FILENAME, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo guardar datos: {ex}")

    def cargar_datos(self):
        if not os.path.exists(self.FILENAME):
            return
        try:
            with open(self.FILENAME, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return
        t_data = data.get('torneo', {})
        self.nombre = t_data.get('nombre', self.nombre)
        self.configuracion_cerrada = t_data.get('configuracion_cerrada', False)
        self._match_id_counter = t_data.get('_match_id_counter', 1)
        self.equipos = {}
        for id, e_data in data.get('equipos', {}).items():
            equipo = Equipo(e_data['identificador'], e_data['pais'], e_data.get('abreviatura',''), e_data.get('confederacion',''), e_data.get('grupo',''))
            equipo.stats = e_data.get('stats', equipo.stats)
            self.equipos[id] = equipo
            if equipo.grupo:
                self.grupos.add(equipo.grupo)
        self.calendario = {}
        for id, p_data in data.get('calendario', {}).items():
            partido = Partido(p_data['id_equipo1'], p_data['id_equipo2'], p_data.get('fecha',''), p_data.get('hora',''), p_data.get('fase','Fase de Grupos'))
            partido.goles_e1 = p_data.get('goles_e1')
            partido.goles_e2 = p_data.get('goles_e2')
            partido.tarj_ama_e1 = p_data.get('tarj_ama_e1', 0)
            partido.tarj_ama_e2 = p_data.get('tarj_ama_e2', 0)
            partido.tarj_roja_e1 = p_data.get('tarj_roja_e1', 0)
            partido.tarj_roja_e2 = p_data.get('tarj_roja_e2', 0)
            partido.jugador_stats = p_data.get('jugador_stats', [])
            self.calendario[id] = partido
    # ============================================================
    # 🔹 Obtener equipo por posición (para las llaves de eliminación)
    # ============================================================
    def obtener_equipo_por_posicion(self, posicion_str):
        """
        Devuelve el equipo correspondiente a un string como:
        '1°A', '2°C', '3°B/E/F' según las tablas de posiciones actuales.
        Si la posición contiene varias opciones (3°B/E/F), elige una al azar.
        """
        import random

        if not posicion_str or len(posicion_str) < 3:
            return None

        try:
            pos = int(posicion_str[0])  # 1, 2 o 3
            grupos = []

            partes = posicion_str.split("°")[-1]
            if "/" in partes:
                grupos = partes.split("/")
            else:
                grupos = [partes]

            grupos = [g.strip() for g in grupos if g.strip().isalpha()]

            if not grupos:
                return None

            grupo = random.choice(grupos)
            tabla = self.calcular_tabla_posiciones(grupo)

            if len(tabla) >= pos:
                return tabla[pos - 1]  # Devuelve el objeto Equipo
            return None
        except Exception as e:
            print("Error en obtener_equipo_por_posicion:", e)
            return None

    # ============================================================
    # 🔹 Generar rondas de eliminación automáticamente
    # ============================================================
    def generar_rondas_eliminacion(self):
        """
        Genera automáticamente los partidos de las siguientes fases de eliminación
        (Octavos → Cuartos → Semifinal → Final)
        en base a los ganadores de los encuentros anteriores.
        """
        nuevas_rondas = []

        # --- Orden de fases ---
        fases_orden = ["Octavos de final", "Cuartos de final", "Semifinal", "Final"]

        # Buscar la fase actual
        fase_actual = None
        for fase in fases_orden:
            if any(p.fase == fase for p in self.calendario.values()):
                fase_actual = fase
                break

        if not fase_actual:
            print("⚠️ No hay fase de eliminación actual para avanzar.")
            return

        # --- Obtener ganadores ---
        ganadores = []
        for p in self.calendario.values():
            if p.fase != fase_actual:
                continue
            if p.goles_e1 is None or p.goles_e2 is None:
                continue
            if p.goles_e1 > p.goles_e2:
                ganadores.append(self.equipos[p.id_equipo1])
            elif p.goles_e2 > p.goles_e1:
                ganadores.append(self.equipos[p.id_equipo2])

        if not ganadores:
            print("⚠️ No hay ganadores aún en la fase actual.")
            return

        # --- Siguiente fase ---
        idx = fases_orden.index(fase_actual)
        if idx + 1 >= len(fases_orden):
            print("🏁 El torneo ya llegó a la final.")
            return

        fase_siguiente = fases_orden[idx + 1]
        print(f"➡️ Generando {fase_siguiente} con {len(ganadores)} equipos...")

        # --- Crear nuevos partidos ---
        for i in range(0, len(ganadores), 2):
            if i + 1 < len(ganadores):
                e1 = ganadores[i]
                e2 = ganadores[i + 1]
                nuevo_partido = Partido(e1.id_equipo1 if hasattr(e1, 'id_equipo1') else e1.identificador,
                                        e2.id_equipo1 if hasattr(e2, 'id_equipo1') else e2.identificador,
                                        fecha="", hora="", fase=fase_siguiente)
                self.agregar_partido(nuevo_partido)
                nuevas_rondas.append(nuevo_partido)

        # Guardar resultados
        if nuevas_rondas:
            self.guardar_datos()
            print(f"✅ {len(nuevas_rondas)} partidos creados para {fase_siguiente}.")

    # ============================================================
    # 🔹 Obtener ganadores de una fase específica
    # ============================================================
    def obtener_ganadores_fase(self, fase):
        """Devuelve una lista con los equipos ganadores de la fase especificada."""
        ganadores = []
        for p in self.calendario.values():
            if p.fase != fase:
                continue
            if p.goles_e1 is None or p.goles_e2 is None:
                continue
            if p.goles_e1 > p.goles_e2:
                ganadores.append(self.equipos[p.id_equipo1])
            elif p.goles_e2 > p.goles_e1:
                ganadores.append(self.equipos[p.id_equipo2])
        return ganadores

def load_teams_from_excel(filename="FIFA_Sub20_2025_Equipos.xlsx"):
    path = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(path):
        # fallback sample 24
        sample = [
            "Arabia Saudita","Argentina","Australia","Brasil","Chile","Colombia",
            "Corea del Sur","Cuba","Egipto","España","Estados Unidos","Francia",
            "Italia","Japón","Marruecos","México","Nigeria","Noruega",
            "Nueva Caledonia","Nueva Zelanda","Panamá","Paraguay","Sudáfrica","Ucrania"
        ]
        messagebox.showwarning("Archivo no encontrado", f"No se encontró '{os.path.basename(path)}' en la carpeta del script.\nSe cargó una lista de ejemplo ({len(sample)} países).")
        return sample
    try:
        df = pd.read_excel(path)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo leer '{os.path.basename(path)}': {e}")
        return []
    col_name = None
    for c in df.columns:
        if str(c).strip().lower() in ('pais','país','equipo','team','country','selección','seleccion'):
            col_name = c
            break
    if not col_name:
        col_name = df.columns[0]
    equipos = df[col_name].dropna().astype(str).tolist()
    seen = set(); unique = []
    for e in equipos:
        en = e.strip()
        if en and en not in seen:
            seen.add(en); unique.append(en)
    return unique
