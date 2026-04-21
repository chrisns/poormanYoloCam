# poormanYoloCam

Point it at any URL that returns a JPEG. Tell it what to look for in plain English. Get back bounding boxes.

A small HTTP service that pulls an image from an upstream URL, runs YOLO (or YOLO-World for zero-shot text-prompted detection), and returns either structured JSON or an annotated JPEG with red boxes.

No training, no Frigate, no labelling, no GPU. You run it, it points at your existing camera snapshot endpoint (Frigate snapshots, `go2rtc`, `paparazzogo`, ESPHome cameras, anything), and you get detections filtered by whatever text prompts you supply.

## Why

Frigate does real-time object detection but it's tied to a fixed set of trained classes (COCO by default, or Frigate+'s label set if you pay). Sometimes you want to ask "is there a wheelie bin on the kerb?" or "is a ladder leaning against the garage?" without training a model. YOLO-World's zero-shot text prompts let you do that in one env var.

This service wraps it in the smallest plausible HTTP API so Home Assistant, Node-RED, or a cron job can poll it.

## Endpoints

| Path | Returns |
|------|---------|
| `GET /json` | `{width, height, inference_ms, detections: [{class, confidence, bbox:{x,y,w,h,cx,cy}}, ...]}` |
| `GET /image.jpg` | Upstream image with red boxes and labels drawn on it |
| `GET /healthz` | `{ok: true}` |

Each request re-fetches the upstream image, runs inference, and returns fresh results. There is no caching — make the upstream endpoint return fast.

## Configuration

All via environment variables.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `UPSTREAM_URL` | yes | — | HTTP URL that returns a JPEG on GET |
| `MODEL_PATH` | no | baked-in `yolov8s-worldv2.pt` | Path to a `.pt` / `.onnx` model, or a name Ultralytics can auto-download |
| `WORLD_PROMPTS` | no | empty | Comma-separated text classes for YOLO-World, e.g. `wheelie bin,car,ladder`. Only makes sense with a `*-world*` model. When empty, the model's built-in classes are used. |
| `TARGET_CLASSES` | no | empty | Comma-separated whitelist of class names. Detections outside this list are dropped. Leave empty to return everything. |
| `CONF_THRESHOLD` | no | `0.4` | Minimum confidence (0–1) to return a detection |
| `FETCH_TIMEOUT` | no | `10` | HTTP timeout in seconds for pulling the upstream image |
| `MIN_CX` / `MAX_CX` | no | no limit | Restrict detections to an X-coordinate band (pixel centre) |
| `MIN_CY` / `MAX_CY` | no | no limit | Restrict detections to a Y-coordinate band (pixel centre). Useful for rejecting far-field false positives. |

## Docker

Public image: `ghcr.io/chrisns/poormanyolocam:latest`

```bash
docker run --rm -p 8000:8000 \
  -e UPSTREAM_URL=https://your-camera/snapshot.jpg \
  -e WORLD_PROMPTS="wheelie bin,car,person" \
  ghcr.io/chrisns/poormanyolocam:latest

curl http://localhost:8000/json
open http://localhost:8000/image.jpg
```

The image bakes in `yolov8s-worldv2.pt` plus the CLIP ViT-B/32 weights it depends on (~365MB) so the container starts with no network calls. If you set `MODEL_PATH` to a different model name, Ultralytics will download it on first request.

## Kubernetes

See [`examples/k8s/`](examples/k8s) for a minimal Deployment + Service.

```bash
kubectl apply -k examples/k8s/
```

Edit `examples/k8s/deployment.yaml` to set `UPSTREAM_URL` to wherever your camera snapshot lives. In-cluster DNS works fine (`http://my-camera-proxy.my-ns.svc/snapshot.jpg`).

## Local development

Requires Python 3.12.

```bash
make install
make dev UPSTREAM_URL=https://your-camera/snapshot.jpg
curl http://localhost:8000/json
```

First call downloads the model (~25MB) + CLIP (~338MB) into `./` — subsequent calls are fast.

## Performance

On CPU (Apple M-series, modern Intel/AMD): **~60–100ms per frame** with `yolov8s-worldv2.pt`. First call after startup is slower (~200ms) while the graph warms up. Memory footprint ~1GB resident.

For faster or more accurate inference, swap `MODEL_PATH` to `yolov8n-world.pt` (smaller, faster) or `yolov8l-worldv2.pt` / `yolov8x-worldv2.pt` (bigger, slower, better accuracy).

## Accuracy is not magic

YOLO-World is astonishing *when* the target object looks vaguely like something in its training distribution. It gives you a zero-effort baseline. It will occasionally false-positive on things that kind-of-look-like your prompt — dogs labelled as lions, bollards labelled as wheelie bins, etc. Mitigations in order of effort:

1. **Raise `CONF_THRESHOLD`** (start at 0.4, try 0.6).
2. **Use `MIN_CY` / `MAX_CY` / `MIN_CX` / `MAX_CX`** to restrict detections to plausible regions of the frame.
3. **Tune prompts**: `"plastic wheelie bin"` often works better than `"bin"`.
4. If none of that is good enough: label 100–200 of your own frames, train YOLOv8 on them (~30 min on a free Colab T4), then point `MODEL_PATH` at the resulting `.pt`. `WORLD_PROMPTS` stops being relevant once you have a trained model.

## License

MIT. See [LICENSE](LICENSE).
