from minio import Minio
from minio.error import S3Error
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from zoneinfo import ZoneInfo
import qrcode
import io
from models.utils.word_utils import add_qr_to_word
from qrcode.image.pil import PilImage

class FloorPlanModel:
    def __init__(self, db):
        self.db = db
        self.db = db
        self.minio_client = Minio(
            endpoint=os.getenv("AWS_ENDPOINT_URL").replace("http://", ""),
            access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            secure=False  # Désactive SSL pour un environnement local
        )
        self.bucket_name = os.getenv("AWS_BUCKET_NAME")

        # Vérifie si le bucket existe, sinon le crée
        if not self.minio_client.bucket_exists(self.bucket_name):
            self.minio_client.make_bucket(self.bucket_name)

    def get_signed_url(self, object_name):
        """
        Génère une URL signée temporaire pour accéder à un fichier MinIO.
        :param object_name: Chemin du fichier dans MinIO
        :return: URL signée temporaire
        """
        try:
            return self.minio_client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(hours=1)  # URL valable 1 heure
            )
        except S3Error as e:
            print(f"Erreur MinIO : {e}")
            return None

    def add_floorplan(self, client_id, name, description, file, uploaded_by):
        """
        Ajoute un plan (PDF, image ou Word) pour un client.
        Si le fichier est un Word, le QR code est automatiquement inséré en haut du document.
        """
        if not file:
            raise ValueError("Aucun fichier reçu pour le plan d'étage.")

        # ✅ Autoriser plusieurs formats
        ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Extension de fichier non autorisée : {ext}")

        # Nettoyage du nom du fichier
        raw_filename = secure_filename(file.filename)
        cleaned_filename = raw_filename.replace(" ", "_")
        unique_filename = f"floorplans/{client_id}/{datetime.now(ZoneInfo('Europe/Paris')).timestamp()}_{cleaned_filename}"

        # Lire les données pour calculer la taille
        file_data = file.stream.read()
        file_size = len(file_data) if file.content_length == 0 else file.content_length
        file.stream.seek(0)  # Réinitialise le flux

        # ✅ Génération automatique du QR code
        qr_url = f"https://app.ahc-digital.com/api/upload_doc?client_ref={client_id}"
        qr_img = qrcode.make(qr_url, image_factory=PilImage)
        qr_bytes = io.BytesIO()
        qr_img.save(qr_bytes, format='PNG')
        qr_bytes.seek(0)

        # ✅ Stockage du QR code dans MinIO
        qr_path = f"qrcodes/{client_id}/{datetime.now(ZoneInfo('Europe/Paris')).timestamp()}_qr.png"
        self.minio_client.put_object(
            bucket_name=self.bucket_name,
            object_name=qr_path,
            data=qr_bytes,
            length=len(qr_bytes.getvalue()),
            content_type="image/png",
        )

        # ✅ Si le fichier est un Word, insérer le QR dans le document
        try:
            if ext in {"doc", "docx"}:
                file.stream.seek(0)
                word_with_qr = add_qr_to_word(file.stream, qr_bytes, client_id)
                file_to_upload = word_with_qr
                upload_length = len(word_with_qr.getvalue())
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else:
                file_to_upload = io.BytesIO(file_data)
                upload_length = file_size
                content_type = file.content_type

            # ✅ Upload du fichier dans MinIO (Word modifié ou original)
            self.minio_client.put_object(
                bucket_name=self.bucket_name,
                object_name=unique_filename,
                data=file_to_upload,
                length=upload_length,
                content_type=content_type,
            )

            # ✅ Enregistrement dans MongoDB
            floorplan = {
                "clientId": client_id,
                "name": name,
                "description": description,
                "imagePath": unique_filename,
                "qrCodePath": qr_path,
                "uploadDate": datetime.now(ZoneInfo("Europe/Paris")),
                "uploadedBy": uploaded_by,
                "fileName": raw_filename,
                "fileSize": upload_length,
                "fileType": content_type,
            }

            return self.db.floorPlans.insert_one(floorplan)

        except S3Error as e:
            raise ValueError(f"Erreur lors de l'upload du plan vers MinIO : {str(e)}")
    def edit_floorplan(self, plan_id, name, description):
        """Modifie un plan d'étage existant."""
        return self.db.floorPlans.update_one(
            {"_id": ObjectId(plan_id)},
            {"$set": {"name": name, "description": description}}
        )

    def get_floorplan(self, plan_id):
        """Récupère un plan d'étage par son ID."""
        return self.db.floorPlans.find_one({"_id": ObjectId(plan_id)})