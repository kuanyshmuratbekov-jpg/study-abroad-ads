import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = sys.argv[1]          # camp.mp4
OUT = sys.argv[2]          # output dir
TMP = sys.argv[3]          # temp dir
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)

F = "/usr/share/fonts/opentype/inter/"
def font(w, s): return ImageFont.truetype(F + {"xb": "Inter-ExtraBold.otf", "b": "Inter-Bold.otf", "sb": "Inter-SemiBold.otf", "m": "Inter-Medium.otf"}[w], s)

NAVY = (24, 26, 82); NAVY2 = (44, 40, 128); RED = (214, 25, 42); WHITE = (255, 255, 255); ICE = (200, 214, 255); CHIP = (86, 80, 200)
W, H = 1080, 1920
CARD_W, CARD_H, CARD_X, CARD_Y = 1000, 713, 40, 640

def gradient(w, h):
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        k = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(NAVY2[i] * (1 - k) + NAVY[i] * k) for i in range(3)))
    return im

def pill(d, x, y, text, f, fill, color, pad=(26, 14), anchor_center=False):
    tw = d.textlength(text, font=f); asc, desc = f.getmetrics()
    w = tw + pad[0] * 2; h = asc + desc + pad[1] * 2
    if anchor_center: x = x - w / 2
    d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=fill)
    d.text((x + pad[0], y + pad[1]), text, font=f, fill=color)
    return x + w, y + h

def center(d, y, text, f, color):
    d.text((W / 2, y), text, font=f, fill=color, anchor="ma")

def chips_row(d, y, items, f, total_w=W):
    gap = 18; pad = 24
    widths = [d.textlength(t, font=f) + pad * 2 for t in items]
    x = (total_w - sum(widths) - gap * (len(items) - 1)) / 2
    for t, w in zip(items, widths):
        pill(d, x, y, t, f, CHIP, WHITE, pad=(pad, 12))
        x += w + gap

# ---------- reel ----------
SEGMENTS = [  # src_time, duration, headline lines, subline
    (0.5, 3.0, ["Зимние каникулы", "в Грузии"], "Английский лагерь в горах"),
    (14.0, 2.5, ["Гудаури, Грузия"], "4–9 января 2027"),
    (19.0, 3.0, ["Английский", "+ лидерство"], "и предпринимательство"),
    (31.0, 3.0, ["Для детей", "9–17 лет"], "Занятия на английском каждый день"),
    (40.5, 3.0, ["Вылет из Астаны"], "3 января → возвращение 9 января"),
    (65.0, 3.5, ["Напишите", "«ГРУЗИЯ» в директ"], "Пришлём программу и стоимость"),
]

mask = Image.new("L", (CARD_W, CARD_H), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, CARD_W - 1, CARD_H - 1], radius=36, fill=255)
mask.save(f"{TMP}/mask.png")

segs = []
for i, (t, dur, lines, sub) in enumerate(SEGMENTS):
    bg = gradient(W, H); d = ImageDraw.Draw(bg)
    pill(d, W / 2, 150, "SpeakUp · Winter Camp 2027", font("b", 34), RED, WHITE, anchor_center=True)
    fh = font("xb", 92 if max(len(l) for l in lines) <= 16 else 80)
    y = 250 if len(lines) == 2 else 300
    for l in lines:
        center(d, y, l, fh, WHITE); y += 104
    center(d, y + 14, sub, font("sb", 44), ICE)
    # shadow under card
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([CARD_X, CARD_Y + 18, CARD_X + CARD_W, CARD_Y + CARD_H + 18], radius=36, fill=(0, 0, 0, 110))
    bg = Image.alpha_composite(bg.convert("RGBA"), sh.filter(ImageFilter.GaussianBlur(22))).convert("RGB"); d = ImageDraw.Draw(bg)
    # persistent info strip
    chips_row(d, 1420, ["4–9 января", "9–17 лет", "Вылет из Астаны"], font("sb", 38))
    # progress dots
    n = len(SEGMENTS); x0 = W / 2 - (n * 34) / 2
    for k in range(n):
        d.rounded_rectangle([x0 + k * 34, 1530, x0 + k * 34 + 24, 1538], radius=4, fill=WHITE if k <= i else NAVY2)
    bg.save(f"{TMP}/bg{i}.png")
    seg = f"{TMP}/seg{i}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-t", str(dur), "-i", SRC,
                    "-loop", "1", "-i", f"{TMP}/bg{i}.png", "-loop", "1", "-i", f"{TMP}/mask.png",
                    "-filter_complex",
                    f"[0:v]crop=2160:1540:0:0,scale={CARD_W}:{CARD_H},setsar=1,format=rgba[v];"
                    f"[2:v]format=gray[m];[v][m]alphamerge[vm];"
                    f"[1:v][vm]overlay={CARD_X}:{CARD_Y}:shortest=1,fps=30,format=yuv420p[o]",
                    "-map", "[o]", "-t", str(dur), "-c:v", "libx264", "-preset", "medium", "-crf", "20", seg], check=True)
    segs.append(seg)

with open(f"{TMP}/list.txt", "w") as fl:
    for s in segs: fl.write(f"file '{s}'\n")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{TMP}/list.txt",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-movflags", "+faststart", f"{OUT}/reel-trial.mp4"], check=True)

# ---------- banners ----------
def still(t, name):
    p = f"{TMP}/{name}.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", SRC, "-frames:v", "1",
                    "-vf", "crop=2160:1500:0:40", p], check=True)
    return Image.open(p).convert("RGB")

def cover(im, w, h, right=False):
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r + 1), int(im.height * r + 1)), Image.LANCZOS)
    x = (im.width - w) if right else (im.width - w) // 2; y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))

def fade(im, start, color):
    w, h = im.size; ov = Image.new("RGBA", (w, h)); od = ImageDraw.Draw(ov)
    for y in range(start, h):
        a = int(255 * min(1, (y - start) / (h * 0.18)))
        od.line([(0, y), (w, y)], fill=color + (a,))
    return Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")

ski = still(1.0, "ski"); gond = still(40.5, "gondola")

def banner(w, h, photo, photo_h, path, ytext, right=False):
    im = gradient(w, h)
    ph = cover(photo, w, photo_h, right); im.paste(ph, (0, 0))
    im = fade(im, photo_h - int(h * 0.20), NAVY2)
    d = ImageDraw.Draw(im)
    pill(d, 48, 48, "SpeakUp · Winter Camp 2027", font("b", 32), RED, WHITE)
    y = ytext
    for l in ["Зимние каникулы", "в Грузии с английским"]:
        d.text((w / 2, y), l, font=font("xb", 76), fill=WHITE, anchor="ma"); y += 88
    for k, l in enumerate(["Международный английский лагерь в Гудаури", "Лидерство и предпринимательство"]):
        d.text((w / 2, y + 10 + k * 44), l, font=font("m", 34), fill=ICE, anchor="ma")
    y += 44
    chips_row(d, y + 80, ["4–9 января 2027", "9–17 лет", "Вылет из Астаны"], font("sb", 36), total_w=w)
    bw, bh = 640, 96; bx = (w - bw) / 2; by = y + 190
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh / 2, fill=RED)
    d.text((w / 2, by + bh / 2), "Напишите «ГРУЗИЯ» в директ", font=font("b", 38), fill=WHITE, anchor="mm")
    im.save(path, quality=93)

banner(1080, 1350, ski, 780, f"{OUT}/banner-feed-4x5.jpg", 660)
banner(1080, 1920, gond, 1200, f"{OUT}/banner-story-9x16.jpg", 1080, right=True)
print("done")
