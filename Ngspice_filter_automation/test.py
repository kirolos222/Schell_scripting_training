import subprocess
import os
import random
TARGET_FREQ = 8 *1e9  # The frequency we want to achieve
TOLERANCE = 0.01*TARGET_FREQ     # How close is "good enough" (in Hz)
resistor = 1000.0     # Starting guess (1k Ohm)
cap= 1 / (2 * 3.14 * resistor * TARGET_FREQ)

if cap < 10e-15:
    cap =100*1e-15
elif cap >1e-6:
    cap =100*1e-9
def run_simulation(r_val,C_VAL):
    # The 'r' before the string handles the Windows path backslashes
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
                # 0.707 is the standard -3dB cutoff point
                if voltage <= 0.707:
                    return freq
            except ValueError:
                continue
    return 0

# --- THE LAYOUT-CONSTRAINED NEWTON LOOP ---
MIN_CAP = 50e-15 # 50fF Limit
# --- THE OPTIMIZATION LOOP ---
print(f"Targeting Cutoff: {TARGET_FREQ/1e9} GHz")
history = []
MAX_RES = 100000.0      # 100k Layout Limit
MIN_RES = 10.0
for attempt in range(50):
    # 1. LOOP DETECTION
    state = (round(resistor, 2), round(cap * 1e15, 2))
    if state in history:
        print("⚠️ Infinite loop detected. Jittering resistor...")
        resistor *= random.uniform(0.8, 1.2)
        history.clear()
        continue
    history.append(state)

    # 2. MEASURE CURRENT STATE
    run_simulation(resistor, cap)
    f1 = get_actual_cutoff()
    error = f1 - TARGET_FREQ
    
    print(f"Step {attempt}: R={resistor:.2f}Ω | C={cap*1e15:.2f}fF | Freq={f1/1e9:.2f}GHz")

    if abs(error) <= TOLERANCE:
        print(f"✅ Success! R: {resistor:.2f}Ω, C: {cap*1e15:.2f}fF")
        break

    # 3. CALCULATE SLOPE WITH RELATIVE NUDGE
    nudge = resistor * 0.05 
    run_simulation(resistor + nudge, cap)
    f2 = get_actual_cutoff()
    slope = (f2 - f1) / nudge

    # 4. EMERGENCY SLOPE RECOVERY (The "Dead Zone" Fix)
    if abs(slope) < 1e-5:
        print("⚠️ Zero slope. Directional kick...")
        if f1 < TARGET_FREQ:
            resistor *= 0.5  # Need higher freq? Drop R
        else:
            resistor *= 2.0  # Need lower freq? Raise R
        continue

    # 5. NEWTON JUMP WITH DAMPING
    new_resistor = resistor - (error / slope)
    
    # 6. LAYOUT & PHYSICAL CONSTRAINTS
    if new_resistor > MAX_RES:
        print("⚠️ R hit 100k. Increasing Cap.")
        resistor = 50000.0
        cap *= 2
    elif new_resistor < MIN_RES:
        if cap > MIN_CAP:
            print(f"⚠️ R hit 10Ω. Reducing Cap (Floor: {MIN_CAP*1e15}fF).")
            resistor = 500.0
            cap = max(MIN_CAP, cap / 2)
    else:
        # Standard Step with 0.7 damping for stability
        resistor = resistor + 0.7 * (new_resistor - resistor)