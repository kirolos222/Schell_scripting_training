import subprocess
import os
import random
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

# --- 1. CORE SIMULATION FUNCTIONS (Keep these global) ---
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
    
    # Run ngspice via Shell
    subprocess.run([spice_path, "-b", "ac_analysis.cir"], stdout=subprocess.DEVNULL)

def get_actual_cutoff():
    if not os.path.exists("output.txt"): return 0
    with open("output.txt", "r") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2: continue
            try:
                freq = float(parts[0])
                voltage = float(parts[1])
                if voltage <= 0.707:
                    return freq
            except ValueError:
                continue
    return 0

# --- 2. GUI CLASS ---
class FilterTunerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Newton-Raphson RC Tuner")
        
        # --- UI Layout ---
        self.setup_widgets()
        
        # --- Matplotlib Setup ---
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
    def setup_widgets(self):
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(control_frame, text="Target Freq (GHz):").pack()
        self.target_entry = ttk.Entry(control_frame)
        self.target_entry.insert(0, "5") # Default 5 GHz
        self.target_entry.pack(pady=5)
        
        self.status_label = ttk.Label(control_frame, text="Status: Idle", foreground="blue")
        self.status_label.pack(pady=20)
        
        self.tune_btn = ttk.Button(control_frame, text="Start Auto-Tune", command=self.start_optimization)
        self.tune_btn.pack(pady=10)
        
        self.stats_text = tk.Text(control_frame, height=15, width=40)
        self.stats_text.pack(pady=10)

    def update_plot(self, r, c, current_f, target_f):
        self.ax.clear()
        
        # Simulate a theoretical curve for visualization
        f_range = np.logspace(0, 11, 100) # 1Hz to 100GHz
        gain = 1 / np.sqrt(1 + (2 * np.pi * f_range * r * c)**2)
        
        self.ax.semilogx(f_range, gain, label=f"R={r:.1f}Ω, C={c*1e15:.1f}fF")
        self.ax.axvline(x=current_f, color='blue', linestyle='--', label=f'Current: {current_f/1e9:.2f}G')
        self.ax.axvline(x=target_f, color='red', label=f'Target: {target_f/1e9:.2f}G')
        self.ax.axhline(y=0.707, color='green', linestyle=':')
        
        self.ax.set_ylim(0, 1.1)
        self.ax.set_title("Filter Magnitude Response")
        self.ax.legend()
        self.canvas.draw()

    def start_optimization(self):
        # --- GET USER INPUT ---
        try:
            target_input = float(self.target_entry.get())
            TARGET_FREQ = target_input * 1e9 # Convert GHz to Hz
        except ValueError:
            self.status_label.config(text="Error: Invalid Number", foreground="red")
            return

        # --- INITIALIZATION ---
        TOLERANCE = 0.01 * TARGET_FREQ
        resistor = 1000.0
        # Calculate initial Cap guess based on target
        cap = 1 / (2 * 3.14 * resistor * TARGET_FREQ)
        
        if cap < 10e-15: cap = 10e-15
        elif cap > 1e-6: cap = 100e-9

        # Constraints
        MIN_CAP = 50e-15
        MAX_RES = 100000.0
        MIN_RES = 10.0
        history = []

        self.status_label.config(text="Optimizing...", foreground="orange")
        self.stats_text.delete(1.0, tk.END)

        # --- THE OPTIMIZATION LOOP (Moved Inside) ---
        for attempt in range(50):
            # 1. LOOP DETECTION
            state = (round(resistor, 2), round(cap * 1e15, 2))
            if state in history:
                self.stats_text.insert(tk.END, "⚠️ Loop detected. Jittering...\n")
                resistor *= random.uniform(0.8, 1.2)
                history.clear()
                continue
            history.append(state)

            # 2. MEASURE CURRENT STATE
            run_simulation(resistor, cap)
            f1 = get_actual_cutoff()
            error = f1 - TARGET_FREQ
            
            # UPDATE GUI VISUALS
            self.update_plot(resistor, cap, f1, TARGET_FREQ)
            log_msg = f"Step {attempt}: R={resistor:.1f}Ω | C={cap*1e15:.1f}fF | F={f1/1e9:.2f}G\n"
            self.stats_text.insert(tk.END, log_msg)
            self.stats_text.see(tk.END)
            self.root.update() # IMPORTANT: Keeps GUI responsive!

            if abs(error) <= TOLERANCE:
                self.status_label.config(text="Success!", foreground="green")
                self.stats_text.insert(tk.END, f"\n✅ FINAL: R={resistor:.2f}Ω, C={cap*1e15:.2f}fF")
                break

            # 3. CALCULATE SLOPE
            nudge = resistor * 0.05 
            run_simulation(resistor + nudge, cap)
            f2 = get_actual_cutoff()
            slope = (f2 - f1) / nudge

            # 4. EMERGENCY SLOPE RECOVERY
            if abs(slope) < 1e-5:
                self.stats_text.insert(tk.END, "⚠️ Zero slope. Kicking...\n")
                if f1 < TARGET_FREQ:
                    resistor *= 0.5
                else:
                    resistor *= 2.0
                continue

            # 5. NEWTON JUMP
            new_resistor = resistor - (error / slope)
            
            # 6. LAYOUT CONSTRAINTS (Your Specific Logic)
            if new_resistor > MAX_RES:
                self.stats_text.insert(tk.END, "⚠️ Hit 100kΩ. Doubling Cap.\n")
                resistor = 50000.0
                cap *= 2
            elif new_resistor < MIN_RES:
                if cap > MIN_CAP:
                    self.stats_text.insert(tk.END, "⚠️ Hit 10Ω. Halving Cap.\n")
                    resistor = 500.0
                    cap = max(MIN_CAP, cap / 2)
                else:
                    self.status_label.config(text="Failed: Physical Limit", foreground="red")
                    break
            else:
                resistor = resistor + 0.7 * (new_resistor - resistor)

# --- START APP ---
if __name__ == "__main__":
    root = tk.Tk()
    app = FilterTunerGUI(root)
    root.mainloop()
