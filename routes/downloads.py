# routes/downloads.py
import os
from datetime import timedelta
from urllib.parse import urlparse
from flask import Blueprint, request, redirect, abort
from minio import Minio

downloads_bp = Blueprint("downloads", __name__)

# ---- MinIO client autonome (lit .env) ----
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:9000")
ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "client-documents")

# Parse l'endpoint (gère http(s)://host:port et aussi host:port)
p = urlparse(ENDPOINT_URL if "://" in ENDPOINT_URL else f"http://{ENDPOINT_URL}")
endpoint = p.netloc or p.path  # ex: "minio.ahc-digital.com:9000" ou "localhost:9000"
secure = (p.scheme == "https")

minio_client = Minio(
    endpoint,
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    secure=secure,
)

@downloads_bp.route("/download_floorplan")
def download_floorplan():
    """
    Génère une URL pré-signée propre (avec Content-Disposition) et redirige.
    Paramètres:
      - key: clé de l'objet (ex: floorplans/<client_id>/.../file.docx)
      - name: nom proposé au téléchargement (facultatif)
    """
    key = request.args.get("key")
    filename = request.args.get("name")

    if not key:
        return abort(400, "Missing 'key' (object path in bucket)")

    if not filename:
        # Nom par défaut : le nom du fichier dans la clé
        filename = os.path.basename(key)

    try:
        url = minio_client.get_presigned_url(
            "GET",
            bucket_name=BUCKET_NAME,
            object_name=key,
            expires=timedelta(minutes=10),
            response_headers={
                # Force le téléchargement avec un nom propre
                "response-content-disposition": f'attachment; filename="{filename}"'
            },
        )
        return redirect(url)
    except Exception as e:
        return abort(500, f"Presign error: {e}")