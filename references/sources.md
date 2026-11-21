# Sources and measurements

Every size in `build.py` comes from one of the sources below. Where a number is an
estimate, it says so and names what would confirm it.

Coordinate frame used everywhere: origin at the centre spot, metres.
`u` (world X) runs across the pitch towards the East stand (Oost).
`v` (world Y) runs along the pitch towards the North stand (Noord).
The pitch's long axis points about 10 degrees west of true north.

## S1. Aerial orthophoto (Mapy.com, Seznam, captured Nov 2026)

https://mapy.com/en/letecka?x=5.1660633&y=50.8134439&z=19

The imagery predates the June 2026 demolition of the old south stand.

Scale checks:
- Scale bar at zoom 19: 36 m = 191 px, so 0.1885 m/px.
- The penalty area measures 40.2 m wide on the image, against 40.32 m by the Laws of
  the Game. Scale confirmed.
- The centre spot to the goal-line midpoint measures 52.3 m, so the pitch length is about 105 m.
- The painted width measured 65.5 m on the image. UEFA Category 4 requires 105 x 68 m,
  and Stayen received Category 4 in July 2026 (S6), so the model uses 105 x 68.
  **Open:** confirm the current line markings.

Roof edges measured at zoom 18 (0.377 m/px). Accuracy is about 2 m, because the roofs lean
outwards in a non-true orthophoto.

| Edge | u | v |
|---|---|---|
| East roof, pitch side | +33 | -60 to +52 |
| East roof, back | +60 | |
| North roof, pitch side | | +52 |
| North roof, back | | +73 |
| West roof, pitch side | -43 | -62 to +50 |
| West roof, back | -66 | |
| West building, back (solar roof) | -87 | |
| Old south stand, pitch side | | -54 |

## S2. Ticketing seat map (stvv.roboticket.com, event 4758, 21 Nov 2026)

There are 86 sectors. The overview map is schematic, but the seat views are row-accurate.
- **Oost** (East): blocks A to K, one tier. Block G has 27 rows, with entrance tunnels
  through rows 8 to 15. A is at the north end.
- **Noord** (North): blocks X1 to Z3. Block Y1 has 16 rows.
- **West** (main stand): a lower tier V1 to O1 (block R1 has 10 rows), an upper hospitality
  balcony V2 to O2 (about 6 rows), and a front strip W. On the level above are 21 skyboxes,
  19 office boxes, the Skylounge, the Officelounge and the terraces.
- **Zuid** (South): M and N1 to N4. Not on sale. The stand is being rebuilt.
- Away fans sit in Oost J and K this season (S6).

## S3. South stand drawings, ae+ architecten, dossier 19.034, 16 March 2020, marked VOORLOPIG

Archaeology note annex: https://loket.onroerenderfgoed.be/archeologie/notas/notas/14549/bijlagen/61130
- The plan is a wedge 82.42 m long (82.42 m grid dimension), on 7.80 m structural bays.
- Levels: 0.00 = 57.30 TAW. Each floor is 4.32 m. Level 5 is at +20.70. The roof is at +25.02.
- The pitch-side terrace is about 1.7 m high, with 690 standing places (346 seated for UEFA) and 145 seats.
- **Open:** the 2025 approved design is not public. Capacity is unchanged (145 seats), and the offices were
  turned into hotel rooms. The scale may be smaller. The model shows the 2020 design as provisional.

## S4. Seats

