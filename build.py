"""Build Stayen (Sint-Truiden) in Blender, to scale, and render camera views.

Usage, with the Blender Python module (pip install bpy):
    python build.py scene.json renders/ [camera ...] [--final] [--save stayen.blend]
or with Blender itself:
    blender -b --python-exit-code 1 -P build.py -- scene.json renders/ [camera ...]

Rules this file follows:
- 1 Blender unit = 1 metre.
- Every dimension carries its source in a comment. S1 to S6 refer to references/sources.md.
  "EST" marks an estimate that still has to be confirmed against photos.
- Cameras, light and colours come from scene.json, not from this file.

World frame: origin at the centre spot. X runs across the pitch towards Oost (East),
Y runs along the pitch towards Noord (North). Z is up.
"""

import json
import math
import os
import sys

import bpy  # must come first: bmesh and mathutils are provided by bpy
import bmesh
from mathutils import Matrix, Vector

# ---------------------------------------------------------------------------
# Geometry (metres)
# ---------------------------------------------------------------------------

PITCH_LENGTH = 105.0  # S1 measured ~104.6 m; UEFA Cat 4 requires 105 (S6)
PITCH_WIDTH = 68.0    # UEFA Cat 4 requires 68 (S6); S1 lines measured 65.5, open item

SEAT_PITCH = 0.50     # S4 Daplast CR6: 500 mm recommended between seat centres
SEAT_WIDTH = 0.40     # S4 CR6 shell width 400 mm
SEAT_BACK = 0.35      # S4 CR6 backrest 35 cm
SEAT_HEIGHT = 0.45    # S4 Daplast: seat ~45 cm above the tread
EYE_SEATED = 1.15     # eye height of a seated adult above the seat's tread

# Stands. "front" is the distance from the centre line (u or v = 0) to the stand's front
# wall, measured outwards. Local frame per stand: x along the stand, y outwards from the
# front wall, z up. "along" ranges are world coordinates on the axis parallel to the stand.
STANDS = {
    "east": {  # Oost, 2003 (S5)
        "outward": (1, 0),
        "front": 36.0,            # S1 roof edge +33, seats start ~3 m behind it. EST
        "along": (-60.0, 52.0),   # S1 roof extent v -60..+52
        "tiers": [
            {   # one tier, 27 rows (S2, block G)
                "rows": 27,
                "tread": 0.80,     # EST, fits 27 rows inside the 27 m roof depth (S1)
                "riser": 0.38,     # EST
                "y0": 0.5,         # EST front gangway
                "z0": 1.2,         # EST first row above pitch level
                "colour": "east",
            }
        ],
        "back": {"y": (22.1, 24.0), "z": 15.0},           # S1 roof back +60 -> local 24
        "roof": {"y": (-3.0, 24.0), "z": 15.0, "thick": 1.0},  # S1 +33..+60; height EST
        "blocks": [],
    },
    "north": {  # Noord, 2009, hotel built into it (S5)
        "outward": (0, 1),
        "front": 55.5,            # S1 roof edge +52, goal line 52.5. EST
        "along": (-40.0, 36.0),   # S1 north roof inner edge -43..+30; seating EST
        "tiers": [
            {   # 16 rows (S2, block Y1)
                "rows": 16,
                "tread": 0.80,     # EST
                "riser": 0.40,     # EST
                "y0": 0.5,
                "z0": 1.2,
                "colour": "north",
            }
        ],
        "back": {"y": (13.3, 18.0), "z": 14.0},            # S1 roof back +73.5 -> local 18
        "roof": {"y": (-3.5, 18.0), "z": 14.0, "thick": 1.2},  # S1; height EST
        "blocks": [
            # hotel rooms overlooking the pitch (S5), glazed band above the back rows. EST
            {"y": (13.3, 13.6), "z": (8.4, 13.4), "x": None, "mat": "glass"},
        ],
    },
    "west": {  # main stand, 2014 (S5)
        "outward": (-1, 0),
        "front": 41.5,            # S1 roof edge -43; wide technical area in front. EST
        "along": (-62.0, 50.0),   # S1 roof extent v -62..+50
        "tiers": [
            {   # lower tier, 10 rows (S2, block R1)
                "rows": 10,
                "tread": 0.80,     # EST
                "riser": 0.35,     # EST
                "y0": 0.5,
                "z0": 1.5,
                "colour": "west_lower",
            },
            {   # hospitality balcony in front of the skyboxes, about 6 rows (S2)
                "rows": 6,
                "tread": 0.85,     # EST
                "riser": 0.40,     # EST
                "y0": 9.5,
                "z0": 6.6,
                "colour": "west_balcony",
            },
        ],
        "back": {"y": (15.0, 24.5), "z": 18.0},             # S1 roof back -66 -> local 24.5
        "roof": {"y": (1.5, 24.5), "z": 18.0, "thick": 1.5},  # S1 -43..-66; height EST
        "blocks": [
            # skybox and office box glazing, two levels (S2: 21 skyboxes, 19 office boxes)
            {"y": (14.9, 15.1), "z": (9.2, 12.4), "x": None, "mat": "glass"},
            {"y": (14.9, 15.1), "z": (13.2, 16.6), "x": None, "mat": "glass"},
            # rear building with the solar roof, to -87 (S1). Height EST.
            {"y": (24.5, 45.5), "z": (0.0, 12.0), "x": None, "mat": "cladding"},
        ],
    },
}

