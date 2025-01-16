from datetime import datetime
from bson.objectid import ObjectId
from zoneinfo import ZoneInfo

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
            contract_type="",
            contract_number="",
            entity="",
            info_scan_ctr="",
            contract_start_date=None,
            contract_duration=None,
            accounting_emails=None,
            nb_prestations=0,  # Nouveau champ
            planning_info="",  # Nouveau champ
            email_before_service=False,  # Nouveau champ
            created_by="admin",
            modified_by="admin",
            creation_date=None,
            modification_date=None,
            client_id=None
    ):
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
            "country": "",
            "treatmentPlaceName": ""
        }
        self.notes = notes
        self.contract_type = contract_type
        self.contract_number = contract_number
        self.entity = entity
        self.info_scan_ctr = info_scan_ctr
        self.contract_start_date = contract_start_date
        self.contract_duration = contract_duration
        self.accounting_emails = accounting_emails or []
        self.nb_prestations = nb_prestations
        self.planning_info = planning_info
        self.email_before_service = email_before_service
        self.user = {
            "createdBy": created_by,
            "modifiedBy": modified_by
        }
        self.creation_date = creation_date or datetime.now(ZoneInfo("Europe/Paris"))
        self.modification_date = modification_date or datetime.now(ZoneInfo("Europe/Paris"))
        self.client_id = ObjectId(client_id) if client_id else None

    def to_dict(self):
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
            "contractType": self.contract_type,
            "contractNumber": self.contract_number,
            "entity": self.entity,
            "infoScanCtr": self.info_scan_ctr,
            "contractStartDate": self.contract_start_date,
            "contractDuration": self.contract_duration,
            "accountingEmails": self.accounting_emails,
            "nbPrestations": self.nb_prestations,
            "planningInfo": self.planning_info,
            "emailBeforeService": self.email_before_service,
            "user": self.user,
            "creationDate": self.creation_date,
            "modificationDate": self.modification_date,
        }

    @classmethod
    def from_form(cls, form_data, existing_client=None):
        """
        Crée un objet Client à partir des données du formulaire.
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
                "treatmentPlaceName": form_data.get("serviceAddress[treatmentPlaceName]", "")  #
            },
            notes=form_data.get("notes", ""),
            contract_type=form_data.get("contractType", ""),
            contract_number=form_data.get("contractNumber", ""),
            entity=form_data.get("entity", ""),
            info_scan_ctr=form_data.get("infoScanCtr", ""),
            contract_start_date=form_data.get("contractStartDate", ""),
            contract_duration=form_data.get("contractDuration", ""),
            accounting_emails=form_data.get("accountingEmails", "").split(","),
            nb_prestations=int(form_data.get("nbPrestations", 0)) if form_data.get("nbPrestations") else 0,
            # Ajout de vérification
            planning_info=form_data.get("planningInfo", ""),
            email_before_service=form_data.get("emailBeforeService") == "on",  # Vérifie si la case est cochée
            created_by=existing_client["user"]["createdBy"] if existing_client else "admin",
            modified_by="admin",  # Remplacer par l'utilisateur connecté si nécessaire
            creation_date=existing_client.get("creationDate") if existing_client else None,
            modification_date=datetime.now(ZoneInfo("Europe/Paris")),
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