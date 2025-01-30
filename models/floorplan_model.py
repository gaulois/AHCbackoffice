from minio import Minio
from minio.error import S3Error
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from zoneinfo import ZoneInfo


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

    def add_floorplan(self, client_id, file, name, description, uploaded_by):
        """
        Ajoute un nouveau plan d'étage pour un client et stocke seulement le chemin du fichier.
        """
        if not file:
            raise ValueError("Aucun fichier reçu pour le plan d'étage.")

        # Nettoyage et préparation du nom de fichier
        raw_filename = secure_filename(file.filename)
        cleaned_filename = raw_filename.replace(" ", "_")
        unique_filename = f"floorplans/{client_id}/{datetime.now(ZoneInfo('Europe/Paris')).timestamp()}_{cleaned_filename}"

        # Lire les données pour calculer la taille
        file_data = file.stream.read()
        file_size = len(file_data) if file.content_length == 0 else file.content_length

        # Réinitialiser le flux avant l'upload
        file.stream.seek(0)

        try:
            # Upload du fichier dans MinIO
            self.minio_client.put_object(
                bucket_name=self.bucket_name,
                object_name=unique_filename,
                data=file.stream,
                length=file_size,
                content_type=file.content_type,
            )

            # Enregistrement des métadonnées dans MongoDB
            floorplan = {
                "clientId": client_id,
                "name": name,
                "description": description,
                "imagePath": unique_filename,  #  Stocke seulement le chemin
                "uploadDate": datetime.now(ZoneInfo("Europe/Paris")),
                "uploadedBy": uploaded_by,
                "fileName": raw_filename,
                "fileSize": file_size,
                "fileType": file.content_type,
            }

            return self.db.floorPlans.insert_one(floorplan)

        except S3Error as e:
            raise ValueError(f"Erreur lors de l'upload du plan d'étage vers MinIO : {str(e)}")
    def edit_floorplan(self, plan_id, name, description):
        """Modifie un plan d'étage existant."""
        return self.db.floorPlans.update_one(
            {"_id": ObjectId(plan_id)},
            {"$set": {"name": name, "description": description}}
        )

    def get_floorplan(self, plan_id):
        """Récupère un plan d'étage par son ID."""
        return self.db.floorPlans.find_one({"_id": ObjectId(plan_id)})