# One container = Flask UI + API + InsightFace + SQLite.  (InsightFace/onnxruntime + model are too big for Vercel serverless.)
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 poppler-utils && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Download the buffalo_s model (SCRFD + ArcFace) at build time so first request is fast. Needs internet during build.
RUN python -c "from insightface.app import FaceAnalysis; a=FaceAnalysis(name='buffalo_s',providers=['CPUExecutionProvider'],allowed_modules=['detection','recognition']); a.prepare(ctx_id=-1,det_size=(320,320))"
COPY app ./app
COPY scripts ./scripts
COPY wsgi.py .
# demo_assets/ is PRIVATE (LFW-derived, git-ignored): build this image from a local folder that contains it.
COPY demo_assets ./demo_assets
ENV DATA_DIR=/data ASSET_DIR=/srv/demo_assets
VOLUME /data
EXPOSE 8000
# 1 worker so the model is loaded once; threads serve concurrent requests (AI runs in a background thread per session).
CMD ["sh","-c","gunicorn -w 1 --threads 2 -t 300 -b 0.0.0.0:${PORT} wsgi:app"]
