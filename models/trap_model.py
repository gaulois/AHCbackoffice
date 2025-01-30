from bson.objectid import ObjectId
from datetime import datetime
from zoneinfo import ZoneInfo

class TrapModel:
    def __init__(self, db):
        self.db = db

    def add_trap(self, plan_id, trap_data):
        """
        Ajoute un piège à un plan d'étage donné.
        """
        trap = {
            "planId": ObjectId(plan_id),
            "type": trap_data.get("type"),
            "label": trap_data.get("label"),
            "location": trap_data.get("location"),
            "coordinates": trap_data.get("coordinates"),
            "barcode": trap_data.get("barcode"),
            "dateAdded": datetime.now(ZoneInfo("Europe/Paris"))
        }
        return self.db.traps.insert_one(trap)

    def get_traps_by_plan(self, plan_id):
        """
        Récupère tous les pièges associés à un plan d'étage.
        :param plan_id: ID du plan d'étage.
        :return: Liste des pièges associés.
        """
        return list(self.db.traps.find({"planId": ObjectId(plan_id)}))

    def delete_trap(self, trap_id):
        """
        Supprime un piège par son ID.
        """
        return self.db.traps.delete_one({"_id": ObjectId(trap_id)})