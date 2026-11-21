# Stayen 3D

A to-scale 3D model of Stayen, home of STVV in Sint-Truiden, built in Blender from Python.
It's for seat-view renders (ticketing and hospitality sales) and, later, sponsor visuals
(LED boards and stand fascias).

## Run it

```
pip install bpy            # Blender as a Python module
python build.py scene.json renders/                        # every camera, draft quality
python build.py scene.json renders/ oost_G_row14           # one camera
python build.py scene.json renders/ --final --save stayen.blend
```

With Blender installed instead:

```
blender -b --python-exit-code 1 -P build.py -- scene.json renders/
```

## Files

| File | What it holds |
|---|---|
| `build.py` | All geometry. Every dimension has its source in a comment (S1 to S6), and estimates are marked EST. |
| `scene.json` | Cameras, sun and colours. A new seat view is one entry. |
| `references/sources.md` | Every source, every measurement, and the open items. |
| `renders/` | The latest draft renders. |

## Adding a seat view

Add an entry to `cameras` in `scene.json`:

```json
"oost_C_row20": { "type": "seat", "stand": "east", "tier": 0, "row": 20, "along": 25, "target": [0, 0, 0], "lens_mm": 24 }
```

`along` is the position along the pitch in metres from the halfway line. It's positive towards
Noord for the side stands, and positive towards Oost for the end stands.

## Advertising slots

Every sponsor position is a named slot. These are the LED runs, the printed boards on the stand front
walls, and the Oost back fascia (`adslots/inventory.csv`). To show a partner's artwork, save it as
`adslots/<SLOT>.png`, or map it in `scene.json`:

```json
"ads": { "assign": { "ST-E-10": "partners/acme_6x1.png", "LED-E": "partners/acme_led_10m.png" } }
```

LED images tile every 10 m. Printed boards stretch to their slot size (most are about 6.1 x 0.9 m). After
changing the inventory, run `python tools/make_slots.py adslots/inventory.csv adslots/` to redraw
the placeholders.

## Seat picker (web)

`web/` is the browser prototype. You pick a stand, block, row and seat, or tap the plan, and the
camera moves to that seat's eye height. Drag to look around, or switch to the aerial view.

```
python build.py scene.json renders/ --export-web web/   # writes stadium.gltf.json and seats.json
```

- `seats.json` lists every modelled seat (10,441) with its ticketing block, row, seat number and
  position. Seat 1 is on the left as seen from the seat.
- The model is glTF with its binary buffer embedded, saved as `.json` so any static host serves it.
- The page uses three.js from jsdelivr.

## Status (draft 3)

- **Zuid.** It shows the current state by default: an empty site, a black screen, and the crane. Set
  `"south_mode": "provisional"` for the 2020 design.
- **Oost.** It has 11 blocks (A to K) with stairs, 4 tunnel mouths, block letters, and an
  approximation of the real seat pattern.
- **Advertising.** There are 65 advertising slots with placeholder artwork. The pitch-side camera
  `pitchside_oost_boards` is the sponsor view.
- **Heights.** These come from Rienhardt's photos, by solving each photo's camera from the pitch
  markings (`tools/solve_camera.py`).
- **Not modelled yet.** West and Noord aisles and tunnels, the West front strip W, and the exact seat
  pattern.
