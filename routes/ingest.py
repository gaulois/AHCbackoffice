from flask import Blueprint, render_template, request, jsonify, current_app, abort, redirect, url_for
import os, io, re, mimetypes
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from minio import Minio
from pdf2image import convert_from_bytes
from PIL import Image
import cv2
import numpy as np
import pytesseract
from PyPDF2 import PdfReader

ingest_bp = Blueprint("ingest", __name__)

# ----- MinIO client (depuis .env) -----
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:9000")
ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "client-documents")

p = urlparse(ENDPOINT_URL if "://" in ENDPOINT_URL else f"http://{ENDPOINT_URL}")
endpoint = p.netloc or p.path
secure = (p.scheme == "https")

minio_client = Minio(
    endpoint,
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    secure=secure,
)

# ----- Helpers -----
def _now_ts():
    return f"{datetime.now().timestamp():.0f}"

def parse_client_id_from_qr(text: str) -> str | None:
    """
    Exemples acceptés:
      - https://app.ahc-digital.com/api/upload_doc?client_ref=<id>
      - ...?client_ref=<id>&...
      - <id> (pur)
    """
    try:
        # essaie URL + query param client_ref
        if text.startswith("http://") or text.startswith("https://"):
            qs = parse_qs(urlparse(text).query)
            cid = qs.get("client_ref", [None])[0]
            if cid:
                return cid
        # sinon, tente un ID brut (hexa/uuid court)
        if re.fullmatch(r"[0-9a-fA-F]{8,64}", text) or re.fullmatch(r"[0-9a-fA-F-]{8,}", text):
            return text
    except Exception:
        pass
    return None

def extract_qr_client_id_from_pdf(pdf_bytes: bytes) -> tuple[str | None, str | None]:
    """
    Convertit la 1ère page en image, tente de décoder un QR via OpenCV.
    Retourne (client_id, qr_raw) ou (None, None).
    """
    try:
        # Convertir la première page du PDF en image
        pages = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, fmt="png")
        if not pages:
            return None, None

        page: Image.Image = pages[0]

        # PIL -> numpy -> BGR pour OpenCV
        img = np.array(page)              # RGB
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(img_bgr)

        if data:
            raw = data.strip()
            cid = parse_client_id_from_qr(raw)
            if cid:
                return cid, raw
            else:
                # QR lisible mais contenu non exploitable pour retrouver un client
                return None, raw

        return None, None
    except Exception:
        return None, None

def put_minio_object(key: str, data: bytes, content_type: str = "application/pdf"):
    bio = io.BytesIO(data)
    bio.seek(0, io.SEEK_END)
    length = bio.tell()
    bio.seek(0)
    minio_client.put_object(
        bucket_name=BUCKET_NAME,
        object_name=key,
        data=bio,
        length=length,
        content_type=content_type,
    )

def presign_get(key: str, disposition_filename: str | None = None) -> str:
    headers = {}
    if disposition_filename:
        headers["response-content-disposition"] = f'attachment; filename="{disposition_filename}"'
        # optionnel : type deviné
        guessed = mimetypes.guess_type(disposition_filename)[0] or "application/pdf"
        headers["response-content-type"] = guessed
    return minio_client.get_presigned_url(
        "GET",
        bucket_name=BUCKET_NAME,
        object_name=key,
        expires=timedelta(minutes=10),
        response_headers=headers or None,
    )

# ----- Routes -----
@ingest_bp.route("/quick_ingest", methods=["GET"])
def quick_ingest():
    return render_template("quick_ingest.html")

@ingest_bp.route("/api/ingest_docs", methods=["POST"])
def api_ingest_docs():
    """
    Reçoit des PDF scannés (files[]).
    Lit le QR pour trouver clientId et range le fichier directement
    dans client-documents/<clientId>/scans/...
    docType est forcé à 'intervention'.
    Les fichiers sans QR vont en unassigned/ pour tri manuel.
    """
    if "files" not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    db = current_app.config["MONGO_DB"]
    files = request.files.getlist("files")
    results = []

    for f in files:
        name = f.filename or "scan.pdf"
        if not name.lower().endswith(".pdf"):
            results.append({"file": name, "status": "error", "message": "Seuls les PDF sont acceptés"})
            continue

        pdf_bytes = f.read()
        client_id, qr_raw = extract_qr_client_id_from_pdf(pdf_bytes)
        date_info = extract_intervention_date_from_pdf(pdf_bytes)
        intervention_date = date_info.get("interventionDate")
        date_source = date_info.get("source")
        print("Date trouvée :", intervention_date)
        print("Source date  :", date_source)
        if client_id:
            key = f"documents/{client_id}/interventions/scans/{_now_ts()}_{name.replace(' ', '_')}"
            try:
                put_minio_object(key, pdf_bytes, "application/pdf")
                db.clientDocuments.insert_one({
                    "clientId": client_id,
                    "fileName": name,
                    "objectPath": key,
                    "filePath": key,
                    "documentType": "intervention",
                    "uploadedBy": "quick_ingest",  # adapte si tu as l'user en session
                    "uploadDate": datetime.now(),
                    "interventionDate": intervention_date,
                    "interventionDateSource": date_source,
                    "source": "scan",
                    "status": "ok",
                    "qrRaw": qr_raw
                })
                results.append({"file": name, "status": "ok", "clientId": client_id})
            except Exception as e:
                results.append({"file": name, "status": "error", "message": f"Upload/DB: {e}"})
        else:
            # pas de QR → parking unassigned
            key = f"documents/unassigned/{_now_ts()}_{name.replace(' ', '_')}"
            try:
                put_minio_object(key, pdf_bytes, "application/pdf")
                doc_id = db.clientDocuments.insert_one({
                    "clientId": None,
                    "fileName": name,
                    "objectPath": key,
                    "filePath": key,
                    "documentType": "intervention",
                    "uploadedBy": "quick_ingest",
                    "uploadDate": datetime.now(),
                    "interventionDate": intervention_date,
                    "interventionDateSource": date_source,
                    "source": "scan",
                    "status": "unassigned",
                    "qrRaw": qr_raw
                }).inserted_id
                results.append({"file": name, "status": "unassigned", "docId": str(doc_id)})
            except Exception as e:
                results.append({"file": name, "status": "error", "message": f"Upload/DB: {e}"})

    return jsonify({"results": results})

