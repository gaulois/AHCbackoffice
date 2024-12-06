from datetime import datetime
from bson.objectid import ObjectId


class Client:
    def __init__(
        self,
        company_name="",
        responsible=None,
        email="",
        phone="",
        gsm="",
        vat_number="",
        billing_address=None,
        service_address=None,
        notes="",
        created_by="admin",
        modified_by="admin",
        creation_date=None,
        modification_date=None,
        client_id=None
    ):
        """Initialise un objet Client avec des valeurs par défaut."""
        self.company_name = company_name
        self.responsible = responsible or {"firstName": "", "lastName": ""}
        self.email = email
        self.phone = phone
        self.gsm = gsm
        self.vat_number = vat_number
        self.billing_address = billing_address or {
            "address": "",
            "postalCode": "",
            "city": "",
            "country": ""
        }
        self.service_address = service_address or {
            "address": "",
            "postalCode": "",
            "city": "",
            "country": ""
        }
        self.notes = notes
        self.user = {
            "createdBy": created_by,
            "modifiedBy": modified_by
        }
        self.creation_date = creation_date or datetime.utcnow()
        self.modification_date = modification_date or datetime.utcnow()
        self.client_id = ObjectId(client_id) if client_id else None

    @classmethod
    def from_form(cls, form_data, existing_client=None):
        """
        Crée un objet Client à partir des données du formulaire.
        :param form_data: Données soumises via un formulaire.
        :param existing_client: Dictionnaire client existant, utilisé pour conserver certaines métadonnées.
        """
        return cls(
            company_name=form_data.get("companyName", ""),
            responsible={
                "firstName": form_data.get("firstName", ""),
                "lastName": form_data.get("lastName", ""),
            },
            email=form_data.get("email", ""),
            phone=form_data.get("phone", ""),
            gsm=form_data.get("gsm", ""),
            vat_number=form_data.get("vatNumber", ""),
            billing_address={
                "address": form_data.get("billingAddress[address]", ""),
                "postalCode": form_data.get("billingAddress[postalCode]", ""),
                "city": form_data.get("billingAddress[city]", ""),
                "country": form_data.get("billingAddress[country]", ""),
            },
            service_address={
                "address": form_data.get("serviceAddress[address]", ""),
                "postalCode": form_data.get("serviceAddress[postalCode]", ""),
                "city": form_data.get("serviceAddress[city]", ""),
                "country": form_data.get("serviceAddress[country]", ""),
            },
            notes=form_data.get("notes", ""),
            created_by=existing_client["user"]["createdBy"] if existing_client else "admin",
            modified_by="admin",  # Remplacer par l'utilisateur connecté si nécessaire
            creation_date=existing_client.get("creationDate") if existing_client else None,
            modification_date=datetime.utcnow(),
            client_id=existing_client.get("_id") if existing_client else None
        )

    def save(self, db):
        """
        Sauvegarde le client dans la base de données.
        :param db: Instance MongoDB.
        """
        data = self.to_dict()
        if self.client_id:  # Mise à jour si l'ID existe
            db.clients.update_one({"_id": self.client_id}, {"$set": data})
        else:  # Insertion sinon
            inserted_id = db.clients.insert_one(data).inserted_id
            self.client_id = inserted_id  # Met à jour l'ID après insertion

    def to_dict(self):
        """
        Convertit l'objet en dictionnaire compatible MongoDB.
        """
        return {
            "companyName": self.company_name,
            "responsible": self.responsible,
            "email": self.email,
            "phone": self.phone,
            "gsm": self.gsm,
            "vatNumber": self.vat_number,
            "billingAddress": self.billing_address,
            "serviceAddress": self.service_address,
            "notes": self.notes,
            "user": self.user,
            "creationDate": self.creation_date,
            "modificationDate": self.modification_date,
        }

    def delete(self, db):
        """
        Supprime le client de la base de données.
        :param db: Instance MongoDB.
        :return: True si suppression réussie, False sinon.
        """
        if self.client_id:
            result = db.clients.delete_one({"_id": self.client_id})
            return result.deleted_count == 1
        raise ValueError("Impossible de supprimer : l'ID du client est manquant.")

    @classmethod
    def from_dict(cls, client_data):
        """
        Crée un objet Client à partir d'un dictionnaire MongoDB.
        :param client_data: Dictionnaire contenant les données du client.
        """
        return cls(
            company_name=client_data.get("companyName", ""),
            responsible=client_data.get("responsible", {"firstName": "", "lastName": ""}),
            email=client_data.get("email", ""),
            phone=client_data.get("phone", ""),
            gsm=client_data.get("gsm", ""),
            vat_number=client_data.get("vatNumber", ""),
            billing_address=client_data.get("billingAddress", {
                "address": "",
                "postalCode": "",
                "city": "",
                "country": ""
            }),
            service_address=client_data.get("serviceAddress", {
                "address": "",
                "postalCode": "",
                "city": "",
                "country": ""
            }),
            notes=client_data.get("notes", ""),
            created_by=client_data.get("user", {}).get("createdBy", "admin"),
            modified_by=client_data.get("user", {}).get("modifiedBy", "admin"),
            creation_date=client_data.get("creationDate", datetime.utcnow()),
            modification_date=client_data.get("modificationDate", datetime.utcnow()),
            client_id=str(client_data.get("_id")) if client_data.get("_id") else None
        )