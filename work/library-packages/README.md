# Library packages (P9)

`test_import.py` checks **Import Library Package** end to end over KiCad's MCP server:
1. It imports the SnapEDA ESP32-S31-WROOM-1-N16R16V zip from the tablet's Downloads folder, for all projects or (with `project`) for the open project.
2. It checks that the libraries load.
3. It places the symbol (and reads its Footprint field) and the footprint.
4. It renders the board in 3D with the part's STEP model (`s31-render.png`), then deletes the trial parts.

Run it with the ESP32-S3 Uno project open on the tablet and `adb forward tcp:27880 tcp:27880`.
SnapEDA's files themselves are not in the repository.
