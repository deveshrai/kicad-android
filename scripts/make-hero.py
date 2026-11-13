#!/usr/bin/env python3
"""Draws the README hero image: a laptop and a tablet, each showing a real screenshot of the app.

Usage: make-hero.py LAPTOP_SHOT:TOP:BOTTOM TABLET_SHOT:TOP:BOTTOM OUT.png

Both screenshots should be 16:10 landscape (the Galaxy Tab S12+ is 2800x1752, the test
emulator 2560x1600); they are scaled into the screens.  Only the app window is used: TOP and
BOTTOM are the first and last pixel rows of the window in the screenshot, so the status bar
and the taskbar (with the owner's apps on it) are left out.  The band above the window gets
the window's own colour, the band below it is left dark.

The devices are drawn, not photographed, so the caption should say that the screens are
screenshots.  Needs Pillow.
"""

import sys

from PIL import Image, ImageDraw, ImageFilter

SS = 2  # supersampling, for smooth edges

W, H = 2400, 1340


def s(v):
    return int(round(v * SS))


def rounded(draw, box, radius, fill):
    draw.rounded_rectangle([s(c) for c in box], radius=s(radius), fill=fill)


def load_window(spec):
    path, top, bottom = spec.rsplit(":", 2)
    shot = Image.open(path).convert("RGB")
    top, bottom = int(top), int(bottom)
    return shot, top, bottom


def paste_screen(canvas, window, box, radius):
    shot, top, bottom = window
    x0, y0, x1, y1 = box
    size = (s(x1 - x0), s(y1 - y0))
    scale = size[1] / shot.height
    img = Image.new("RGB", size, (11, 11, 12))
    ImageDraw.Draw(img).rectangle([0, 0, size[0], int(top * scale) + 1],
                                  fill=shot.getpixel((shot.width // 2, top + 1)))
    app = shot.crop((0, top, shot.width, bottom + 1))
    app = app.resize((size[0], int(round(app.height * scale))), Image.LANCZOS)
    img.paste(app, (0, int(round(top * scale))))
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=s(radius),
                                           fill=255)
    canvas.paste(img, (s(x0), s(y0)), mask)


def shadow(canvas, box, radius, blur, alpha, offset=(0, 0)):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    x0, y0, x1, y1 = box
    ImageDraw.Draw(layer).rounded_rectangle(
        [s(x0 + offset[0]), s(y0 + offset[1]), s(x1 + offset[0]), s(y1 + offset[1])],
        radius=s(radius), fill=(0, 0, 0, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(s(blur)))
    canvas.alpha_composite(layer)


def laptop(canvas, shot, x, y, screen_w):
    screen_h = screen_w * 10 / 16
    bezel, top_bezel = 22, 30
    lid = (x, y, x + screen_w + 2 * bezel, y + screen_h + top_bezel + bezel)
    base_y = lid[3]
    overhang = 120
    base = [(lid[0] - overhang, base_y), (lid[2] + overhang, base_y),
            (lid[2] + overhang - 18, base_y + 34), (lid[0] - overhang + 18, base_y + 34)]

    shadow(canvas, (lid[0] - overhang + 30, base_y + 10, lid[2] + overhang - 30, base_y + 46),
           20, 18, 110)
    shadow(canvas, lid, 26, 22, 70, offset=(0, 10))

    draw = ImageDraw.Draw(canvas)
    rounded(draw, lid, 26, (78, 82, 89, 255))
    rounded(draw, (lid[0] + 3, lid[1] + 3, lid[2] - 3, lid[3] - 1), 23, (14, 15, 17, 255))
    # Camera
    cx, cy = (lid[0] + lid[2]) / 2, lid[1] + top_bezel / 2
    draw.ellipse([s(cx - 5), s(cy - 5), s(cx + 5), s(cy + 5)], fill=(44, 47, 52, 255))
    paste_screen(canvas, shot,
                 (lid[0] + bezel, lid[1] + top_bezel, lid[2] - bezel, lid[3] - bezel), 4)

    # The base, a silver slab seen edge on, with the notch for opening the lid
    draw.polygon([(s(px), s(py)) for px, py in base], fill=(186, 190, 197, 255))
    draw.rectangle([s(base[0][0]), s(base_y), s(base[1][0]), s(base_y + 9)],
                   fill=(214, 217, 222, 255))
    mid = (lid[0] + lid[2]) / 2
    draw.rounded_rectangle([s(mid - 110), s(base_y), s(mid + 110), s(base_y + 12)],
                           radius=s(6), fill=(160, 164, 171, 255))
    return lid, base_y + 34


def tablet(canvas, shot, x, y, screen_w):
    screen_h = screen_w * 10 / 16
    bezel = 26
    body = (x, y, x + screen_w + 2 * bezel, y + screen_h + 2 * bezel)

    shadow(canvas, body, 40, 26, 120, offset=(0, 16))

    draw = ImageDraw.Draw(canvas)
    rounded(draw, body, 40, (58, 61, 66, 255))
    rounded(draw, (body[0] + 4, body[1] + 4, body[2] - 4, body[3] - 4), 36, (12, 13, 15, 255))
    # Front camera on the long edge, as on Galaxy tablets held landscape
    cx, cy = (body[0] + body[2]) / 2, body[1] + bezel / 2
    draw.ellipse([s(cx - 5), s(cy - 5), s(cx + 5), s(cy + 5)], fill=(40, 43, 48, 255))
    paste_screen(canvas, shot,
                 (body[0] + bezel, body[1] + bezel, body[2] - bezel, body[3] - bezel), 14)
    return body


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)

    laptop_shot = load_window(sys.argv[1])
    tablet_shot = load_window(sys.argv[2])

    canvas = Image.new("RGBA", (s(W), s(H)), (0, 0, 0, 0))
    laptop(canvas, laptop_shot, 150, 20, 1560)
    tablet(canvas, tablet_shot, 1370, 640, 920)

    canvas = canvas.resize((W, H), Image.LANCZOS)
    canvas.save(sys.argv[3], optimize=True)


if __name__ == "__main__":
    main()
