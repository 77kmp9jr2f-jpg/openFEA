# Slicer material-usage evidence

These compressed files preserve the exact synthetic input surfaces, effective
OrcaSlicer settings and G-code used by `../slicer-usage-comparison.json`.
The JSON records compressed and uncompressed SHA-256 hashes for every file.
Gzip timestamps are zero for stable packaging.

The G-code is **measurement only**. Heating, homing, purge and machine macros
were removed to isolate model deposition. Do not send it to a printer.
OrcaSlicer 2.4.2 generated it using the installed Bambu X1 Carbon 0.4 mm and
Generic PLA profiles, with the explicit overrides recorded in the evidence.
Effective profiles retain slicer defaults beyond those overrides.

Regenerate with `python -m scripts.compare_slicer_usage` from the repository
root. The command creates isolated temporary configuration and model storage;
it does not change the user's slicer settings or send jobs to hardware.

These are nominal material-usage comparisons, not physical mass measurements,
stiffness calibration, or an accuracy guarantee for other inputs/settings.