@ingest_bp.route("/api/assign_doc", methods=["PATCH"])
def api_assign_doc():
    """
    Assigne un PDF 'unassigned' à un client choisi.
    Déplace l'objet MinIO dans le bon répertoire et met à jour Mongo.
    Body JSON: { "docId": "...", "clientId": "..." }
    """
    from bson import ObjectId

    data = request.get_json(silent=True) or {}
    doc_id = data.get("docId")
    client_id = data.get("clientId")
    if not doc_id or not client_id:
        return jsonify({"error": "docId et clientId requis"}), 400

    db = current_app.config["MONGO_DB"]
    doc = db.clientDocuments.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        return jsonify({"error": "Document introuvable"}), 404
    if doc.get("status") != "unassigned":
        return jsonify({"error": "Document déjà assigné"}), 400

    src_key = doc["objectPath"]
    filename = doc.get("fileName") or os.path.basename(src_key)
    dst_key = f"documents/{client_id}/interventions/scans/{_now_ts()}_{filename.replace(' ', '_')}"

    # copie + suppression (faute de "move" natif S3)
    try:
        # copie
        minio_client.copy_object(BUCKET_NAME, dst_key, f"/{BUCKET_NAME}/{src_key}")
        # suppression source
        minio_client.remove_object(BUCKET_NAME, src_key)
        # MAJ Mongo
        db.clientDocuments.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "clientId": client_id,
                "objectPath": dst_key,
                "status": "ok",
            }}
        )
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": f"Move failed: {e}"}), 500

def extract_date_from_text(text: str) -> str | None:
    """
    Cherche une date dans différents formats et la renvoie au format YYYY-MM-DD.
    """
    if not text:
        return None

    patterns = [
        r"\b(\d{2}/\d{2}/\d{4})\b",
        r"\b(\d{2}-\d{2}-\d{4})\b",
        r"\b(\d{4}-\d{2}-\d{2})\b",
        r"\b(\d{2}/\d{2}/\d{2})\b",
        r"\b(\d{2}-\d{2}-\d{2})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            raw = match.group(1)

            # Essais de parsing selon plusieurs formats
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
                try:
                    dt = datetime.strptime(raw, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass

    return None

def extract_intervention_date_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Cherche la date d'intervention dans un PDF.
    1. Tente d'abord une extraction texte native
    2. Si échec, considère que c'est un scan et fait OCR sur la première page
    """
    # --- Étape 1 : extraction texte native ---
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        extracted_text = ""

        for page in reader.pages[:2]:
            page_text = page.extract_text()
            if page_text:
                extracted_text += "\n" + page_text

        extracted_text = extracted_text.strip()

        if extracted_text and len(extracted_text) > 20:
            found_date = extract_date_from_text(extracted_text)
            if found_date:
                return {
                    "interventionDate": found_date,
                    "source": "pdf_text",
                    "rawText": extracted_text
                }
    except Exception as e:
        print("Erreur extraction texte PDF :", e)

    # --- Étape 2 : OCR sur image si PDF scanné ---
    try:
        pages = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, fmt="png")
        print("Nombre de pages converties OCR :", len(pages))

        if not pages:
            return {
                "interventionDate": None,
                "source": "none",
                "rawText": ""
            }

        page: Image.Image = pages[0]

        ocr_text = pytesseract.image_to_string(page, lang="fra")
        ocr_text = ocr_text.strip()

        print("Texte OCR extrait :")
        print(ocr_text[:1000])

        found_date = extract_date_from_text(ocr_text)

        return {
            "interventionDate": found_date,
            "source": "ocr",
            "rawText": ocr_text
        }

    except Exception as e:
        print("Erreur OCR :", e)
        return {
            "interventionDate": None,
            "source": "none",
            "rawText": ""
        }