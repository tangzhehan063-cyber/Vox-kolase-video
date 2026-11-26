"""usage: python3 qc_grid.py out.png t1 t2 ... -> contact sheet of preview-size stills"""
import sys, subprocess, glob
from PIL import Image, ImageDraw
out, ts = sys.argv[1], [float(x) for x in sys.argv[2:]]
subprocess.check_call([sys.executable, "render.py", "--stills"] + [str(t) for t in ts], stdout=subprocess.DEVNULL)
ims = [Image.open(f"frames_qc/still_{t:06.2f}.png") for t in ts]
cols = min(len(ims), 6)
rows = (len(ims) + cols - 1) // cols
w, h = 360, 640
sheet = Image.new("RGB", (cols * w, rows * h), (20, 20, 20))
for i, im in enumerate(ims):
    im = im.resize((w, h), Image.LANCZOS)
    ImageDraw.Draw(im).text((8, 6), f"{ts[i]:.2f}s", fill=(255, 255, 255))
    sheet.paste(im, ((i % cols) * w, (i // cols) * h))
sheet.save(out)
