from datetime import datetime

class Client:
    def __init__(self, company_name, responsible, email, phone, gsm, vat_number, billing_address, service_address, notes=None, created_by="admin", modified_by="admin", creation_date=None, modification_date=None, client_id=None):
        self.company_name = company_name
        self.responsible = responsible
        self.email = email
        self.phone = phone
        self.gsm = gsm
        self.vat_number = vat_number
        self.billing_address = billing_address
        self.service_address = service_address
        self.notes = notes
        self.user = {
            "createdBy": created_by,
            "modifiedBy": modified_by
        }
        self.creation_date = creation_date or datetime.utcnow()
        self.modification_date = modification_date or datetime.utcnow()
        self.client_id = client_id  # ID du client pour les mises à jour

    @classmethod
    def from_form(cls, form_data, existing_client=None):
        """Crée un objet Client à partir des données du formulaire."""
        return cls(
            company_name=form_data.get("companyName"),
            responsible={
                "firstName": form_data.get("firstName"),
                "lastName": form_data.get("lastName"),
            },
            email=form_data.get("email"),
            phone=form_data.get("phone"),
            gsm=form_data.get("gsm"),
            vat_number=form_data.get("vatNumber"),
            billing_address={
                "address": form_data.get("billingAddress[address]"),
                "postalCode": form_data.get("billingAddress[postalCode]"),
                "city": form_data.get("billingAddress[city]"),
                "country": form_data.get("billingAddress[country]"),
            },
            service_address={
                "address": form_data.get("serviceAddress[address]"),
                "postalCode": form_data.get("serviceAddress[postalCode]"),
                "city": form_data.get("serviceAddress[city]"),
                "country": form_data.get("serviceAddress[country]"),
            },
            notes=form_data.get("notes"),
            created_by=existing_client["user"]["createdBy"] if existing_client else "admin",
            modified_by="admin",  # Remplacer par l'utilisateur connecté si géré
            creation_date=existing_client["creationDate"] if existing_client else None,
            modification_date=datetime.utcnow(),
            client_id=existing_client["_id"] if existing_client else None
        )

    def save(self, db):
        """Sauvegarde le client dans la base de données."""
        data = self.to_dict()
        if self.client_id:  # Mise à jour si l'ID existe
            db.clients.update_one({"_id": self.client_id}, {"$set": data})
        else:  # Insertion sinon
            db.clients.insert_one(data)

    def to_dict(self):
        """Convertit l'objet en dictionnaire compatible MongoDB."""
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
        """Supprime le client de la base de données."""
        if self.client_id:
            result = db.clients.delete_one({"_id": self.client_id})
            return result.deleted_count == 1  # Retourne True si supprimé, False sinon
        raise ValueError("Impossible de supprimer : l'ID du client est manquant.")