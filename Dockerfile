FROM python:3.14-slim@sha256:a7fb1e634c4a578f9e0bd6327f11a3cde11b7a9395f48e24360c0988bcc5c2bc

ARG YOLO_MODEL=yolov8s-worldv2.pt

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

RUN python -c "from ultralytics import YOLO; m = YOLO('${YOLO_MODEL}'); \
    ('world' in '${YOLO_MODEL}') and m.set_classes(['warmup'])" \
 && mv "${YOLO_MODEL}" "/models/${YOLO_MODEL}" 2>/dev/null || mkdir -p /models && mv "${YOLO_MODEL}" "/models/${YOLO_MODEL}"

COPY app/ ./app/

ENV MODEL_PATH=/models/${YOLO_MODEL} \
    CONF_THRESHOLD=0.4

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
