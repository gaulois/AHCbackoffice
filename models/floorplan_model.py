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

    def add_floorplan(self, client_id, file, name, description, uploaded_by):
        """
        Ajoute un nouveau plan d'étage pour un client, gérant à la fois l'upload et l'enregistrement des métadonnées.

        :param client_id: ID du client.
        :param file: Fichier du plan d'étage uploadé via un formulaire.
        :param name: Nom du plan d'étage.
        :param description: Description du plan d'étage.
        :param uploaded_by: Nom ou ID de l'utilisateur ayant effectué l'upload.
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
                "imageUrl": unique_filename,
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