# South stand: 2020 design, provisional (S3). Wedge along the railway.
SOUTH = {
    "front": 55.0,           # S1 old south stand edge -54
    "length": 82.42,         # S3 grid dimension 8242 cm
    "depth_wide": 24.6,      # S3 roof plan, scaled from the 82.42 m length. EST +-1 m
    "depth_narrow": 3.0,     # S3 roof plan. EST
    "roof": 25.02,           # S3 dakniveau +2502 cm
    "terrace_height": 1.7,   # S3 section, 170 cm
    "terrace_depth": 4.0,    # EST
    "terrace_length": 60.0,  # EST
}

# Pitch surround. S1: artificial turf runs to the stand fronts.
APRON = {"x": (-41.5, 36.0), "y": (-55.0, 55.5)}
AD_BOARD_OFFSET = 3.0   # EST, LED boards ~3 m off the touchlines and goal lines
AD_BOARD_HEIGHT = 0.9   # EST


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(h):
    h = h.lstrip("#")
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)) + (1.0,)


MATS = {}


def make_material(name, hex_colour, roughness=0.7, metallic=0.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = hex_to_linear(hex_colour)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    m.diffuse_color = hex_to_linear(hex_colour)
    MATS[name] = m
    return m


def new_object(name, bm, mat=None, collection=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    if mat:
        ob.data.materials.append(MATS[mat])
    return ob


def add_box(bm, x0, x1, y0, y1, z0, z1):
    res = bmesh.ops.create_cube(bm, size=1.0)
    for v in res["verts"]:
        v.co.x = x0 if v.co.x < 0 else x1
        v.co.y = y0 if v.co.y < 0 else y1
        v.co.z = z0 if v.co.z < 0 else z1


def box_object(name, x0, x1, y0, y1, z0, z1, mat, collection=None):
    bm = bmesh.new()
    add_box(bm, x0, x1, y0, y1, z0, z1)
    return new_object(name, bm, mat, collection)


def stand_matrix(stand):
    ox, oy = stand["outward"]
    rot = math.atan2(oy, ox) - math.pi / 2
    loc = Vector((ox * stand["front"], oy * stand["front"], 0))
    return Matrix.Translation(loc) @ Matrix.Rotation(rot, 4, "Z")


def local_x(stand, along_world):
    """World coordinate along the stand -> the stand's local x."""
    ox, oy = stand["outward"]
    ax, ay = oy, -ox  # local x axis in world (keeps a right-handed frame)
    # along_world is v for east/west stands and u for north/south stands
    p = (0.0, along_world) if ox != 0 else (along_world, 0.0)
    return p[0] * ax + p[1] * ay


def local_x_range(stand):
    a, b = (local_x(stand, v) for v in stand["along"])
    return min(a, b), max(a, b)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def build_pitch(col):
    # Ground and apron
    box_object("ground", -250, 250, -250, 250, -0.2, -0.01, "ground", col)
    box_object("apron", APRON["x"][0], APRON["x"][1], APRON["y"][0], APRON["y"][1],
               -0.01, 0.0, "turf_dark", col)
    # Mowing stripes, 12 across the length (cosmetic)
    n = 12
    L, W = PITCH_LENGTH, PITCH_WIDTH
    for i in range(n):
        y0 = -L / 2 + i * L / n
        box_object(f"stripe_{i:02d}", -W / 2, W / 2, y0, y0 + L / n, 0.0, 0.005,
                   "turf_light" if i % 2 else "turf_dark", col)

    # Lines, 12 cm wide (Laws of the Game max 12 cm)
    lw = 0.12
    z0, z1 = 0.005, 0.012
    bm = bmesh.new()

    def line(xa, ya, xb, yb):
        if abs(xa - xb) < 1e-6:
            add_box(bm, xa - lw / 2, xa + lw / 2, min(ya, yb), max(ya, yb), z0, z1)
        else:
            add_box(bm, min(xa, xb), max(xa, xb), ya - lw / 2, ya + lw / 2, z0, z1)

    hl, hw = L / 2, W / 2
    line(-hw, -hl, -hw, hl); line(hw, -hl, hw, hl)        # touchlines
    line(-hw, -hl, hw, -hl); line(-hw, hl, hw, hl)        # goal lines
    line(-hw, 0, hw, 0)                                    # halfway line
    for s in (-1, 1):
        g = s * hl
        # penalty area 40.32 x 16.5, goal area 18.32 x 5.5 (Laws of the Game)
        line(-20.16, g, -20.16, g - s * 16.5); line(20.16, g, 20.16, g - s * 16.5)
        line(-20.16, g - s * 16.5, 20.16, g - s * 16.5)
        line(-9.16, g, -9.16, g - s * 5.5); line(9.16, g, 9.16, g - s * 5.5)
        line(-9.16, g - s * 5.5, 9.16, g - s * 5.5)
    new_object("lines", bm, "lines", col)

    # Centre circle r 9.15 and penalty arcs (outside the area only)
    def ring(name, cx, cy, r, a0=0.0, a1=2 * math.pi, seg=96):
        bm = bmesh.new()
        prev = None
        for i in range(seg + 1):
            a = a0 + (a1 - a0) * i / seg
            inner = bm.verts.new((cx + (r - lw / 2) * math.cos(a), cy + (r - lw / 2) * math.sin(a), z1))
            outer = bm.verts.new((cx + (r + lw / 2) * math.cos(a), cy + (r + lw / 2) * math.sin(a), z1))
            if prev:
                bm.faces.new((prev[0], prev[1], outer, inner))
            prev = (inner, outer)
        new_object(name, bm, "lines", col)

    ring("centre_circle", 0, 0, 9.15)
    arc = math.acos((16.5 - 11.0) / 9.15)
    ring("arc_south", 0, -hl + 11.0, 9.15, math.pi / 2 - arc, math.pi / 2 + arc, 32)
    ring("arc_north", 0, hl - 11.0, 9.15, -math.pi / 2 - arc, -math.pi / 2 + arc, 32)

    # Goals: 7.32 x 2.44, posts 12 cm (Laws of the Game)
    for s in (-1, 1):
        g = s * hl
        bm = bmesh.new()
        p = 0.12
        add_box(bm, -3.66 - p, -3.66, g - p / 2, g + p / 2, 0, 2.44)
        add_box(bm, 3.66, 3.66 + p, g - p / 2, g + p / 2, 0, 2.44)
        add_box(bm, -3.66 - p, 3.66 + p, g - p / 2, g + p / 2, 2.44, 2.44 + p)
        new_object(f"goal_{'n' if s > 0 else 's'}", bm, "lines", col)

    # LED perimeter boards
    o = AD_BOARD_OFFSET
    h = AD_BOARD_HEIGHT
    bm = bmesh.new()
    add_box(bm, -hw - o - 0.2, -hw - o, -hl + 2, hl - 2, 0, h)
    add_box(bm, hw + o, hw + o + 0.2, -hl + 2, hl - 2, 0, h)
    add_box(bm, -hw + 2, -6, hl + o, hl + o + 0.2, 0, h)
    add_box(bm, 6, hw - 2, hl + o, hl + o + 0.2, 0, h)
    add_box(bm, -hw + 2, -6, -hl - o - 0.2, -hl - o, 0, h)
    add_box(bm, 6, hw - 2, -hl - o - 0.2, -hl - o, 0, h)
    new_object("led_boards", bm, "ad_board", col)


def make_seat_mesh():
    """One CR6-sized seat (S4): a 400 mm shell with a 350 mm backrest, sitting 450 mm above the tread."""
    bm = bmesh.new()
    w = SEAT_WIDTH
    add_box(bm, -w / 2, w / 2, -0.20, 0.16, SEAT_HEIGHT - 0.05, SEAT_HEIGHT)          # pan
    add_box(bm, -w / 2, w / 2, 0.14, 0.19, SEAT_HEIGHT, SEAT_HEIGHT + SEAT_BACK)        # backrest
    add_box(bm, -0.03, 0.03, -0.05, 0.05, 0.0, SEAT_HEIGHT - 0.05)                      # pedestal
    me = bpy.data.meshes.new("seat_cr6")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(None)  # one slot; each seat block sets its own colour
    return me


def build_tier(name, tier, x0, x1, col, seat_mesh, seat_mat, mw):
    t, r, rows = tier["tread"], tier["riser"], tier["rows"]
    y0, z0 = tier["y0"], tier["z0"]

    # Stepped concrete profile in (y, z), extruded along x
    prof = [(y0, 0.0), (y0, z0)]
    for i in range(rows):
        z = z0 + i * r
        prof.append((y0 + (i + 1) * t, z))
        if i < rows - 1:
            prof.append((y0 + (i + 1) * t, z + r))
    y_end = y0 + rows * t
    prof.append((y_end, 0.0))

    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in prof]
    b = [bm.verts.new((x1, y, z)) for y, z in prof]
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    ob = new_object(f"{name}_concrete", bm, "concrete", col)
    ob.matrix_world = mw

    # Seats: one seat mesh, arrayed along the row and up the rows (instanced, not copied)
    margin = 0.6
    count = int((x1 - x0 - 2 * margin) / SEAT_PITCH) + 1
    seats = bpy.data.objects.new(f"{name}_seats", seat_mesh)
    col.objects.link(seats)
    seats.matrix_world = mw @ Matrix.Translation((x0 + margin, y0 + 0.55 * t, z0))
    m1 = seats.modifiers.new("along_row", "ARRAY")
    m1.use_relative_offset = False
    m1.use_constant_offset = True
    m1.constant_offset_displace = (SEAT_PITCH, 0, 0)
    m1.count = count
    m2 = seats.modifiers.new("up_rows", "ARRAY")
    m2.use_relative_offset = False
    m2.use_constant_offset = True
    m2.constant_offset_displace = (0, t, r)
    m2.count = rows
    # material per object (the slot links to the object, so the seat mesh stays shared)
    seats.material_slots[0].link = "OBJECT"
    seats.material_slots[0].material = seat_mat
    return count * rows


def build_stand(key, stand, col, seat_mesh, seat_colours):
    mw = stand_matrix(stand)
    x0, x1 = local_x_range(stand)
    seats_total = 0
    for i, tier in enumerate(stand["tiers"]):
        seat_mat = MATS[seat_colours[tier["colour"]]]
        seats_total += build_tier(f"{key}_t{i}", tier, x0, x1, col, seat_mesh, seat_mat, mw)

    # Front wall (pitch side), 0.3 m thick, up to the first row
    t0 = stand["tiers"][0]
    ob = box_object(f"{key}_front_wall", x0, x1, t0["y0"] - 0.3, t0["y0"], 0, t0["z0"] + 0.6,
                    "concrete_dark", col)
    ob.matrix_world = mw

    # Back structure and cladding
    by0, by1 = stand["back"]["y"]
    ob = box_object(f"{key}_back", x0, x1, by0, by1, 0, stand["back"]["z"], "cladding", col)
    ob.matrix_world = mw
    # side walls closing each end
    for xa, xb in ((x0 - 0.3, x0), (x1, x1 + 0.3)):
        ob = box_object(f"{key}_end", xa, xb, t0["y0"] - 0.3, by1, 0, stand["roof"]["z"],
                        "cladding", col)
        ob.matrix_world = mw

    # Roof slab with a front fascia
    ry0, ry1 = stand["roof"]["y"]
    rz, th = stand["roof"]["z"], stand["roof"]["thick"]
    ob = box_object(f"{key}_roof", x0 - 0.3, x1 + 0.3, ry0, ry1, rz, rz + th, "roof_top", col)
    ob.matrix_world = mw
    ob = box_object(f"{key}_fascia", x0 - 0.3, x1 + 0.3, ry0, ry0 + 0.4, rz - 0.8, rz + th + 0.2,
                    "steel", col)
    ob.matrix_world = mw

    for i, b in enumerate(stand["blocks"]):
        bx0, bx1 = b["x"] if b["x"] else (x0, x1)
        ob = box_object(f"{key}_block{i}", bx0, bx1, b["y"][0], b["y"][1], b["z"][0], b["z"][1],
                        b["mat"], col)
        ob.matrix_world = mw
    return seats_total


def build_corners(col):
    # NE corner: the north building runs on over the east stand's north end (S1 roof +36..+58)
    box_object("ne_corner", 36.0, 58.0, 52.0, 73.5, 0, 14.0, "cladding", col)
    box_object("ne_corner_roof", 36.0, 58.0, 52.0, 73.5, 14.0, 15.2, "roof_top", col)
    # NW corner: west stand back building meets the north stand (S1)
    box_object("nw_corner", -66.0, -40.3, 55.2, 73.5, 0, 14.0, "cladding", col)


def build_south_provisional(col):
    """2020 design (S3), marked provisional. Wedge plan, wide end to the west."""
    s = SOUTH
    front = -s["front"]
    half = s["length"] / 2
    # Wedge footprint in world XY: pitch-side edge straight, rear edge follows the railway
    yb = front - s["terrace_depth"]
    pts = [(-half, yb), (half, yb), (half, yb - s["depth_narrow"]), (-half, yb - s["depth_wide"])]
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, 0.0)) for x, y in pts]
    top = [bm.verts.new((x, y, s["roof"])) for x, y in pts]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    new_object("south_PROVISIONAL_2020", bm, "provisional", col)
    # Low pitch-side terrace, 1.7 m high (S3), stepped in 5 risers
    tl = s["terrace_length"] / 2
    steps = 5
    for i in range(steps):
        z = s["terrace_height"] * (i + 1) / steps
        y_a = front - i * s["terrace_depth"] / steps
        box_object(f"south_terrace_{i}", -tl, tl, y_a - s["terrace_depth"] / steps, y_a, 0, z,
                   "provisional", col)


