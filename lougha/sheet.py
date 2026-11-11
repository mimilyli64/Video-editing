"""Contact sheet of preview stills: python3 -m lougha.sheet h 0.1,0.5,... out.png"""
import os, sys, cv2, numpy as np
from . import config as C
fmt, times, out = sys.argv[1], sys.argv[2].split(","), sys.argv[3]
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 3
ims = []
for t in times:
    p = os.path.join(C.BUILD, "stills", f"{fmt}_{float(t):05.2f}.png")
    im = cv2.imread(p)
    h = 360 if fmt == "h" else 480
    im = cv2.resize(im, (int(im.shape[1] * h / im.shape[0]), h))
    cv2.putText(im, f"{float(t):.2f}s", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    ims.append(im)
while len(ims) % cols:
    ims.append(np.zeros_like(ims[0]))
rows = [np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)]
cv2.imwrite(out, np.vstack(rows))
