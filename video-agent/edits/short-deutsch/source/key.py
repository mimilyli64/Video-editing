# green-screen key: takes/gs/greenscreen.mov -> keyed.mp4 (1080x1920, original fps) on a real photo background
import sys, subprocess, numpy as np
from PIL import Image, ImageFilter
SRC, BG, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
BLUR = float(sys.argv[4]) if len(sys.argv) > 4 else 3
LIMIT = int(sys.argv[5]) if len(sys.argv) > 5 else 10**9
TINT = np.array([float(v) for v in (sys.argv[6] if len(sys.argv) > 6 else "1,1,1").split(",")], np.float32)   # colour match to the room light
IW, IH, OW, OH = 720, 1280, 1080, 1920
y0, y1 = 22, 1100; h = y1 - y0; w = int(h * 9 / 16); x0 = 360 - w // 2     # shins up, 9:16
im = Image.open(BG).convert('RGB'); iw, ih = im.size; s = max(OW / iw, OH / ih)
im = im.resize((int(iw * s) + 1, int(ih * s) + 1), Image.LANCZOS)
cx, cy = .5, .5; x = int((im.width - OW) * cx); y = int((im.height - OH) * cy)
bg = np.array(im.crop((x, y, x + OW, y + OH)).filter(ImageFilter.GaussianBlur(BLUR))).astype(np.float32)
blurbg = np.array(Image.fromarray(bg.astype(np.uint8)).filter(ImageFilter.GaussianBlur(12))).astype(np.float32)
dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', SRC, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
fps = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', SRC], capture_output=True, text=True).stdout.strip()
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', fps, '-i', '-', '-i', SRC,
                        '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '12', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-shortest', OUT], stdin=subprocess.PIPE)
n = 0
while n < LIMIT:
    buf = dec.stdout.read(IW * IH * 3)
    if len(buf) < IW * IH * 3: break
    f = np.frombuffer(buf, np.uint8).reshape(IH, IW, 3)[y0:y1, x0:x0 + w].astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]; d = g - np.maximum(r, b)
    a = 1 - np.clip((d - 14) / 30, 0, 1); a[:max(0, 22 - y0)] = 0
    aI = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1.1))
    g2 = np.where(g > np.maximum(r, b), np.maximum(r, b), g); g2 = np.minimum(g2, (r + b) / 2 + 12)
    ah = np.asarray(aI).astype(np.float32) / 255
    fg = np.stack([r, np.where(ah < .98, g2, np.minimum(g, np.maximum(r, b) + 6)), b], -1)
    fg = np.asarray(Image.fromarray(fg.clip(0, 255).astype(np.uint8)).resize((OW, OH), Image.LANCZOS)).astype(np.float32)
    A = np.asarray(aI.resize((OW, OH), Image.LANCZOS)).astype(np.float32) / 255
    edge = np.asarray(Image.fromarray(((1 - A) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))).astype(np.float32) / 255 * A
    fg = fg * (1 - .25 * edge[..., None]) + blurbg * (.25 * edge[..., None])
    fg = fg * TINT
    out = fg * A[..., None] + bg * (1 - A[..., None])
    enc.stdin.write(out.clip(0, 255).astype(np.uint8).tobytes()); n += 1
enc.stdin.close(); enc.wait(); print('frames', n)