# ---------------------------------------------------------------------------
# Scene, light, cameras
# ---------------------------------------------------------------------------

def setup_world(cfg):
    w = bpy.data.worlds.new("sky")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes.get("Background")
    tex = nt.nodes.new("ShaderNodeTexGradient")
    tex.gradient_type = "EASING"
    mapping = nt.nodes.new("ShaderNodeMapping")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    # gradient along Z of the view direction
    mapping.inputs["Rotation"].default_value = (0, math.radians(-90), 0)
    nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].color = hex_to_linear(cfg["colours"]["sky_horizon"])
    ramp.color_ramp.elements[1].color = hex_to_linear(cfg["colours"]["sky_top"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0

    sun_cfg = cfg["sun"]
    # Pitch long axis points ~10 deg west of true north (S1), so true bearings rotate by +10
    az = math.radians(sun_cfg["azimuth_true_deg"] + 10.0)
    el = math.radians(sun_cfg["elevation_deg"])
    to_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    ld = bpy.data.lights.new("sun", "SUN")
    ld.energy = sun_cfg["strength"]
    ld.angle = math.radians(0.53)
    sun = bpy.data.objects.new("sun", ld)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()


def seat_eye(cam):
    stand = STANDS[cam["stand"]]
    tier = stand["tiers"][cam["tier"]]
    i = cam["row"] - 1
    y = tier["y0"] + i * tier["tread"] + 0.55 * tier["tread"]
    z = tier["z0"] + i * tier["riser"] + EYE_SEATED
    x = local_x(stand, cam["along"])
    return stand_matrix(stand) @ Vector((x, y, z))


def add_camera(name, cam):
    if cam["type"] == "seat":
        pos = seat_eye(cam)
    else:
        pos = Vector(cam["position"])
    cd = bpy.data.cameras.new(name)
    cd.lens = cam.get("lens_mm", 24)
    cd.sensor_width = 36
    cd.clip_end = 2000
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = pos
    d = Vector(cam["target"]) - pos
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def check_scene():
    """Report anything floating above or sinking below the ground."""
    problems = []
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH" or ob.name in ("ground",):
            continue
        zs = [(ob.matrix_world @ Vector(c)).z for c in ob.bound_box]
        lo = min(zs)
        if lo < -0.05:
            problems.append(f"{ob.name}: lowest point {lo:.2f} m below ground")
    return problems


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    final = "--final" in argv
    save = None
    if "--save" in argv:
        save = argv[argv.index("--save") + 1]
    args = [a for a in argv if not a.startswith("--") and a != save]
    scene_path, out_dir = args[0], args[1]
    only = args[2:]

    with open(scene_path) as f:
        cfg = json.load(f)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0

    for k, v in cfg["colours"].items():
        if k.startswith("sky"):
            continue
        rough = 0.25 if k in ("glass", "steel") else 0.75
        make_material(k, v, roughness=rough, metallic=0.6 if k == "steel" else 0.0)

    seat_colours = cfg["stand_seat_colours"]

    col = bpy.data.collections.new("stadium")
    sc.collection.children.link(col)
    build_pitch(col)
    seat_mesh = make_seat_mesh()
    seats = 0
    for key, stand in STANDS.items():
        seats += build_stand(key, stand, col, seat_mesh, seat_colours)
    build_corners(col)
    build_south_provisional(col)
    setup_world(cfg)
    print(f"[build] seats modelled (no aisles yet): {seats}")

    probs = check_scene()
    for p in probs:
        print("[check]", p)

    r = cfg["render"]
    sc.render.engine = r["engine"]
    res = r["final_resolution"] if final else r["draft_resolution"]
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "Standard"
    if sc.render.engine == "CYCLES":
        sc.cycles.samples = r["final_samples"] if final else r["draft_samples"]
        sc.cycles.use_denoising = True
        sc.cycles.device = "CPU"
        sc.cycles.max_bounces = 4
    sc.render.image_settings.file_format = "PNG"

    os.makedirs(out_dir, exist_ok=True)
    for name, cam in cfg["cameras"].items():
        if name.startswith("_") or (only and name not in only):
            continue
        ob = add_camera(name, cam)
        sc.camera = ob
        sc.render.filepath = os.path.join(out_dir, f"{name}.png")
        print(f"[render] {name} at {tuple(round(c, 2) for c in ob.location)}")
        bpy.ops.render.render(write_still=True)

    if save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(save))


if __name__ == "__main__":
    main()
