import io
import os
import time

import httpx
from fastapi import FastAPI, HTTPException, Response
from PIL import Image, ImageDraw
from ultralytics import YOLO

UPSTREAM_URL = os.environ["UPSTREAM_URL"]
MODEL_PATH = os.environ.get("MODEL_PATH", "yolov8s-worldv2.pt")
CONF_THRESHOLD = float(os.environ.get("CONF_THRESHOLD", "0.4"))
TARGET_CLASSES = {
    c.strip() for c in os.environ.get("TARGET_CLASSES", "").split(",") if c.strip()
}
WORLD_PROMPTS = [
    c.strip() for c in os.environ.get("WORLD_PROMPTS", "").split(",") if c.strip()
]
FETCH_TIMEOUT = float(os.environ.get("FETCH_TIMEOUT", "10"))
MIN_CY = float(os.environ.get("MIN_CY", "0"))
MAX_CY = float(os.environ.get("MAX_CY", "1e9"))
MIN_CX = float(os.environ.get("MIN_CX", "0"))
MAX_CX = float(os.environ.get("MAX_CX", "1e9"))

app = FastAPI(title="poormanYoloCam")
model = YOLO(MODEL_PATH)
if WORLD_PROMPTS:
    model.set_classes(WORLD_PROMPTS)
client = httpx.Client(timeout=FETCH_TIMEOUT)


def fetch_image() -> Image.Image:
    r = client.get(UPSTREAM_URL)
    if r.status_code != 200:
        raise HTTPException(502, f"upstream returned {r.status_code}")
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def detect(img: Image.Image):
    t0 = time.perf_counter()
    result = model.predict(img, conf=CONF_THRESHOLD, verbose=False)[0]
    names = result.names
    detections = []
    for box in result.boxes:
        cls = names[int(box.cls)]
        if TARGET_CLASSES and cls not in TARGET_CLASSES:
            continue
        x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        if not (MIN_CX <= cx <= MAX_CX and MIN_CY <= cy <= MAX_CY):
            continue
        detections.append(
            {
                "class": cls,
                "confidence": round(float(box.conf), 4),
                "bbox": {
                    "x": round(x1, 1),
                    "y": round(y1, 1),
                    "w": round(x2 - x1, 1),
                    "h": round(y2 - y1, 1),
                    "cx": round(cx, 1),
                    "cy": round(cy, 1),
                },
            }
        )
    return detections, round((time.perf_counter() - t0) * 1000, 1)


@app.get("/json")
def json_endpoint():
    img = fetch_image()
    detections, took_ms = detect(img)
    return {
        "width": img.width,
        "height": img.height,
        "inference_ms": took_ms,
        "detections": detections,
    }


@app.get("/image.jpg")
def image_endpoint():
    img = fetch_image()
    detections, _ = detect(img)
    draw = ImageDraw.Draw(img)
    for d in detections:
        b = d["bbox"]
        draw.rectangle(
            [b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]],
            outline="red",
            width=3,
        )
        draw.text(
            (b["x"] + 4, b["y"] + 4),
            f"{d['class']} {d['confidence']:.2f}",
            fill="red",
        )
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return Response(content=buf.getvalue(), media_type="image/jpeg")


@app.get("/healthz")
def healthz():
    return {"ok": True}
