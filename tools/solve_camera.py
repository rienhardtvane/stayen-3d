"""Solve a photo's camera from pitch markings with known positions, then measure heights.

Reads references/photo_points.json. For each photo: image points (px) of pitch markings
with known world coordinates (metres, centre-spot frame), and optionally "measure" entries:
an image point plus the world plane it lies on (axis 0 = u/X, 1 = v/Y, and the value).
Focal length is swept and the best fit kept, unless "f_px" is given (e.g. pinned by a second
check such as the centre circle). Prints the camera and the measured 3D points, and writes a
"solved" camera into scene.json so the render matches the photo exactly.

    python tools/solve_camera.py references/photo_points.json scene.json
"""
import json
import sys

import cv2
import numpy as np


def solve(entry):
    W, H = entry["size"]
    obj = np.array([p["world"] for p in entry["points"]], float)
    img = np.array([p["px"] for p in entry["points"]], float)
    fs = [entry["f_px"]] if entry.get("f_px") else np.arange(0.5 * W, 2.0 * W, 10)
    best = None
    for f in fs:
        K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1.0]])
        ok, r, t = cv2.solvePnP(obj, img, K, None)
        proj, _ = cv2.projectPoints(obj, r, t, K, None)
        err = np.sqrt(((proj.reshape(-1, 2) - img) ** 2).sum(1)).mean()
        if best is None or err < best[0]:
            best = (err, f, r, t, K)
    err, f, r, t, K = best
    R, _ = cv2.Rodrigues(r)
    C = (-R.T @ t).ravel()
    return err, f, R, C, K


def measure(R, C, K, px, axis, value):
    d = R.T @ (np.linalg.inv(K) @ np.array([px[0], px[1], 1.0]))
    s = (value - C[axis]) / d[axis]
    return C + s * d


def main(points_path, scene_path):
    data = json.load(open(points_path))
    scene = json.load(open(scene_path))
    for name, entry in data.items():
        if name.startswith("_"):
            continue
        err, f, R, C, K = solve(entry)
        W, H = entry["size"]
        print(f"\n{name}: reprojection error {err:.1f} px, f {f:.0f} px, camera at {C.round(2)}")
        for m in entry.get("measure", []):
            p = measure(R, C, K, m["px"], m["axis"], m["value"])
            print(f"  {m['name']:40s} {p.round(1)}")
        scale = 1008 / max(W, H)
        scene["cameras"][f"match_{name}"] = {
            "_note": f"Solved from {entry['photo']} (tools/solve_camera.py), error {err:.1f} px",
            "type": "solved",
            "position": [round(float(c), 3) for c in C],
            "R_cv": [[round(float(x), 6) for x in row] for row in R],
            "lens_mm": round(float(f) / W * 36.0, 2),
            "sensor_mm": 36.0,
            "sensor_fit": "HORIZONTAL",
            "resolution": [round(W * scale), round(H * scale)],
        }
    json.dump(scene, open(scene_path, "w"), indent=2)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