- Daplast (https://daplast.com/en/project/stayen-stadion/): 2,300 A3 seats (2014),
  973 Energy and 63 Space VIP seats, and more than 5,200 CR6 seats (2018).
- CR6 shell: 400 mm wide, 435 mm tall, 35 cm backrest. 500 mm between seat centres is recommended
  (minimum 450 mm). From the CR6 data sheet.
- SKOR (July 2026): 1,800 new bucket seats with higher backrests, yellow and blue. New dugouts with
  27 seats each, plus a 5-seat fourth-official box.

## S5. Stand history (stadiumguide.com)

- 2003: Oost, all-seater, opposite the main stand.
- 2009: Noord, behind the goal. The hotel is built into the north side, and 20 of its rooms overlook the pitch.
- 2014: West, the new main stand.

## S6. STVV, "Stayen Europaproof" (6 July 2026)

https://stvv.com/nl/nieuws/artikel/stayen-europaproof-v2
- In Noord, all 1,700 seats were replaced with higher-backrest seats. There are new West dugouts.
- Away fans are in Oost J and K, with a new staircase. Zuid is unavailable.
- UEFA Stadium Category 4.

## S7. Rienhardt's own photos (references/photos/, 12 images, 2025-2026 matchdays)

Camera poses were solved from pitch markings with `tools/solve_camera.py`. The image points are in
`references/photo_points.json`. Heights were then measured by intersecting the photo rays with
planes at known distances.

| Photo | Fit | Camera solved at | Check |
|---|---|---|---|
| IMG_6935 (West balcony, night) | 5.4 px, f pinned at 2050 px with the centre circle | u -52.8, v -8.4, z 13.4 | goal post tops 2.6 m (true 2.44) |
| IMG_6223 (Oost front rows, looking at West) | 2.6 px, f 1998 px | u 44.0, v 1.5, z 3.9 | camera lands in Oost row ~5, which moved Oost's front to u 40 |

Measured with them (model values in build.py, marked PH):
- **Oost:** roof front edge 19.7 to 19.9 m at u 33. DMM fascia top 16.5 m. The front row starts at about u 40.5.
- **NE brick tower:** top 23.5 m. Its face to the pitch runs from u ~27 to ~48.
- **Noord:** the building top is 26.3 m, hotel windows ~24.6 m, the canopy's lower edge ~20.3 m,
  big windows ~16.2 m, and the underside over the back rows ~13.7 m. These assume the facade sits at v 69. EST
- **West:** roof eave 21.5 m, floodlight row 19.9 m, office box level top 20.7 m, skybox glass 14.5 to 16.7 m,
  balcony front rail 11.5 m, banner walkway 10.9 m, lower tier front wall about 4 m.

Read from the photos rather than measured: every stand is a yellow and blue seat mix. Oost has glass end
screens and floodlights on the roof front. West has a brick tower at its north end and a steel and glass
south end. There's a glazed block at the NW corner, floodlight masts at both south corners, and a video
screen at the south end of Oost.

The sunny photos showing the old Zuid stand (IMG_6263, IMG_6231) are from before the June 2026 demolition.

## S8. STVV Instagram (stvv_official, Aug to Nov 2026), screenshots kept outside this repo

These are the club's photos, so they're used as references only and not stored here.
- **IMG_0835 (Conference League, 15 Oct):** the south end since the demolition. There is an empty
  site behind a black screen on poles, a tower crane at the south-east corner, and terraced houses
  beyond. Modelled as `south_mode: current`.
- **IMG_0834:** Oost has four tunnel mouths, stairs at the block boundaries, and a designed blue seat
  pattern (large shapes low and mid, sparse at the top). The pattern is approximated, because the
  design can't be read at screenshot resolution.
- **IMG_0840:** block letters sit on the beam above Oost's top row.
- **IMG_0841:** printed boards (about 1 m high) run along the top of Oost's front wall, with the
  perimeter LED about 2 to 3 m in front of them.
- **IMG_0836:** block labels on the West balcony (R3) and the seat colours close up.
- **IMG_0838, IMG_0833:** confirm the Noord glazing and hotel windows already modelled.
- **IMG_0832** is labelled AI content by the club. It is not used for geometry.

## Advertising inventory

`build.py` writes `adslots/inventory.csv` with 65 slots:
- 6 LED runs, with one tiled image per side: LED-W, LED-E, LED-N and LED-S.
- Printed 6 m boards on the Oost, West and Noord front walls (ST-E, ST-W, ST-N).
- 12 bays on the Oost back fascia (FA-E).

Board sizes and positions are EST from S8 photos. `tools/make_slots.py` draws placeholders that show
each slot's id and size.

## Estimates still to confirm

| Item | Value used | Status |
|---|---|---|
| Row depth (tread) | Oost 0.75 m, Noord 0.80 m, West 0.80 and 0.90 m | EST. Count rows on a side-on photo |
| Risers | Oost 0.50, Noord 0.50, West 0.46 and 0.48 m | Back-solved from the measured heights above |
| Noord facade line | v 69 | EST. A solve of IMG_6228 would fix it |
| Pitch line width | 68 m (aerial says 65.5) | Open |
| Oost aisles and tunnels | ticketing block boundaries; tunnels in C, E, G, I, rows 8-15 | EST. Positions not yet checked against a photo solve |
| West and Noord aisles and tunnels, West front strip W | not modelled | To do |
| Zuid | current state by default; 2020 design available as `south_mode: provisional` | Waiting on the real building |
