# ESP32-S3 Uno: a board designed through KiCad's MCP server

An Arduino Uno-format board for the ESP32-S3-WROOM-1. Claude Code built it on the tablet,
start to finish, through KiCad Android's built-in MCP server. Every design change went through
MCP (`kicad_api` and the `pcb_*` tools); adb was used only for screen recording and screenshots.

- **Shield headers** J1-J4, mounting holes and outline sit where an Uno has them (from KiCad's Arduino Uno template).
- **Pin map:**
  - A0-A3 are IO1-IO4.
  - SDA/SCL are IO8/IO9, on both J3 and J2.
  - D2-D13 are IO17, IO16, IO15, IO7, IO6, IO5, IO21, IO14, IO10, IO11, IO13 and IO12.
  - TX/RX go to the module's UART0.
- **J5** (2x8) carries the rest: IO0, IO18, IO35-IO42 and IO45-IO48, plus 3V3 and GND.
- **Power:**
  - USB-B like an Uno, through a 500 mA polyfuse and a Schottky diode to 5 V. USB D+/D- go to the S3's native USB.
  - The 7-12 V barrel jack goes through a reverse-protection diode and an AMS1117-5.0 regulator.
  - An AMS1117-3.3 makes 3V3.
- **Controls and LEDs:** RESET (EN) and BOOT (IO0) buttons with pull-ups, the EN RC delay, an ON LED, and an L LED on D13.
- **Antenna:** the module's antenna overhangs the right-hand edge, so its keepout lies off the board. A custom rule tells DRC to ignore the courtyard keepout.

## Net classes

Track widths assume 1 oz copper on a 2-layer 1.6 mm board (IPC-2221 outer layers, 10 °C rise).

| Class | Nets | Track | Clearance | Via |
|---|---|---|---|---|
| Power_In | VBUS, VBUS_F, VIN_RAW, VIN (USB 5 V and the 7-12 V jack, up to 1 A) | 0.80 mm | 0.30 mm | 0.8/0.4 mm |
| Power | +5V, +3V3 (the ESP32-S3 peaks at about 0.5 A) | 0.60 mm | 0.25 mm | 0.8/0.4 mm |
| GND | GND (mostly carried by the pours on both layers) | 0.50 mm | 0.20 mm | 0.8/0.4 mm |
| USB | USB_D+, USB_D- (full-speed pair, 0.2 mm gap) | 0.30 mm | 0.20 mm | 0.6/0.3 mm |
| Analog | A0-A3 (extra clearance against coupling) | 0.25 mm | 0.30 mm | 0.6/0.3 mm |
| Digital | D2-D13 | 0.25 mm | 0.20 mm | 0.6/0.3 mm |
| I2C | SDA, SCL | 0.25 mm | 0.20 mm | 0.6/0.3 mm |
| UART | TX, RX | 0.25 mm | 0.20 mm | 0.6/0.3 mm |
| GPIO | IO18, IO35-IO48 | 0.25 mm | 0.20 mm | 0.6/0.3 mm |
| Control | EN, IO0, LED nets | 0.25 mm | 0.20 mm | 0.6/0.3 mm |

**Board minimums:** 0.15 mm track and 0.2 mm drill. The router necks tracks down to 0.19 mm where they leave the module's 1.27 mm-pitch pads, and the module footprint has 0.2 mm thermal vias.

**Result:**
- 107 of 107 connections routed (57 vias), with GND pours on both layers.
- DRC finds no errors.
- The warnings are all expected:
  - silkscreen clipped by the deliberately overhanging jack, USB-B and antenna, and by the template's J4;
  - footprints that differ from the library copies (the template's sockets, and U1's moved reference).

## How it was built (in order)

Each step is a script that talks to the tablet's MCP server through `mcp_client.py`. Over USB, forward the port first with `adb forward tcp:27880 tcp:27880`.

1. `build_schematic.py`: places every symbol and joins each pin to its net by a label or a power symbol (`PlaceSymbolFromLibrary`, `CreateItems`, `UpdateItems`). The netlist is then exported (`RunSchematicJobExportNetlist`) and imported into the template board (`ImportNetlist`).
2. `set_netclasses.py`: net classes and their pattern assignments (`SetNetClasses`, `SetNetClassAssignments`).
3. `design_rules.py`: minimum sizes, plus the track and via size lists (`SetBoardDesignRules`).
4. `place_pcb.py`: placement (`pcb_move_footprint`), moved reference texts, and the module courtyard rule (`SetCustomDesignRules`).
5. `route.py`: the integrated autorouter (`pcb_autoroute`). It removes copper pours first, because the router routes much worse around a filled GND pour (23 connections unrouted instead of 0).
6. `zones.py`: GND pours on F.Cu and B.Cu (`CreateItems` Zone, `RefillZones`). Then `pcb_run_drc`.
7. `models_3d.py`: points `KICAD10_3DMODEL_DIR` at `${KIPRJMOD}/3dmodels` with a project text variable (`SetTextVariables`). KiCad Android does not bundle the 3D library.
8. `export.py`: Gerbers, drill and 3D renders (`RunBoardJobExport*`). The outputs are in `project/fab` and `project/render-*.png`.

`mcp-log.jsonl.gz` records every MCP request and reply of the session (465 tool calls).

### 3D models

`project/3dmodels` is not in the repository. To render the board with parts:
- Download these files from [kicad-packages3D](https://gitlab.com/kicad/libraries/kicad-packages3D) (tag 10.0.8) into `project/3dmodels/<Library>.3dshapes/`:
  - SW_SPST_PTS645Sx43SMTR92, C_0805_2012Metric, BarrelJack_Horizontal
  - PinHeader_2x08_P2.54mm_Vertical, D_SMA, Fuse_1206_3216Metric, LED_0805_2012Metric
  - SOT-223, R_0805_2012Metric, ESP32-S3-WROOM-1
  - PinSocket_1x06/1x08/1x10_P2.54mm_Vertical
- The library has no model for the OST USB-B connector.
- The template's sockets still point at KiCad 9 `.wrl` files, so they render without bodies.

## Known blemishes

- In the schematic, C5 sits on the title block border.
