import os
import jwt
from flask import Blueprint, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

onlyoffice_bp = Blueprint('onlyoffice', __name__)

ONLYOFFICE_JWT_SECRET = os.getenv("ONLYOFFICE_JWT_SECRET")
ONLYOFFICE_URL = os.getenv("ONLYOFFICE_URL", "https://docs.ahc-digital.com")

@onlyoffice_bp.route("/view_doc")
def view_doc():
    file_url = request.args.get("file_url")
    file_name = request.args.get("file_name", "document.docx")

    if not file_url:
        return "URL du document manquante", 400

    # 🔐 Création du token JWT attendu par OnlyOffice
    payload = {
        "document": {
            "fileType": file_name.split('.')[-1],
            "title": file_name,
            "url": file_url
        },
        "editorConfig": {
            "mode": "edit",
            "callbackUrl": file_url
        }
    }

    token = jwt.encode(payload, ONLYOFFICE_JWT_SECRET, algorithm="HS256")

    # 🔧 Prépare la config du viewer OnlyOffice
    config = {
        "document": payload["document"],
        "editorConfig": payload["editorConfig"],
        "token": token
    }

    return render_template("onlyoffice_viewer.html", config=config, onlyoffice_url=ONLYOFFICE_URL)