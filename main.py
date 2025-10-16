# main.py
import tkinter as tk
from assigner import GroupAssigner
from phase_groups import PhaseGroupsUI
from elimination import EliminationUI
from utils import apply_style, center_fullscreen
import os

def run_assigner_and_flow():
    # Step 1 - Assign groups
    root = tk.Tk()
    app = GroupAssigner(root)
    root.mainloop()
    # Check if assigner completed
    if not hasattr(app, 'assigned_data'):
        print("Asignación cancelada, saliendo.")
        return
    assigned = app.assigned_data
    matches = app.generated_matches

    # Step 2 - Phase Groups (Jornadas)
    root2 = tk.Tk()
    pg = PhaseGroupsUI(root2, assigned, matches)
    root2.mainloop()
    # After PhaseGroupsUI closes, tournament data file exists and contains group results
    # Load Torneo from core and pass to elimination UI
    from core import Torneo
    torneo = Torneo()
    # Step 3 - Eliminations
    root3 = tk.Tk()
    elim = EliminationUI(root3, torneo)
    root3.mainloop()
    print("Flujo completo terminado.")

if __name__ == "__main__":
    run_assigner_and_flow()
