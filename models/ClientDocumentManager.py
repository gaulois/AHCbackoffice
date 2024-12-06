from minio import Minio
from minio.error import S3Error
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId


class ClientDocumentManager:
    def __init__(self, db):
        """
        Initialise le gestionnaire de documents client.
        :param db: Instance de la base de données MongoDB.
        """
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

    def handle_file_upload(self, client_id, file, uploaded_by):
        """
        Gère l'upload d'un fichier pour un client.
        :param client_id: ID du client.
        :param file: Fichier uploadé via un formulaire.
        :param uploaded_by: Nom ou ID de l'utilisateur ayant effectué l'upload.
        """
        if not file:
            raise ValueError("Aucun fichier reçu pour l'upload.")

        # Nettoyage du nom de fichier
        raw_filename = secure_filename(file.filename)  # Supprime les caractères spéciaux et espaces
        cleaned_filename = raw_filename.replace(" ", "_")  # Remplace les espaces restants par des underscores
        unique_filename = f"{client_id}/{datetime.utcnow().timestamp()}_{cleaned_filename}"
        #unique_filename = f"{client_id}/{cleaned_filename}"
        # Lire les données pour calculer la taille si nécessaire
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

            # Sauvegarde les métadonnées dans MongoDB
            document = {
                "clientId": client_id,
                "fileName": raw_filename,  # Conserve le nom original pour affichage
                "filePath": unique_filename,  # Utilise le chemin nettoyé pour MinIO
                "uploadDate": datetime.utcnow(),
                "uploadedBy": uploaded_by,
                "fileSize": file_size,
                "fileType": file.content_type,
            }
            self.db.clientDocuments.insert_one(document)

        except S3Error as e:
            raise ValueError(f"Erreur lors de l'upload vers MinIO : {str(e)}")

    def get_documents_by_client(self, client_id):
        """
        Récupère tous les documents associés à un client.
        :param client_id: ID du client.
        :return: Liste des documents avec des URL signées pour chaque document.
        """
        documents = list(self.db.clientDocuments.find({"clientId": client_id}))
        for document in documents:
            document["fileUrl"] = self.generate_presigned_url(document["filePath"])
        return documents

    def delete_document(self, document_id):
        """
        Supprime un document par son ID (MongoDB et MinIO).
        :param document_id: ID du document à supprimer.
        """
        document = self.db.clientDocuments.find_one({"_id": ObjectId(document_id)})
        if not document:
            raise ValueError("Document introuvable.")

        try:
            # Supprime le fichier de MinIO
            file_path = document["filePath"]
            self.minio_client.remove_object(self.bucket_name, file_path)

            # Supprime les métadonnées de MongoDB
            self.db.clientDocuments.delete_one({"_id": ObjectId(document_id)})

        except S3Error as e:
            raise ValueError(f"Erreur lors de la suppression dans MinIO : {str(e)}")

    def get_documents_by_client(self, client_id):
        """
        Récupère tous les documents associés à un client et génère des URL signées.
        """
        documents = list(self.db.clientDocuments.find({"clientId": client_id}))
        for document in documents:
            try:
                # Génère une URL signée basée sur filePath
                document["fileUrl"] = self.generate_presigned_url(document["filePath"])
            except Exception as e:
                print(f"Erreur lors de la génération de l'URL signée pour {document['filePath']}: {e}")
                document["fileUrl"] = None  # Assurez-vous que cela n'interrompt pas l'affichage
        return documents

    def generate_presigned_url(self, object_name, expiration=3600):
        """
        Génère une URL signée pour un objet dans MinIO.
        :param object_name: Le chemin de l'objet dans le bucket (sans le nom du bucket).
        :param expiration: Durée de validité de l'URL (en secondes).
        """
        try:
            # Log du chemin de l'objet avant génération de l'URL
            print(f"Génération de l'URL signée pour : {object_name}")
            # Appel à MinIO pour générer l'URL signée
            presigned_url = self.minio_client.presigned_get_object(
                bucket_name=self.bucket_name,  # Nom du bucket (client-documents)
                object_name=object_name.strip(),  # Chemin sans espace
                expires=timedelta(seconds=expiration)
            )
            print(f"URL générée : {presigned_url}")
            return presigned_url
        except S3Error as e:
            raise ValueError(f"Erreur lors de la génération du lien signé : {str(e)}")

    def get_document_by_id(self, document_id):
        """
        Récupère un document spécifique à partir de son ID et génère une URL signée.
        :param document_id: ID du document à récupérer.
        :return: Document avec une URL signée.
        """
        document = self.db.clientDocuments.find_one({"_id": ObjectId(document_id)})
        if not document:
            raise ValueError("Document introuvable.")

        # Génère une URL signée pour le document
        try:
            document["fileUrl"] = self.generate_presigned_url(document["filePath"])
        except Exception as e:
            raise ValueError(f"Erreur lors de la génération de l'URL signée pour le document : {e}")

        return document