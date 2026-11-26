"""usage: python3 qc_safe.py out.png t1 t2 ... -> stills with the platform dead zones tinted red (top 180, bottom 420, right 150)."""
import sys, subprocess
from PIL import Image, ImageDraw
out, ts = sys.argv[1], [float(x) for x in sys.argv[2:]]
subprocess.check_call([sys.executable, "render.py", "--stills"] + [str(t) for t in ts], stdout=subprocess.DEVNULL)
w, h = 270, 480
sheet = Image.new("RGB", (len(ts) * w, h))
for i, t in enumerate(ts):
    im = Image.open(f"frames_qc/still_{t:06.2f}.png").convert("RGBA").resize((w, h))
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    k = w / 1080
    for box in ((0, 0, w, 180 * k), (0, h - 420 * k, w, h), (w - 150 * k, 0, w, h)):
        d.rectangle(box, fill=(255, 0, 0, 90))
    sheet.paste(Image.alpha_composite(im, ov).convert("RGB"), (i * w, 0))
sheet.save(out)
