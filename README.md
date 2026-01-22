# Schell_scripting_training

## **High-Frequency RC Filter Optimizer**

This project provides an automated toolchain to optimize a low-pass RC filter for high-frequency applications (targeting up to **80GHz**). It bridges **Python**, **Shell**, and **NGSpice** to find the ideal component values while respecting physical layout constraints.

---

### **Overview**

The tool uses the **Newton-Raphson method** to iteratively solve for the target cutoff frequency. Unlike simple brute-force loops, this approach calculates the "rate of change" (slope) to converge on the target in significantly fewer simulation steps.

### **Core Features**

* **Hybrid Automation:** Python handles the high-level math, Shell manages simulation execution, and NGSpice performs the circuit analysis.
* **Newton-Raphson Optimization:** Calculates exact component adjustments based on experimental slope measurements.
* **Layout Constraints:** * **Resistor Range:**  to  (clamped for layout feasibility).
* **Capacitor Floor:** Minimum  to prevent physically impossible designs.


* **Robustness Logic:**
* **Anti-Oscillation:** Detects and breaks infinite loops by tracking component history.
* **Directional Recovery:** Automatically "kicks" the values if it hits a zero-slope "dead zone" (e.g., when the cutoff is far outside the simulation window).



---

### **Project Structure**

* `test.py`: The main Python controller containing the optimization engine.
* `ac_analysis.cir`: The SPICE netlist template generated dynamically during runtime.
* `output.txt`: The raw simulation data exported from NGSpice for Python to parse.

---

### **Getting Started**

1. **Prerequisites:** * Python 3.x
* [NGSpice](http://ngspice.sourceforge.net/) installed on your system.


2. **Configuration:** Update the `spice_path` variable in `test.py` to point to your local `ngspice.exe`.
3. **Run:** Execute the script:
```bash
python test.py

```



---

### **How it Works**

The script runs a simulation at a current value, then runs a second "nudge" simulation to determine the slope (). It uses this slope to "jump" to the next best guess. If it hits the resistor limit, it automatically scales the capacitor value and resets the search to ensure a valid layout-friendly solution.

**Would you like me to add a "How to Contribute" or a "Troubleshooting" section to this README?**
