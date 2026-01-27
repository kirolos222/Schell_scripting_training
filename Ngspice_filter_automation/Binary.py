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
    * Automated Dual-Binary Search Optimization
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
                if float(parts[1]) <= 0.707:
                    return float(parts[0])
    except: return 0
    return 0

# --- 2. GUI CLASS ---
class FilterTunerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Dual-Binary Search Tuner (Best Fit Enabled)")
        self.setup_widgets()
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
    def setup_widgets(self):
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(control_frame, text="Target Frequency (GHz):").pack()
        self.target_entry = ttk.Entry(control_frame)
        self.target_entry.insert(0, "50")
        self.target_entry.pack(pady=5)
        
        self.status_label = ttk.Label(control_frame, text="Status: Idle", foreground="blue")
        self.status_label.pack(pady=20)
        
        self.tune_btn = ttk.Button(control_frame, text="Start Optimization", command=self.start_optimization)
        self.tune_btn.pack(pady=10)
        
        self.stats_text = tk.Text(control_frame, height=20, width=45, font=("Consolas", 9))
        self.stats_text.pack(pady=10)

    def update_plot(self, r, c, current_f, target_f):
        self.ax.clear()
        f_range = np.logspace(0, 11, 100)
        gain = 1 / np.sqrt(1 + (2 * np.pi * f_range * r * c)**2)
        self.ax.semilogx(f_range, gain, label=f"R={r:.1f}Ω, C={c*1e15:.1f}fF")
        self.ax.axvline(x=target_f, color='red', label='Target')
        self.ax.axvline(x=current_f, color='blue', linestyle='--', label='Actual')
        self.ax.axhline(y=0.707, color='green', linestyle=':')
        self.ax.set_ylim(0, 1.1)
        self.ax.legend()
        self.canvas.draw()

    def start_optimization(self):
        try:
            target_f = float(self.target_entry.get()) * 1e9
        except: return

        # Binary Search Parameters
        r_low, r_high = 10.0, 100000.0
        c_low, c_high = 50e-15, 1e-6
        
        # Best Fit Tracking Variables
        best_error = float('inf')
        best_r, best_c, best_f = 0, 0, 0
        
        TOLERANCE = 0.005 * target_f 
        self.stats_text.delete(1.0, tk.END)
        self.status_label.config(text="Searching...", foreground="orange")

        

        for i in range(40):
            # 1. Midpoint Calculation
            r_mid = (r_low + r_high) / 2
            c_mid = (c_low + c_high) / 2

            run_simulation(r_mid, c_mid)
            f_curr = get_actual_cutoff()
            if f_curr == 0: f_curr = 1e12 # Safety for out-of-bounds

            current_abs_error = abs(f_curr - target_f)
            
            # --- THE BEST FIT LOGIC ---
            if current_abs_error < best_error:
                best_error = current_abs_error
                best_r, best_c, best_f = r_mid, c_mid, f_curr
                marker = "⭐ NEW BEST"
            else:
                marker = ""

            self.update_plot(r_mid, c_mid, f_curr, target_f)

            log_msg = f"[{i}] R={r_mid:.1f} C={c_mid*1e15:.1f}f F={f_curr/1e9:.2f}G {marker}\n"
            self.stats_text.insert(tk.END, log_msg)
            self.stats_text.see(tk.END)
            self.root.update()

            # Success Check
            if current_abs_error <= TOLERANCE:
                self.status_label.config(text="Target Reached!", foreground="green")
                break

            # 2. Binary Search Update
            # (Frequency is inversely proportional to R and C)
            if f_curr > target_f:
                r_low, c_low = r_mid, c_mid # Too fast -> Increase RC
            else:
                r_high, c_high = r_mid, c_mid # Too slow -> Decrease RC

        # --- FINAL OUTPUT ---
        self.stats_text.insert(tk.END, "\n" + "="*30 + "\n")
        self.stats_text.insert(tk.END, "🏆 OPTIMIZED DESIGN FOUND:\n")
        self.stats_text.insert(tk.END, f"Best Resistance:  {best_r:.3f} Ω\n")
        self.stats_text.insert(tk.END, f"Best Capacitance: {best_c*1e15:.3f} fF\n")
        self.stats_text.insert(tk.END, f"Best Cutoff:      {best_f/1e9:.4f} GHz\n")
        self.stats_text.insert(tk.END, f"Final Error:     {(best_error/target_f)*100:.4f}%\n")
        self.stats_text.insert(tk.END, "="*30 + "\n")
        self.stats_text.see(tk.END)

# --- EXECUTION ---
if __name__ == "__main__":
    root = tk.Tk()
    app = FilterTunerGUI(root)
    root.mainloop()