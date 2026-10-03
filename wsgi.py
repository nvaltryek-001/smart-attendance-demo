"""Entry point.  Local:  python wsgi.py     Production:  gunicorn -w 1 --threads 8 -t 300 wsgi:app"""
import os
from app import create_app
app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)
