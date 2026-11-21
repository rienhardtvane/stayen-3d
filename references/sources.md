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

## Estimates still to confirm with photos

| Item | Value used | How it was derived |
|---|---|---|
| Row depth (tread) | 0.80 m | Typical for this era. Fits 27 Oost rows into the 27 m East roof depth. |
| Oost riser | 0.38 m per row | Estimate |
| Noord riser | 0.40 m per row | Estimate |
| West lower riser | 0.35 m per row | Estimate |
| Roof heights | see build.py | Estimated from row counts plus clearance |
| West front strip W | not modelled yet | Ticketing shows it in front of V1 to T1 |

**Next:** side-on photos of each stand, to measure the rake against seat size (400 mm wide shells).
