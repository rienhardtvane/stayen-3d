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

## Status (draft 1)

- The pitch, and the Oost, Noord and West stands, are in their measured positions with real row counts.
- Rakes and roof heights are estimates until they're checked against side-on photos.
- Zuid shows the 2020 design (ae+ architecten) as **provisional**. The approved 2025 design isn't public.
- Not modelled yet: aisles and tunnel openings, the West front strip W, floodlights, real roof shapes
  (the West roof is curved), signage, or the area around the stadium.
