"""Make placeholder artwork for every advertising slot, so the inventory is visible in renders.

    python tools/make_slots.py adslots/inventory.csv adslots/

Each placeholder shows the slot id and its size. Replace a PNG (same name) with partner artwork,
or point the slot at another file in scene.json -> ads.assign. LED runs share one tiled image per
side (LED-W, LED-E, LED-N, LED-S), sized for a 10 m repeat.
"""
import csv
import os
import sys

from PIL import Image, ImageDraw, ImageFont

PALETTE = {"board": ["#1F3F94", "#F6C700", "#E9E9E9", "#C8282E", "#2E7D4F", "#222222"],
           "fascia": ["#F2F2F2"], "led": ["#0E1A3A"]}
INK = {"#F6C700": "#1F3F94", "#E9E9E9": "#1F3F94", "#F2F2F2": "#1F3F94"}
PX_PER_M = 100


def font(size):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def card(path, w_m, h_m, bg, title, sub):
    W, H = int(w_m * PX_PER_M), int(h_m * PX_PER_M)
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    ink = INK.get(bg, "#FFFFFF")
    d.rectangle([3, 3, W - 4, H - 4], outline=ink, width=3)
    f1, f2 = font(int(H * 0.42)), font(int(H * 0.2))
    d.text((W / 2, H * 0.42), title, fill=ink, font=f1, anchor="mm")
    d.text((W / 2, H * 0.8), sub, fill=ink, font=f2, anchor="mm")
    im.save(path)


def main(inventory, out):
    os.makedirs(out, exist_ok=True)
    rows = list(csv.DictReader(open(inventory)))
    done_led = set()
    for i, r in enumerate(rows):
        slot, kind = r["slot"], r["kind"]
        w, h = float(r["width_m"]), float(r["height_m"])
        if kind == "led":
            side = slot.rstrip("12")
            if side in done_led:
                continue
            done_led.add(side)
            card(os.path.join(out, f"{side}.png"), 10.0, h, PALETTE["led"][0],
                 f"{side}  ·  LED", "10 m repeat · partner artwork here")
        else:
            pal = PALETTE[kind]
            card(os.path.join(out, f"{slot}.png"), w, h, pal[i % len(pal)], slot,
                 f"{w:.1f} x {h:.1f} m · {r['location']}")
    print(f"{len(rows)} slots, placeholders in {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
