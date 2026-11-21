"""Put a reference photo and a render side by side, with an optional 50% overlay.

    python tools/compare.py references/photos/IMG_6223.jpg renders/match_IMG6223_west.png out.jpg
"""
import sys

from PIL import Image


def main(photo_path, render_path, out_path, height=900):
    photo = Image.open(photo_path).convert("RGB")
    render = Image.open(render_path).convert("RGB")

    def fit(im):
        return im.resize((round(im.width * height / im.height), height), Image.LANCZOS)

    photo, render = fit(photo), fit(render)
    blend = Image.blend(photo, render.resize(photo.size), 0.5)
    out = Image.new("RGB", (photo.width + render.width + blend.width, height), "white")
    out.paste(photo, (0, 0))
    out.paste(render, (photo.width, 0))
    out.paste(blend, (photo.width + render.width, 0))
    out.save(out_path, quality=88)


if __name__ == "__main__":
    main(*sys.argv[1:4])
