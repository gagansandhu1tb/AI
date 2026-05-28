# Project Hail Mary — Simulation

Run the interactive GUI and see event log output in the terminal.

Which GUI to use
- Use `run_gui.py` (preferred). A single polished tkinter GUI is provided.
- `run_interactive.py` was removed to avoid duplication. Use `run_gui.py`.
- This repository now keeps only the GUI runner, so the project is simpler and easier to maintain.

Run instructions
1. Open a terminal (PowerShell or CMD) in the project folder.
2. Run the GUI so you can see event log messages in the same terminal:

```powershell
python run_gui.py
```

Notes
- The simulation prints event log lines to the terminal (so keep the terminal open).
- A central Petrova column (dense astrophage) has been added down the middle of the grid; entering it causes fast health/energy drain.
- Rocky/Grace communication uses a simple fuzzy-influenced rule: when a xenonite tunnel exists between ships communication improves; otherwise it's limited.

If you want the non-GUI batch runner, use `python main.py batch`.
