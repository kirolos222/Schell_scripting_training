import subprocess
import os

TARGET_FREQ = 80*1000000000  # The frequency we want to achieve
TOLERANCE = 0.01*TARGET_FREQ     # How close is "good enough" (in Hz)
resistor = 10000.0     # Starting guess (1k Ohm)
cap= 1 / (2 * 3.14 * resistor * TARGET_FREQ)
if cap < 1e-15:
    cap =10*1e-15
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

# --- THE OPTIMIZATION LOOP ---
print(f"Targeting Cutoff: {TARGET_FREQ} Hz")

for attempt in range(100):
    run_simulation(resistor,cap)
    current_cutoff = get_actual_cutoff()
    
    error = current_cutoff - TARGET_FREQ
    print(f"Step {attempt}: R={resistor:.2f}Ω |C={cap*1000000000000000:.2f}fF | Cutoff={current_cutoff/1000000000:.2f}GHz")

    if abs(error) <= TOLERANCE:
        print(f"✅ Success! Ideal Resistor: {resistor:.2f} Ohms")
        break
    
    # Simple logic: If frequency is too high, increase Resistance
    # Frequency = 1 / (2 * pi * R * C)
    if current_cutoff > TARGET_FREQ and resistor<=50e3:
        resistor += 10
    elif current_cutoff < TARGET_FREQ  and resistor>50 :
        resistor -= 10
    elif current_cutoff > TARGET_FREQ and resistor>50e3 and cap < 1e-6:
        cap += cap/100
    elif current_cutoff < TARGET_FREQ  and resistor<=50 and cap > 10*1e-15:
        cap -= cap/100   
   