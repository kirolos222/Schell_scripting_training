import subprocess
import os
import random
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

# --- 1. CORE SIMULATION FUNCTIONS ---
def run_simulation(r_val, C_VAL):
    spice_path = r"d:\Spice64\bin\ngspice.exe" 
    
    netlist = f"""
    * Automated Filter Optimization
    V1 in 0 AC 1
    R1 in out {r_val}
    C1 out 0 {C_VAL}
    .ac dec 20 1 200G
    .control
        run
        wrdata output.txt v(out)
        quit
    .endc
    .end
    """
    with open("ac_analysis.cir", "w") as f:
        f.write(netlist)
    
    subprocess.run([spice_path, "-b", "ac_analysis.cir"], stdout=subprocess.DEVNULL)

def get_actual_cutoff():
    if not os.path.exists("output.txt"): return 0
    try:
        with open("output.txt", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 2: continue
                freq = float(parts[0])
                voltage = float(parts[1])
                if voltage <= 0.707:
                    return freq
    except (ValueError, FileNotFoundError):
        return 0
    return 0

# --- 2. GUI CLASS ---
class FilterTunerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Dual-Parameter RC Optimizer (with Best-Fit Memory)")
        
        self.setup_widgets()
        
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
    def setup_widgets(self):
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(control_frame, text="Target Freq (GHz):").pack()
        self.target_entry = ttk.Entry(control_frame)
        self.target_entry.insert(0, "5")
        self.target_entry.pack(pady=5)
        
        self.status_label = ttk.Label(control_frame, text="Status: Idle", foreground="blue")
        self.status_label.pack(pady=20)
        
        self.tune_btn = ttk.Button(control_frame, text="Start Auto-Tune", command=self.start_optimization)
        self.tune_btn.pack(pady=10)
        
        self.stats_text = tk.Text(control_frame, height=20, width=45, font=("Consolas", 9))
        self.stats_text.pack(pady=10)

    def update_plot(self, r, c, current_f, target_f):
        self.ax.clear()
        f_range = np.logspace(0, 11, 100)
        gain = 1 / np.sqrt(1 + (2 * np.pi * f_range * r * c)**2)
        
        self.ax.semilogx(f_range, gain, color='black', label=f"R={r:.1f}Ω, C={c*1e15:.1f}fF")
        self.ax.axvline(x=current_f, color='blue', linestyle='--', label=f'Current: {current_f/1e9:.2f}G')
        self.ax.axvline(x=target_f, color='red', label=f'Target: {target_f/1e9:.2f}G')
        self.ax.axhline(y=0.707, color='green', linestyle=':')
        
        self.ax.set_ylim(0, 1.1)
        self.ax.set_title("Filter Magnitude Response")
        self.ax.legend()
        self.canvas.draw()

    def start_optimization(self):
        try:
            target_input = float(self.target_entry.get())
            TARGET_FREQ = target_input * 1e9
        except ValueError:
            self.status_label.config(text="Error: Invalid Number", foreground="red")
            return

        TOLERANCE = 0.005 * TARGET_FREQ 
        FINE_TUNE_THRESHOLD = 0.10 * TARGET_FREQ 
        
        resistor = 1000.0
        cap = 1 / (2 * 3.14 * resistor * TARGET_FREQ)
        
        # Constraints
        MIN_CAP = 50e-15
        MAX_RES = 100000.0
        MIN_RES = 10.0
        
        # --- NEW: BEST-FIT MEMORY TRACKERS ---
        best_error = float('inf')
        best_r, best_c, best_f = 0, 0, 0
        
        history = []
        fine_tune_turn = "R" 

        self.status_label.config(text="Optimizing...", foreground="orange")
        self.stats_text.delete(1.0, tk.END)

        for attempt in range(200): 
            state = (round(resistor, 2), round(cap * 1e15, 2))
            if state in history:
                resistor *= random.uniform(0.9, 1.1)
                history.clear()
                continue
            history.append(state)

            run_simulation(resistor, cap)
            f1 = get_actual_cutoff()
            error = f1 - TARGET_FREQ
            abs_error = abs(error)
            
            # --- TRACK THE BEST RESULT ---
            if abs_error < best_error:
                best_error = abs_error
                best_r, best_c, best_f = resistor, cap, f1
                marker = "⭐ [BEST]"
            else:
                marker = ""
            
            self.update_plot(resistor, cap, f1, TARGET_FREQ)
            
            in_fine_tune = abs_error <= FINE_TUNE_THRESHOLD
            mode_msg = "[Fine]" if in_fine_tune else "[Newt]"
            log_msg = f"{mode_msg} {attempt}: R={resistor:.1f}Ω | F={f1/1e9:.2f}G {marker}\n"
            
            self.stats_text.insert(tk.END, log_msg)
            self.stats_text.see(tk.END)
            self.root.update()

            if abs_error <= TOLERANCE:
                self.status_label.config(text="Success!", foreground="green")
                break

            # 3. HYBRID LOGIC: DUAL-PARAMETER FINE TUNING
            if in_fine_tune:
                step_size = 0.005 
                if fine_tune_turn == "R":
                    resistor = resistor * (1 + step_size) if f1 > TARGET_FREQ else resistor * (1 - step_size)
                    fine_tune_turn = "C" 
                else:
                    new_cap = cap * (1 + step_size) if f1 > TARGET_FREQ else cap * (1 - step_size)
                    cap = max(MIN_CAP, new_cap)
                    fine_tune_turn = "R" 
                continue

            # 4. STANDARD NEWTON RAPHSON (Coarse Tuning)
            nudge = resistor * 0.05 
            run_simulation(resistor + nudge, cap)
            f2 = get_actual_cutoff()
            slope = (f2 - f1) / nudge

            if abs(slope) < 1e-5:
                if f1 < TARGET_FREQ: resistor *= 0.5
                else: resistor *= 2.0
                continue

            new_resistor = resistor - (error / slope)
            
            # 5. LAYOUT CONSTRAINTS
            if new_resistor > MAX_RES:
                resistor = 50000.0
                cap *= 2
            elif new_resistor < MIN_RES:
                if cap > MIN_CAP:
                    resistor = 500.0
                    cap = max(MIN_CAP, cap / 2)
            else:
                resistor = resistor + 0.7 * (new_resistor - resistor)

        # --- FINAL OUTPUT OF BEST SAVED STATE ---
        self.stats_text.insert(tk.END, "\n" + "="*35 + "\n")
        self.stats_text.insert(tk.END, "🏆 OPTIMAL DESIGN SUMMARY:\n")
        self.stats_text.insert(tk.END, f"Best Resistance:  {best_r:.2f} Ω\n")
        self.stats_text.insert(tk.END, f"Best Capacitance: {best_c*1e15:.2f} fF\n")
        self.stats_text.insert(tk.END, f"Best Frequency:   {best_f/1e9:.4f} GHz\n")
        self.stats_text.insert(tk.END, f"Minimum Error:    {(best_error/TARGET_FREQ)*100:.4f}%\n")
        self.stats_text.insert(tk.END, "="*35 + "\n")
        self.stats_text.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = FilterTunerGUI(root)
    root.mainloop()