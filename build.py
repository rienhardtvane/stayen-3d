"""Build Stayen (Sint-Truiden) in Blender, to scale, and render camera views.

Usage, with the Blender Python module (pip install bpy):
    python build.py scene.json renders/ [camera ...] [--final] [--save stayen.blend]
or with Blender itself:
    blender -b --python-exit-code 1 -P build.py -- scene.json renders/ [camera ...]

Rules this file follows:
- 1 Blender unit = 1 metre.
- Every dimension carries its source in a comment. S1 to S7 refer to references/sources.md.
  "EST" marks an estimate; "PH" marks a value set by matching renders to S7 photos.
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

# Stands. "front" is the distance from the centre line to the stand's front wall,
# measured outwards. Local frame per stand: x along the stand, y outwards from the front
# wall, z up. "along" ranges are world coordinates on the axis parallel to the stand.
# "blocks" are extra boxes in the local frame: x=None means the full stand length;
# "repeat": (width, gap) splits a block into a row of windows.
STANDS = {
    "east": {  # Oost, 2003 (S5). Single tier under a sloping steel roof (S7)
        "outward": (1, 0),
        "front": 40.0,            # PH: IMG_6223 camera solves to row ~5 at u=44; roof edge +33 (S1)
        "along": (-60.0, 52.0),   # S1 roof extent v -60..+52
        "tiers": [
            {   # one tier, 29 rows (S9)
                "rows": 29,        # S9 Roboticket: 29 rows in Oost
                "tread": 0.72,     # EST, 29 rows from u=40.5 to the S1 back line at ~61
                "riser": 0.464,    # PH: top row kept at the height solved from IMG_6935 (DMM fascia 16.5 m)
                "y0": 0.5,
                "z0": 1.3,         # S7: low front wall behind the LED boards
                "colour": "east",
                "labels": True,    # block letters above the top row (S8 IMG_0840)
            }
        ],
        "back": {"y": (21.4, 22.0), "z": 16.5},
        # PH: roof front edge solved at 19.7-20.0 m at u=33 (IMG_6935); rises to the back (S7)
        "roof": {"y": (-7.0, 22.0), "z": 19.6, "thick": 0.9, "slope": 1.8,
                 "bay": 9.3, "rafter_depth": 1.8, "columns_y": 21.7},  # bays: 12 fascia panels (S8)
        "end_mat": "glass",       # S7: glazed wind screens at both ends of Oost
        "lights": True,           # S7: floodlights along the roof front edge
        "blocks": [
            # strip of windows between the fascia and the roof (S7)
            {"y": (21.7, 22.0), "z": (16.5, 19.6), "x": None, "mat": "glass"},
            # DMM.com fascia along the back of the top row, top at 16.5 m (PH)
            {"y": (21.3, 21.5), "z": (15.3, 16.5), "x": None, "mat": "fascia_white"},
        ],
    },
    "north": {  # Noord, 2009, hotel built into it (S5, S7)
        "outward": (0, 1),
        "front": 55.5,            # S1 roof edge +52, goal line 52.5. EST
        "along": (-42.0, 26.5),   # PH: NW tower to the NE brick tower (IMG_6935); fits 120 seats + 8 stairs (S9)
        "tiers": [
            {   # 16 rows (S2, block Y1)
                "rows": 16,
                "tread": 0.80,     # EST
                "riser": 0.50,     # PH (IMG_6935, IMG_6228)
                "y0": 0.5,
                "z0": 3.0,         # S7: tall front wall the tifos hang from
                "colour": "north",
            }
        ],
        "back": {"y": (13.3, 18.0), "z": 1.0},
        # sloping canopy over the seats, lower edge ~19.5 m at the front, ~22.8 m at the
        # facade (PH, IMG_6935). Reaches v=52 in the aerial (S1)
        "roof": {"y": (-3.5, 11.0), "z": 19.4, "thick": 0.6, "slope": 3.4, "bay": 7.6, "rafter_depth": 1.0},
        "end_mat": "facade",
        "lights": True,
        "blocks": [
            # building behind and over the back rows (S5, S7); underside 13.8 m (PH)
            {"y": (13.3, 18.0), "z": (0.0, 26.5), "x": None, "mat": "facade"},
            {"y": (11.0, 13.3), "z": (13.8, 26.5), "x": None, "mat": "facade"},
            # big windows of the hospitality floor, 15.2-17.6 m (PH)
            {"y": (10.85, 11.0), "z": (15.2, 17.6), "x": None, "mat": "glass"},
            # hotel rooms in the top storey, 23.9-25.4 m (PH)
            {"y": (10.85, 11.0), "z": (23.9, 25.4), "x": None, "mat": "glass",
             "repeat": (1.6, 2.4)},
            {"y": (11.0, 18.0), "z": (26.5, 26.9), "x": None, "mat": "roof_top"},
        ],
    },
    "west": {  # main stand, 2014 (S5). Curved roof, two box levels (S7)
        "outward": (-1, 0),
        "front": 41.5,            # S1 roof edge -43; wide technical area in front. EST
        "along": (-62.0, 50.0),   # S1 roof extent v -62..+50
        "tiers": [
            {   # lower tier, 10 rows (S2, block R1)
                "rows": 10,
                "tread": 0.80,     # EST
                "riser": 0.46,     # PH (IMG_6223): top row ~7.5 m
                "y0": 0.5,
                "z0": 3.4,         # PH: front wall top solved at ~4 m (IMG_6223)
                "colour": "west_lower",
            },
            {   # hospitality balcony in front of the skyboxes, about 6 rows (S2, S7)
                "rows": 6,
                "tread": 0.90,     # EST
                "riser": 0.48,     # PH
                "y0": 9.8,
                "z0": 10.4,        # PH: front rail 11.5 m (IMG_6223); photographer eye 13.5 m (IMG_6935)
                "colour": "west_balcony",
            },
            {   # office box level (lower glazed level). Section from S10 (video stills, terrace
                # seen looking north): frameless glass balustrade at the front, a 1.5 m walkway,
                # two stepped rows of padded seats, a raised standing strip, then the box glass.
                # The skybox floor slab is the terrace's ceiling. Heights PH (IMG_6223), depths EST
                "rows": 2,
                "tread": 0.9,
                "riser": 0.35,
                "y0": 16.7,
                "z0": 13.75,
                "front_y": 15.2,
                "walk_z": 13.4,
                "colour": "west_hosp",
                "hospitality": True,
            },
            {   # skybox level (upper glazed level), the same section one floor up (S10); the
                # Skyterras use a third row where the boxes have their standing strip (S9)
                "rows": 3,
                "tread": 0.9,
                "riser": 0.35,
                "y0": 16.7,
                "z0": 17.85,
                "front_y": 15.2,
                "walk_z": 17.5,
                "colour": "west_hosp",
                "hospitality": True,
            },
        ],
        "back": {"y": (19.7, 24.5), "z": 21.0},
        # PH: eave 21.4 m, floodlight row 19.8 m (IMG_6223). Curved (S7)
        "roof": {"y": (1.0, 24.5), "z": 21.4, "thick": 0.8, "arc": 1.5, "bay": 8.0, "rafter_depth": 0.5},
        "end_mat": "steel_glass",
        "lights": True,
        "blocks": [
            # lounge glazing under the yellow banner walkway (PH 8.6-9.6 m, 9.6-10.4 m)
            {"y": (8.9, 9.8), "z": (0.0, 8.6), "x": None, "mat": "concrete_dark"},
            {"y": (9.0, 9.1), "z": (8.6, 9.6), "x": None, "mat": "glass"},
            {"y": (9.0, 9.8), "z": (9.6, 10.4), "x": None, "mat": "banner_yellow"},
            # office level: structure under the walkway, standing strip, box glass (S10)
            {"y": (15.2, 16.7), "z": (0.0, 13.4), "x": None, "mat": "concrete_dark"},
            {"y": (18.5, 19.7), "z": (0.0, 14.45), "x": None, "mat": "concrete"},
            {"y": (19.65, 19.75), "z": (14.45, 17.0), "x": None, "mat": "glass"},
            # skybox floor slab = office terrace ceiling (S10), then the skybox level
            {"y": (15.2, 19.7), "z": (17.0, 17.5), "x": None, "mat": "concrete"},
            {"y": (18.5, 19.7), "z": (17.5, 18.55), "x": None, "mat": "concrete"},
            {"y": (19.65, 19.75), "z": (18.55, 21.0), "x": None, "mat": "glass"},
            # rear building with the solar roof, to -87 (S1). Height EST
            {"y": (24.5, 45.5), "z": (0.0, 12.0), "x": None, "mat": "cladding"},
            # brick stair and lift tower at the north end (S7)
            {"y": (12.0, 26.0), "z": (0.0, 22.5), "x": (50.0, 53.0), "mat": "brick"},
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

# Real block, row and seat layout from the ticketing system (S9). See the file for the format.
SEATMAP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "references", "roboticket_seatmap.json")))
STAND_NAMES = {("east", 0): "Oost", ("north", 0): "Noord",
               ("west", 0): "West lower", ("west", 1): "West balcony",
               ("west", 2): "Office boxes", ("west", 3): "Skyboxes"}
GAP_W = 1.2          # EST width of a stair inside a block ("gaps_after")

SEATS = []          # filled while building: one dict per seat
_CURRENT = {}       # stand key and tier index of the tier being built


def parse_runs(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out.extend(range(int(a), int(b or a) + 1))
    return out


def parse_rows(rows):
    res = {}
    for k, v in rows.items():
        a, _, b = k.partition("-")
        for r in range(int(a), int(b or a) + 1):
            res[r] = parse_runs(v)
    return res


# Pitch surround. S1: artificial turf runs to the stand fronts.
APRON = {"x": (-41.5, 36.0), "y": (-55.0, 55.5)}
AD_BOARD_OFFSET = 3.0   # EST, LED boards ~3 m off the touchlines and goal lines
AD_BOARD_HEIGHT = 0.9   # EST


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(h):
    h = h.lstrip("#")
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)) + (1.0,)


MATS = {}


def make_material(name, hex_colour, roughness=0.7, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = hex_to_linear(hex_colour)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    m.diffuse_color = hex_to_linear(hex_colour)
    MATS[name] = m
    return m


def make_emissive(name, hex_colour, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = hex_to_linear(hex_colour)
    bsdf.inputs["Emission Color"].default_value = hex_to_linear(hex_colour)
    bsdf.inputs["Emission Strength"].default_value = strength
    MATS[name] = m
    return m


def make_mosaic(name, base_hex, accent_hex, accent_share):
    """Seats in a random yellow/blue mix, one colour per seat (S7 photos)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.5
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    snap = nt.nodes.new("ShaderNodeVectorMath")
    snap.operation = "SNAP"
    snap.inputs[1].default_value = (0.5, 0.5, 0.4)  # roughly one cell per seat
    noise = nt.nodes.new("ShaderNodeTexWhiteNoise")
    noise.noise_dimensions = "3D"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = hex_to_linear(base_hex)
    ramp.color_ramp.elements[1].position = 1.0 - accent_share
    ramp.color_ramp.elements[1].color = hex_to_linear(accent_hex)
    nt.links.new(geo.outputs["Position"], snap.inputs[0])
    nt.links.new(snap.outputs["Vector"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Value"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    m.diffuse_color = hex_to_linear(base_hex)
    MATS[name] = m
    return m


def make_pattern(name, base_hex, accent_hex):
    """Oost seat pattern (S8 IMG_0834): large blue shapes in the lower and middle rows, sparse
    blue near the top. The real design can't be read at screenshot resolution, so this is an
    approximation driven by a large-scale noise field plus per-seat randomness."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.5
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    snap = nt.nodes.new("ShaderNodeVectorMath"); snap.operation = "SNAP"
    snap.inputs[1].default_value = (0.5, 0.5, 0.4)
    L.new(geo.outputs["Position"], snap.inputs[0])
    rand = nt.nodes.new("ShaderNodeTexWhiteNoise"); rand.noise_dimensions = "3D"
    L.new(snap.outputs["Vector"], rand.inputs["Vector"])
    blob = nt.nodes.new("ShaderNodeTexNoise")
    blob.inputs["Scale"].default_value = 0.22
    blob.inputs["Detail"].default_value = 1.0
    L.new(snap.outputs["Vector"], blob.inputs["Vector"])
    stretch = nt.nodes.new("ShaderNodeMapRange")
    stretch.inputs["From Min"].default_value = 0.42
    stretch.inputs["From Max"].default_value = 0.58
    L.new(blob.outputs["Fac"], stretch.inputs["Value"])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Position"], sep.inputs["Vector"])
    height = nt.nodes.new("ShaderNodeMapRange")
    height.inputs["From Min"].default_value = 6.0
    height.inputs["From Max"].default_value = 15.0
    L.new(sep.outputs["Z"], height.inputs["Value"])

    def math(op, a, b=None, val=None):
        n = nt.nodes.new("ShaderNodeMath"); n.operation = op
        L.new(a, n.inputs[0])
        if b is not None:
            L.new(b, n.inputs[1])
        elif val is not None:
            n.inputs[1].default_value = val
        return n.outputs[0]

    v = math("ADD", math("MULTIPLY", stretch.outputs["Result"], val=0.65),
             math("MULTIPLY", rand.outputs["Value"], val=0.35))
    v = math("SUBTRACT", v, math("MULTIPLY", height.outputs["Result"], val=0.45))
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = hex_to_linear(base_hex)
    ramp.color_ramp.elements[1].position = 0.58
    ramp.color_ramp.elements[1].color = hex_to_linear(accent_hex)
    L.new(v, ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    m.diffuse_color = hex_to_linear(base_hex)
    MATS[name] = m
    return m


IMAGE_MATS = {}


def make_image_material(path, strength):
    """Emissive (LED) or matte (printed board) material from an artwork image."""
    key = (path, strength)
    if key in IMAGE_MATS:
        return IMAGE_MATS[key]
    m = bpy.data.materials.new(os.path.basename(path))
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.abspath(path))
    tex.extension = "REPEAT"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.6
    if strength > 0:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = strength
    IMAGE_MATS[key] = m
    return m


# ---------------------------------------------------------------------------
# Mesh helpers
# ---------------------------------------------------------------------------

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


def box_object(name, x0, x1, y0, y1, z0, z1, mat, collection=None, mw=None):
    bm = bmesh.new()
    add_box(bm, x0, x1, y0, y1, z0, z1)
    ob = new_object(name, bm, mat, collection)
    if mw is not None:
        ob.matrix_world = mw
    return ob


def prism_object(name, profile, x0, x1, mat, collection, mw=None):
    """Extrude a closed (y, z) profile along x from x0 to x1."""
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in profile]
    b = [bm.verts.new((x1, y, z)) for y, z in profile]
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    ob = new_object(name, bm, mat, collection)
    if mw is not None:
        ob.matrix_world = mw
    return ob


def quad_object(name, corners, mat, collection, u_repeat=1.0, mw=None):
    """Quad from 4 corners (bottom-left, bottom-right, top-right, top-left) with UVs 0..u_repeat."""
    bm = bmesh.new()
    vs = [bm.verts.new(c) for c in corners]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new("UVMap")
    for loop, (u, v) in zip(f.loops, ((0, 0), (u_repeat, 0), (u_repeat, 1), (0, 1))):
        loop[uv].uv = (u, v)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    ob.data.materials.append(mat)
    if mw is not None:
        ob.matrix_world = mw
    return ob


def stand_matrix(stand):
    ox, oy = stand["outward"]
    rot = math.atan2(oy, ox) - math.pi / 2
    loc = Vector((ox * stand["front"], oy * stand["front"], 0))
    return Matrix.Translation(loc) @ Matrix.Rotation(rot, 4, "Z")


def local_x(stand, along_world):
    """World coordinate along the stand -> the stand's local x."""
    ox, oy = stand["outward"]
    ax, ay = oy, -ox  # local x axis in world (keeps a right-handed frame)
    p = (0.0, along_world) if ox != 0 else (along_world, 0.0)
    return p[0] * ax + p[1] * ay


def local_x_range(stand):
    a, b = (local_x(stand, v) for v in stand["along"])
    return min(a, b), max(a, b)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def build_pitch(col):
    box_object("ground", -250, 250, -250, 250, -0.2, -0.01, "ground", col)
    box_object("apron", APRON["x"][0], APRON["x"][1], APRON["y"][0], APRON["y"][1],
               -0.01, 0.0, "turf_dark", col)
    n = 12  # mowing-style stripes (the artificial turf is laid in strips, S7)
    L, W = PITCH_LENGTH, PITCH_WIDTH
    for i in range(n):
        y0 = -L / 2 + i * L / n
        box_object(f"stripe_{i:02d}", -W / 2, W / 2, y0, y0 + L / n, 0.0, 0.005,
                   "turf_light" if i % 2 else "turf_dark", col)

    lw = 0.12  # Laws of the Game: lines max 12 cm
    z0, z1 = 0.005, 0.012
    bm = bmesh.new()

    def line(xa, ya, xb, yb):
        if abs(xa - xb) < 1e-6:
            add_box(bm, xa - lw / 2, xa + lw / 2, min(ya, yb), max(ya, yb), z0, z1)
        else:
            add_box(bm, min(xa, xb), max(xa, xb), ya - lw / 2, ya + lw / 2, z0, z1)

    hl, hw = L / 2, W / 2
    line(-hw, -hl, -hw, hl); line(hw, -hl, hw, hl)
    line(-hw, -hl, hw, -hl); line(-hw, hl, hw, hl)
    line(-hw, 0, hw, 0)
    for s in (-1, 1):
        g = s * hl
        line(-20.16, g, -20.16, g - s * 16.5); line(20.16, g, 20.16, g - s * 16.5)
        line(-20.16, g - s * 16.5, 20.16, g - s * 16.5)
        line(-9.16, g, -9.16, g - s * 5.5); line(9.16, g, 9.16, g - s * 5.5)
        line(-9.16, g - s * 5.5, 9.16, g - s * 5.5)
    new_object("lines", bm, "lines", col)

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

    for s in (-1, 1):
        g = s * hl
        bm = bmesh.new()
        p = 0.12
        add_box(bm, -3.66 - p, -3.66, g - p / 2, g + p / 2, 0, 2.44)
        add_box(bm, 3.66, 3.66 + p, g - p / 2, g + p / 2, 0, 2.44)
        add_box(bm, -3.66 - p, 3.66 + p, g - p / 2, g + p / 2, 2.44, 2.44 + p)
        new_object(f"goal_{'n' if s > 0 else 's'}", bm, "lines", col)

    # LED perimeter boards (S7: continuous LED along both touchlines and the goal lines)
    o, h = AD_BOARD_OFFSET, AD_BOARD_HEIGHT
    bm = bmesh.new()
    add_box(bm, -hw - o - 0.2, -hw - o, -hl + 2, hl - 2, 0, h)
    add_box(bm, hw + o, hw + o + 0.2, -hl + 2, hl - 2, 0, h)
    add_box(bm, -hw + 2, -6, hl + o, hl + o + 0.2, 0, h)
    add_box(bm, 6, hw - 2, hl + o, hl + o + 0.2, 0, h)
    add_box(bm, -hw + 2, -6, -hl - o - 0.2, -hl - o, 0, h)
    add_box(bm, 6, hw - 2, -hl - o - 0.2, -hl - o, 0, h)
    new_object("led_housing", bm, "steel", col)

    # Dugouts at the halfway line in front of West (S6: 27 seats each; S7 photos)
    for name, v0, v1 in (("dugout_home", 3.0, 12.0), ("dugout_away", -12.0, -3.0)):
        box_object(name, -hw - 3.4, -hw - 1.6, v0, v1, 0, 1.9, "dugout", col)


def make_seat_mesh():
    """One CR6-sized seat (S4): a 400 mm shell with a 350 mm backrest, 450 mm above the tread."""
    bm = bmesh.new()
    w = SEAT_WIDTH
    add_box(bm, -w / 2, w / 2, -0.20, 0.16, SEAT_HEIGHT - 0.05, SEAT_HEIGHT)
    add_box(bm, -w / 2, w / 2, 0.14, 0.19, SEAT_HEIGHT, SEAT_HEIGHT + SEAT_BACK)
    add_box(bm, -0.03, 0.03, -0.05, 0.05, 0.0, SEAT_HEIGHT - 0.05)
    me = bpy.data.meshes.new("seat_cr6")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(None)  # one slot; each seat block sets its own material
    return me


def tier_profile(tier, lift=0.0, base=0.0):
    t, r, rows = tier["tread"], tier["riser"], tier["rows"]
    y0, z0 = tier["y0"], tier["z0"]
    prof = [(y0, base), (y0, z0 + lift)]
    for i in range(rows):
        z = z0 + i * r + lift
        prof.append((y0 + (i + 1) * t, z))
        if i < rows - 1:
            prof.append((y0 + (i + 1) * t, z + r))
    prof.append((y0 + rows * t, base))
    return prof


def seat_run(name, x_first, step, labels, rows, tier, col, seat_mesh, seat_mat, mw, block, key, ti):
    """Consecutive seats in consecutive rows as one instanced array. x_first is the local x of
    the first label; step is +/-SEAT_PITCH towards the next label."""
    t, r = tier["tread"], tier["riser"]
    r0 = rows[0] - 1
    seats = bpy.data.objects.new(name, seat_mesh)
    col.objects.link(seats)
    seats.matrix_world = mw @ Matrix.Translation((x_first, tier["y0"] + (r0 + 0.55) * t, tier["z0"] + r0 * r))
    for mod_name, off, cnt in (("along_row", (step, 0, 0), len(labels)), ("up_rows", (0, t, r), len(rows))):
        m = seats.modifiers.new(mod_name, "ARRAY")
        m.use_relative_offset = False
        m.use_constant_offset = True
        m.constant_offset_displace = off
        m.count = cnt
    seats.material_slots[0].link = "OBJECT"
    seats.material_slots[0].material = seat_mat
    for row in rows:
        for k, lab in enumerate(labels):
            lx = x_first + k * step
            p = mw @ Vector((lx, tier["y0"] + (row - 1 + 0.55) * t, tier["z0"] + (row - 1) * r))
            SEATS.append({"stand": key, "tier": ti, "row": row, "no": lab, "block": block,
                          "pos": (round(p.x, 2), round(p.y, 2), round(p.z, 2))})
    return len(labels) * len(rows)


def layout_blocks(layout, x0, x1, margin=0.6):
    """Place the ticketing blocks along the stand: block width from its seat count, stairs
    between blocks sized to fill the stand (0.9 to 1.8 m), the whole run centred."""
    blocks = []
    for b in layout["blocks"]:
        rows = parse_rows(b["rows"])
        width_labels = max(max(v) for v in rows.values())
        gaps = b.get("gaps_after", [])
        blocks.append({"name": b["name"], "rows": rows, "gaps": gaps,
                       "w": width_labels * SEAT_PITCH + len(gaps) * GAP_W})
    total = sum(b["w"] for b in blocks)
    n = len(blocks)
    aisle = min(1.8, max(0.9, (x1 - x0 - 2 * margin - total) / max(1, n - 1)))
    span = total + aisle * (n - 1)
    if layout["order"] == "+x":
        cur = x0 + (x1 - x0 - span) / 2
        for b in blocks:
            b["x0"], b["x1"] = cur, cur + b["w"]
            cur += b["w"] + aisle
    else:
        cur = x1 - (x1 - x0 - span) / 2
        for b in blocks:
            b["x0"], b["x1"] = cur - b["w"], cur
            cur -= b["w"] + aisle
    return blocks, aisle


def build_units(name, tier, layout, x0, x1, col, seat_mesh, seat_mat, mw, stand, key, ti):
    """Hospitality level: boxes, lounges and terraces side by side, each with its own rows of
    outdoor seats, glass side screens between units and a glass balustrade at the front (S9).
    Units are placed by their ticketing-map extents scaled onto the stand length."""
    t, r, rows_n = tier["tread"], tier["riser"], tier["rows"]
    y0, z0 = tier["y0"], tier["z0"]
    walk = tier.get("walk_z", z0)
    fy = tier.get("front_y", y0)
    prism_object(f"{name}_floor", tier_profile(tier, base=walk), x0, x1, "concrete", col, mw)
    box_object(f"{name}_walkway", x0, x1, fy, y0, walk - 0.3, walk, "concrete", col, mw)
    # frameless glass balustrade (S10), see-through
    box_object(f"{name}_balustrade", x0, x1, fy - 0.03, fy, walk, walk + 1.1, "glass_clear", col, mw)
    box_object(f"{name}_handrail", x0, x1, fy - 0.05, fy + 0.02, walk + 1.1, walk + 1.14, "steel", col, mw)
    # downlights in the ceiling over the terrace (S10), every 3 m
    bm = bmesh.new()
    lx = x0 + 1.5
    while lx < x1:
        add_box(bm, lx - 0.12, lx + 0.12, 17.2, 17.44, walk + 3.42, walk + 3.48)
        lx += 3.0
    new_object(f"{name}_downlights", bm, "lamp", col).matrix_world = mw
    tx0, tx1 = layout["ticket_x_range"]
    # ticket x grows north to south; for the West stand local x = v, so north = high local x
    def lx_of(tx):
        return x1 - (tx - tx0) / (tx1 - tx0) * (x1 - x0)
    count, k = 0, 0
    for u in layout["units"]:
        ua, ub = sorted((lx_of(u["x"][0]), lx_of(u["x"][1])))
        rows = parse_rows(u["rows"])
        groups = []
        for rw in sorted(rows):
            if groups and groups[-1][1] == rows[rw] and groups[-1][0][-1] == rw - 1:
                groups[-1][0].append(rw)
            else:
                groups.append(([rw], rows[rw]))
        width = max(len(v) for v in rows.values()) * SEAT_PITCH
        start_hi = (ua + ub) / 2 + width / 2 - SEAT_PITCH / 2   # first label at the north (high) side
        for rows_g, labels in groups:
            first = min(min(v) for v in rows.values())
            run = [labels[0]]
            for lab in labels[1:] + [None]:
                if lab is not None and lab == run[-1] + 1:
                    run.append(lab)
                    continue
                x_first = start_hi - (run[0] - first) * SEAT_PITCH
                count += seat_run(f"{name}_u{k}", x_first, -SEAT_PITCH, run, rows_g, tier, col,
                                  seat_mesh, seat_mat, mw, u["name"], key, ti)
                k += 1
                run = [lab]
    return count


def build_tier(name, tier, x0, x1, col, seat_mesh, seat_mat, mw, stand):
    key, ti = _CURRENT["stand"], _CURRENT["tier"]
    layout = SEATMAP[f"{key}-{ti}"]
    t, r, rows_n = tier["tread"], tier["riser"], tier["rows"]
    y0, z0 = tier["y0"], tier["z0"]
    if layout.get("kind") == "units":
        return build_units(name, tier, layout, x0, x1, col, seat_mesh, seat_mat, mw, stand, key, ti)
    conc = prism_object(f"{name}_concrete", tier_profile(tier), x0, x1, "concrete", col, mw)
    blocks, aisle = layout_blocks(layout, x0, x1)
    high = layout["seat1"] == "high"

    def seat_x(b, lab):
        off = (lab - 1) * SEAT_PITCH + SEAT_PITCH / 2 + GAP_W * sum(1 for g in b["gaps"] if lab > g)
        return b["x1"] - off if high else b["x0"] + off

    # Stairs: between blocks and inside blocks with a gap (S9), as a yellow stepped strip (S8)
    stairs = []
    ordered = sorted(blocks, key=lambda b: b["x0"])
    for a_, b_ in zip(ordered, ordered[1:]):
        stairs.append(((a_["x1"] + b_["x0"]) / 2, min(aisle, 1.4)))
    for b in blocks:
        for g in b["gaps"]:
            stairs.append(((seat_x(b, g) + seat_x(b, g + 1)) / 2, GAP_W * 0.9))
    for i, (sx, sw) in enumerate(stairs):
        prism_object(f"{name}_stair{i}", tier_profile(tier, lift=0.02), sx - sw / 2, sx + sw / 2,
                     "stair", col, mw)

    # Tunnel mouths: rows missing from a block inside the tier's range (S9)
    if layout.get("tunnels"):
        bm = bmesh.new()
        for b in blocks:
            missing = [rw for rw in range(1, rows_n + 1) if rw not in b["rows"]]
            if not missing:
                continue
            ta, tb = missing[0] - 1, missing[-1]       # 0-indexed start, exclusive end
            tx0, tx1 = b["x0"] + 0.1, b["x1"] - 0.1
            add_box(bm, tx0, tx1, y0 + ta * t, y0 + tb * t, z0 + ta * r, z0 + tb * r + 2.0)
            box_object(f"{name}_tunnel_back_{b['name']}", tx0, tx1, y0 + tb * t - 0.05, y0 + tb * t + 0.05,
                       z0 + ta * r - 0.5, z0 + ta * r + 2.3, "tunnel_dark", col, mw)
            for sx in (tx0, tx1):
                box_object(f"{name}_tunnel_rail", sx - 0.03, sx + 0.03, y0 + ta * t, y0 + tb * t,
                           z0 + ta * r + 0.9, z0 + ta * r + 1.0, "steel", col, mw)
        if bm.verts:
            cutter = new_object(f"{name}_tunnel_cutter", bm, None, col)
            cutter.matrix_world = mw
            cutter.hide_render = True
            cutter.display_type = "WIRE"
            bo = conc.modifiers.new("tunnels", "BOOLEAN")
            bo.operation = "DIFFERENCE"
            bo.object = cutter
            bo.solver = "EXACT"
        else:
            bm.free()

    # Seats: runs of consecutive labels (no gap) over consecutive rows with the same labels
    count, k = 0, 0
    step = -SEAT_PITCH if high else SEAT_PITCH
    for b in blocks:
        rows_sorted = sorted(b["rows"])
        groups = []
        for rw in rows_sorted:
            if groups and groups[-1][1] == b["rows"][rw] and groups[-1][0][-1] == rw - 1:
                groups[-1][0].append(rw)
            else:
                groups.append(([rw], b["rows"][rw]))
        for rows_g, labels in groups:
            run = [labels[0]]
            for lab in labels[1:] + [None]:
                if lab is not None and lab == run[-1] + 1 and run[-1] not in b["gaps"]:
                    run.append(lab)
                    continue
                count += seat_run(f"{name}_{b['name']}_{k}", seat_x(b, run[0]), step, run, rows_g,
                                  tier, col, seat_mesh, seat_mat, mw, b["name"], key, ti)
                k += 1
                run = [lab]

    # Block letters above the top row (S8 IMG_0840), on small yellow plaques
    if tier.get("labels"):
        for b in blocks:
            lx = (b["x0"] + b["x1"]) / 2
            yb = y0 + rows_n * t
            zt = z0 + (rows_n - 1) * r + 2.6
            box_object(f"{name}_plaque_{b['name']}", lx - 0.35, lx + 0.35, yb - 0.06, yb - 0.02,
                       zt - 0.1, zt + 0.7, "banner_yellow", col, mw)
            cu = bpy.data.curves.new(f"label_{b['name']}", "FONT")
            cu.body = b["name"]
            cu.size = 0.6
            cu.align_x = "CENTER"
            cu.materials.append(MATS["steel"])
            tx_ob = bpy.data.objects.new(f"{name}_label_{b['name']}", cu)
            col.objects.link(tx_ob)
            tx_ob.matrix_world = mw @ Matrix.Translation((lx, yb - 0.07, zt)) @ Matrix.Rotation(math.pi / 2, 4, "X")
    return count


def add_blocks(key, blocks, x0, x1, col, mw):
    for i, b in enumerate(blocks):
        bx0, bx1 = b["x"] if b["x"] else (x0, x1)
        if b.get("repeat"):
            w, gap = b["repeat"]
            bm = bmesh.new()
            x = bx0 + gap / 2
            while x + w <= bx1:
                add_box(bm, x, x + w, b["y"][0], b["y"][1], b["z"][0], b["z"][1])
                x += w + gap
            ob = new_object(f"{key}_block{i}", bm, b["mat"], col)
            ob.matrix_world = mw
        else:
            box_object(f"{key}_block{i}", bx0, bx1, b["y"][0], b["y"][1], b["z"][0], b["z"][1],
                       b["mat"], col, mw)


def build_stand(key, stand, col, seat_mesh, seat_mats):
    mw = stand_matrix(stand)
    x0, x1 = local_x_range(stand)
    seats_total = 0
    for i, tier in enumerate(stand["tiers"]):
        _CURRENT.update(stand=key, tier=i)
        seats_total += build_tier(f"{key}_t{i}", tier, x0, x1, col, seat_mesh,
                                  seat_mats[tier["colour"]], mw, stand)

    t0 = stand["tiers"][0]
    box_object(f"{key}_front_wall", x0, x1, t0["y0"] - 0.3, t0["y0"], 0, t0["z0"] + 0.6,
               "concrete_dark", col, mw)
    by0, by1 = stand["back"]["y"]
    box_object(f"{key}_back", x0, x1, by0, by1, 0, stand["back"]["z"], "cladding", col, mw)

    roof = stand["roof"]
    ry0, ry1 = roof["y"]
    rz, th = roof["z"], roof["thick"]
    for xa, xb in ((x0 - 0.3, x0), (x1, x1 + 0.3)):
        box_object(f"{key}_end", xa, xb, t0["y0"] - 0.3, by1, 0, rz, stand["end_mat"], col, mw)

    # Roof: flat with a slope (rises towards the back) or curved ("arc")
    n = 16
    top, bot = [], []
    for i in range(n + 1):
        f = i / n
        y = ry0 + (ry1 - ry0) * f
        lift = roof.get("slope", 0.0) * f + roof.get("arc", 0.0) * math.sin(math.pi * f)
        bot.append((y, rz + roof.get("slope", 0.0) * f))
        top.append((y, rz + th + lift))
    prism_object(f"{key}_roof", bot + list(reversed(top)), x0 - 0.3, x1 + 0.3, "roof_top", col, mw)
    box_object(f"{key}_fascia", x0 - 0.3, x1 + 0.3, ry0, ry0 + 0.35, rz - 0.9, rz + th + 0.2,
               "steel", col, mw)

    # Rafters under the roof, one per bay, deepening towards the back (S7/S8 photos show
    # exposed steel rafters under Oost and Noord, and a curved beam line under West)
    bay = roof.get("bay")
    if bay:
        sl = roof.get("slope", 0.0)
        prof = [(ry0 + 0.35, rz - 0.5), (ry1, rz + sl - roof.get("rafter_depth", 1.4)),
                (ry1, rz + sl), (ry0 + 0.35, rz)]
        n = max(1, round((x1 - x0) / bay))
        bm_x = [x0 + i * (x1 - x0) / n for i in range(n + 1)]
        for i, bx in enumerate(bm_x):
            prism_object(f"{key}_rafter{i}", prof, bx - 0.2, bx + 0.2, "steel", col, mw)
        # purlins along the stand, every ~4 m across the roof depth
        y = ry0 + 4.0
        while y < ry1 - 1.0:
            f = (y - ry0) / (ry1 - ry0)
            zb = rz + sl * f
            box_object(f"{key}_purlin", x0, x1, y - 0.12, y + 0.12, zb - 0.35, zb, "steel", col, mw)
            y += 4.0
        col_y = roof.get("columns_y")
        if col_y is not None:
            f = (col_y - ry0) / (ry1 - ry0)
            ztop = rz + sl * f
            for i, bx in enumerate(bm_x):
                box_object(f"{key}_column{i}", bx - 0.3, bx + 0.3, col_y - 0.3, col_y + 0.3, 0.0, ztop,
                           "steel", col, mw)

    if stand.get("lights"):
        # floodlights under the roof front (S7). One lamp object arrayed along the stand.
        lamp = box_object(f"{key}_lamps", x0 + 1.0, x0 + 1.6, ry0 + 0.6, ry0 + 1.0,
                          rz - 1.4, rz - 0.9, "lamp", col, mw)
        a = lamp.modifiers.new("along", "ARRAY")
        a.use_relative_offset = False
        a.use_constant_offset = True
        a.constant_offset_displace = (1.8, 0, 0)
        a.count = int((x1 - x0 - 2.0) / 1.8)

    add_blocks(key, stand["blocks"], x0, x1, col, mw)
    return seats_total


def build_corners(col):
    """Corner buildings (S1 footprint, S7 photos)."""
    # NE: brick hotel tower between Noord and Oost, ~7 storeys of windows (S7).
    # Height and width PH (IMG_6935: top 23.5 m, face from u~27 to ~48 at v=55, second render check)
    box_object("ne_tower", 26.5, 50.0, 55.0, 73.5, 0, 23.5, "brick", col)  # PH top 23.6 m (IMG_6935)
    box_object("ne_tower_roof", 26.3, 50.2, 54.8, 73.7, 23.5, 24.0, "roof_top", col)
    bm = bmesh.new()
    for floor in range(7):
        z = 3.5 + floor * 2.9
        x = 28.0
        while x + 1.0 < 49.0:   # windows facing the pitch (south face)
            add_box(bm, x, x + 1.0, 54.9, 55.0, z, z + 1.5)
            x += 2.2
        y = 57.0
        while y + 1.0 < 73.0:   # windows facing west (towards Noord's seats)
            add_box(bm, 26.4, 26.5, y, y + 1.0, z, z + 1.5)
            y += 2.4
    new_object("ne_tower_windows", bm, "glass", col)
    # club banner on the tower (S7: Daio Wasabi Stayen Stadium)
    box_object("ne_banner", 33.0, 37.0, 54.85, 54.9, 8.0, 14.0, "banner_blue", col)
    # fill to the east stand's back line
    box_object("ne_fill", 50.0, 61.0, 52.0, 73.5, 0, 16.5, "cladding", col)

    # NW: brick tower and glazed block between West and Noord (S7)
    box_object("nw_tower", -44.0, -40.3, 55.2, 73.5, 0, 23.0, "brick", col)
    box_object("nw_glass", -66.0, -44.0, 52.0, 73.5, 0, 17.0, "glass", col)
    box_object("nw_glass_roof", -66.2, -43.8, 51.8, 73.7, 17.0, 17.4, "roof_top", col)


def build_south_provisional(col):
    """2020 design (S3), provisional."""
    s = SOUTH
    front = -s["front"]
    half = s["length"] / 2
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
    tl = s["terrace_length"] / 2
    steps = 5
    for i in range(steps):
        z = s["terrace_height"] * (i + 1) / steps
        y_a = front - i * s["terrace_depth"] / steps
        box_object(f"south_terrace_{i}", -tl, tl, y_a - s["terrace_depth"] / steps, y_a, 0, z,
                   "provisional", col)



def build_south_current(col):
    """Zuid as it stands since the June 2026 demolition (S8 IMG_0835): an empty site behind a
    black screen on poles, a tower crane at the south-east corner. Sizes EST from the photo."""
    # black screen behind the south goal line, ~4 m high, with taller poles
    box_object("south_screen", -40.0, 34.0, -58.4, -58.2, 0.0, 4.0, "hoarding", col)
    bm = bmesh.new()
    u = -40.0
    while u <= 34.0:
        add_box(bm, u - 0.12, u + 0.12, -58.6, -58.4, 0.0, 9.0)
        u += 7.4
    new_object("south_screen_poles", bm, "steel", col)
    # building site
    box_object("south_site", -45.0, 40.0, -85.0, -58.6, -0.01, 0.02, "site", col)
    # tower crane (S8): mast ~45 m, jib towards the west across the south end. EST
    cx, cy = 28.0, -70.0
    box_object("crane_mast", cx - 1.0, cx + 1.0, cy - 1.0, cy + 1.0, 0.0, 44.0, "crane_yellow", col)
    box_object("crane_cab", cx - 1.4, cx + 1.4, cy - 1.4, cy + 1.4, 44.0, 47.0, "fascia_white", col)
    box_object("crane_jib", cx - 55.0, cx + 1.0, cy - 0.7, cy + 0.7, 46.0, 48.0, "crane_red", col)
    box_object("crane_counterjib", cx + 1.0, cx + 16.0, cy - 0.8, cy + 0.8, 46.0, 47.4, "crane_red", col)
    box_object("crane_hook", cx - 30.1, cx - 29.9, cy - 0.05, cy + 0.05, 12.0, 46.0, "steel", col)


def build_neighbourhood(col):
    """Terraced houses beyond the railway to the south (S8 IMG_0835, S1). Generic, EST."""
    import random
    rnd = random.Random(7)
    for row, (y_front, depth) in enumerate(((-96.0, 9.0), (-122.0, 9.0), (-148.0, 9.0))):
        u = -110.0
        while u < 110.0:
            w = rnd.choice((24.0, 30.0, 36.0))
            eave = rnd.choice((5.6, 6.0, 6.4))
            ridge = eave + rnd.choice((3.0, 3.6))
            y0, y1 = y_front - depth, y_front
            box_object(f"house_{row}_{int(u)}", u, u + w - 2.0, y0, y1, 0, eave, "house_brick", col)
            prism_object(f"roof_{row}_{int(u)}", [(y0 - 0.3, eave), (y1 + 0.3, eave),
                         ((y0 + y1) / 2, ridge)], u - 0.2, u + w - 1.8, "house_roof", col)
            u += w + rnd.choice((4.0, 8.0, 12.0))


def build_south(col, mode):
    if mode == "provisional":
        build_south_provisional(col)
    else:
        build_south_current(col)
    build_neighbourhood(col)


def build_south_fixtures(col):
    # Floodlight masts at the two south corners, still standing (S7, S8). Height EST ~35 m
    for name, x, y in (("mast_se", 44.0, -64.0), ("mast_sw", -46.0, -66.0)):
        box_object(name, x - 0.4, x + 0.4, y - 0.4, y + 0.4, 0, 35.0, "steel", col)
        box_object(name + "_head", x - 2.0, x + 2.0, y - 0.3, y + 0.3, 33.0, 37.0, "lamp", col)
    # Video screen at the south end of Oost (S7). Size EST
    box_object("screen_frame", 30.0, 40.0, -61.0, -60.3, 7.0, 13.0, "steel", col)
    box_object("screen", 30.4, 39.6, -60.35, -60.25, 7.4, 12.6, "screen", col)


# ---------------------------------------------------------------------------
# Advertising inventory (S8 IMG_0841: printed boards on the stand front walls, LED in front)
# ---------------------------------------------------------------------------

SLOTS = []  # (slot_id, kind, location, width_m, height_m)


def slot_material(cfg, slot, kind):
    ads = cfg.get("ads", {})
    path = ads.get("assign", {}).get(slot) or os.path.join(ads.get("folder", "adslots"), f"{slot}.png")
    strength = ads.get("led_strength", 1.2) if kind == "led" else 0.0
    if os.path.exists(path):
        return make_image_material(path, strength)
    return MATS["steel"]


def build_ads(cfg, col):
    hl, hw = PITCH_LENGTH / 2, PITCH_WIDTH / 2
    o, h = AD_BOARD_OFFSET, AD_BOARD_HEIGHT
    tile = cfg.get("ads", {}).get("led_tile_m", 10.0)

    # LED faces, one tiled artwork per run. Corners run left to right as seen from the pitch.
    runs = [
        ("LED-W", (-hw - o + 0.01, -hl + 2, 0), (-hw - o + 0.01, hl - 2, 0)),
        ("LED-E", (hw + o - 0.01, hl - 2, 0), (hw + o - 0.01, -hl + 2, 0)),
        ("LED-N1", (-hw + 2, hl + o - 0.01, 0), (-6, hl + o - 0.01, 0)),
        ("LED-N2", (6, hl + o - 0.01, 0), (hw - 2, hl + o - 0.01, 0)),
        ("LED-S1", (hw - 2, -hl - o + 0.01, 0), (6, -hl - o + 0.01, 0)),
        ("LED-S2", (-6, -hl - o + 0.01, 0), (-hw + 2, -hl - o + 0.01, 0)),
    ]
    for slot, a, b in runs:
        L = (Vector(b) - Vector(a)).length
        SLOTS.append((slot, "led", "perimeter LED", round(L, 1), h))
        led_slot = slot.rstrip("12")
        quad_object(slot, [a, b, (b[0], b[1], h), (a[0], a[1], h)],
                    slot_material(cfg, led_slot, "led"), col, u_repeat=L / tile)

    # Printed boards on the front walls: 6 m panels (EST, typical widths in IMG_0841)
    walls = {"east": ("ST-E", 0.9), "west": ("ST-W", 1.0), "north": ("ST-N", 1.0)}
    for key, (prefix, bh) in walls.items():
        stand = STANDS[key]
        mw = stand_matrix(stand)
        x0, x1 = local_x_range(stand)
        t0 = stand["tiers"][0]
        yf = t0["y0"] - 0.32
        ztop = t0["z0"] + 0.6
        n = int((x1 - x0) // 6.0)
        w = (x1 - x0) / n
        for i in range(n):
            slot = f"{prefix}-{i + 1:02d}"
            xa, xb = x0 + i * w + 0.05, x0 + (i + 1) * w - 0.05
            SLOTS.append((slot, "board", f"{key} front wall", round(xb - xa, 2), bh))
            quad_object(slot, [(xa, yf, ztop - bh), (xb, yf, ztop - bh), (xb, yf, ztop), (xa, yf, ztop)],
                        slot_material(cfg, slot, "board"), col, mw=mw)

    # Oost back fascia between the roof columns (DMM.com today, S7/S8): 12 bays
    stand = STANDS["east"]
    mw = stand_matrix(stand)
    x0, x1 = local_x_range(stand)
    n = 12
    w = (x1 - x0) / n
    for i in range(n):
        slot = f"FA-E-{i + 1:02d}"
        xa, xb = x0 + i * w + 0.2, x0 + (i + 1) * w - 0.2
        SLOTS.append((slot, "fascia", "east back fascia", round(xb - xa, 2), 1.2))
        quad_object(slot, [(xa, 21.28, 15.3), (xb, 21.28, 15.3), (xb, 21.28, 16.5), (xa, 21.28, 16.5)],
                    slot_material(cfg, slot, "fascia"), col, mw=mw)


def write_inventory(path):
    import csv
    with open(path, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["slot", "kind", "location", "width_m", "height_m"])
        for row in SLOTS:
            wr.writerow(row)


# ---------------------------------------------------------------------------
# Web export: stadium as GLB, seats as a compact JSON for instancing in the browser
# ---------------------------------------------------------------------------

def seat_colour(seat, cfg):
    """0 = yellow, 1 = blue. Mirrors the render shaders closely enough for a concept."""
    import random
    x, y, z = seat["pos"]
    rnd = random.Random(hash((round(x * 2), round(y * 2), round(z * 2.5))) & 0xFFFFFFFF).random()
    spec = cfg["stand_seat_colours"]
    key = {("east", 0): "east", ("north", 0): "north", ("west", 0): "west_lower",
           ("west", 1): "west_balcony", ("west", 2): "west_hosp",
           ("west", 3): "west_hosp"}[(seat["stand"], seat["tier"])]
    sp = spec[key]
    base_blue = sp["base"] == "seat_blue"
    if sp.get("pattern"):
        blob = 0.5 + 0.25 * (math.sin(0.23 * y + 1.3) * math.sin(0.55 * z + 0.4)
                             + math.sin(0.11 * (y + 2 * z) + 2.1))
        v = 0.65 * blob + 0.35 * rnd - 0.45 * min(1.0, max(0.0, (z - 6.0) / 9.0))
        accent = v > 0.58
    else:
        accent = rnd < sp["accent_share"]
    return int(base_blue != accent)


def export_web(out_dir, cfg):
    import json as _json
    os.makedirs(out_dir, exist_ok=True)

    tiers = list(STAND_NAMES)
    out = {
        "_note": "Generated by build.py --export-web. Blocks, rows and seat numbers follow the club ticketing system (S9). Positions are Blender metres (X towards Oost, "
                 "Y towards Noord, Z up), at the seat's tread; eye height is added in the page.",
        "eye_height": EYE_SEATED,
        "tiers": [{"id": f"{k}-{i}", "name": STAND_NAMES[(k, i)],
                   "outward": list(STANDS[k]["outward"]),
                   "blocks": [b["name"] for b in SEATMAP[f"{k}-{i}"].get("blocks") or SEATMAP[f"{k}-{i}"]["units"]]}
                  for k, i in tiers],
        "fields": ["tier", "block", "row", "seat", "x", "y", "z", "blue"],
        "seats": [],
    }
    for st in SEATS:
        ti = tiers.index((st["stand"], st["tier"]))
        lay = SEATMAP[f"{st['stand']}-{st['tier']}"]
        bi = [b["name"] for b in lay.get("blocks") or lay["units"]].index(st["block"])
        out["seats"].append([ti, bi, st["row"], st["no"], *st["pos"], seat_colour(st, cfg)])
    with open(os.path.join(out_dir, "seats.json"), "w") as f:
        _json.dump(out, f, separators=(",", ":"))

    # Stadium mesh: hide seats and boolean cutters, turn block letters into meshes, export GLB
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in list(bpy.context.scene.objects):
        if ob.type == "FONT":
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
            mob = bpy.data.objects.new(ob.name + "_mesh", me)
            for c in ob.users_collection:
                c.objects.link(mob)
            mob.matrix_world = ob.matrix_world.copy()
            bpy.data.objects.remove(ob)
        elif ob.type == "MESH" and ob.data.name == "seat_cr6":
            ob.hide_render = True
    # Export GLB, then repack it as glTF JSON with the binary buffer embedded as base64, so it is
    # plain .json that any static host (including claude.ai artifacts) will serve
    import base64
    import struct
    tmp = os.path.abspath(os.path.join(out_dir, "_stadium.glb"))
    bpy.ops.export_scene.gltf(filepath=tmp, export_format="GLB", use_renderable=True,
                              export_apply=True, export_lights=False, export_cameras=False)
    raw = open(tmp, "rb").read()
    jlen = struct.unpack("<I", raw[12:16])[0]
    gltf = _json.loads(raw[20:20 + jlen])
    blen = struct.unpack("<I", raw[20 + jlen:24 + jlen])[0]
    binary = raw[28 + jlen:28 + jlen + blen]
    gltf["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(binary).decode()
    with open(os.path.join(out_dir, "stadium.gltf.json"), "w") as f:
        _json.dump(gltf, f, separators=(",", ":"))
    os.remove(tmp)
    print(f"[export] {len(out['seats'])} seats, stadium.gltf.json in {out_dir}")


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
    z = tier["z0"] + i * tier["riser"] + cam.get("eye", EYE_SEATED)
    x = local_x(stand, cam["along"])
    return stand_matrix(stand) @ Vector((x, y, z))


def add_camera(name, cam):
    pos = seat_eye(cam) if cam["type"] == "seat" else Vector(cam["position"])
    cd = bpy.data.cameras.new(name)
    cd.lens = cam.get("lens_mm", 24)
    cd.sensor_fit = cam.get("sensor_fit", "AUTO")
    cd.sensor_width = cam.get("sensor_mm", 36)
    cd.clip_end = 2000
    cd.clip_start = cam.get("clip_start", 0.1)
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = pos
    if cam["type"] == "solved":
        # OpenCV camera (x right, y down, z forward) -> Blender camera (x right, y up, -z forward)
        Rt = Matrix(cam["R_cv"]).transposed()
        cols = [Rt.col[0], -Rt.col[1], -Rt.col[2]]
        rot = Matrix([[cols[j][i] for j in range(3)] for i in range(3)])
        ob.rotation_euler = rot.to_euler()
    else:
        d = Vector(cam["target"]) - pos
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def check_scene():
    problems = []
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH" or ob.name == "ground":
            continue
        zs = [(ob.matrix_world @ Vector(c)).z for c in ob.bound_box]
        if min(zs) < -0.05:
            problems.append(f"{ob.name}: lowest point {min(zs):.2f} m below ground")
    return problems


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    final = "--final" in argv
    save = argv[argv.index("--save") + 1] if "--save" in argv else None
    web = argv[argv.index("--export-web") + 1] if "--export-web" in argv else None
    args = [a for a in argv if not a.startswith("--") and a not in (save, web)]
    scene_path, out_dir = args[0], args[1]
    only = args[2:]

    with open(scene_path) as f:
        cfg = json.load(f)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0

    colours = cfg["colours"]
    for k, v in colours.items():
        if k.startswith("sky") or k.startswith("seat"):
            continue
        rough = 0.15 if k in ("glass", "steel_glass") else 0.75
        make_material(k, v, roughness=rough, metallic=0.6 if k == "steel" else 0.0)
    m = make_material("glass_clear", colours["glass"], roughness=0.05)
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Alpha"].default_value = 0.18
    m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
    make_emissive("lamp", colours["lamp_glow"], cfg["lights_on"] * 40.0 + 0.5)
    make_emissive("led", colours["led_board"], 0.6)
    make_emissive("screen", colours["screen_glow"], 2.0)

    seat_mats = {}
    for key, spec in cfg["stand_seat_colours"].items():
        if spec.get("pattern"):
            seat_mats[key] = make_pattern(f"seats_{key}", colours[spec["base"]], colours[spec["accent"]])
        else:
            seat_mats[key] = make_mosaic(f"seats_{key}", colours[spec["base"]],
                                         colours[spec["accent"]], spec["accent_share"])

    col = bpy.data.collections.new("stadium")
    sc.collection.children.link(col)
    build_pitch(col)
    seat_mesh = make_seat_mesh()
    seats = sum(build_stand(k, s, col, seat_mesh, seat_mats) for k, s in STANDS.items())
    build_corners(col)
    build_south(col, cfg.get("south_mode", "current"))
    build_south_fixtures(col)
    build_ads(cfg, col)
    ads_dir = cfg.get("ads", {}).get("folder", "adslots")
    os.makedirs(ads_dir, exist_ok=True)
    write_inventory(os.path.join(ads_dir, "inventory.csv"))
    setup_world(cfg)
    print(f"[build] seats modelled: {seats}; ad slots: {len(SLOTS)}")
    for p in check_scene():
        print("[check]", p)

    if web:
        export_web(web, cfg)
        return

    r = cfg["render"]
    sc.render.engine = r["engine"]
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
        res = cam.get("resolution") or (r["final_resolution"] if final else r["draft_resolution"])
        sc.render.resolution_x, sc.render.resolution_y = res
        ob = add_camera(name, cam)
        sc.camera = ob
        sc.render.filepath = os.path.join(out_dir, f"{name}.png")
        print(f"[render] {name} at {tuple(round(c, 2) for c in ob.location)}")
        bpy.ops.render.render(write_still=True)

    if save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(save))


if __name__ == "__main__":
    main()
