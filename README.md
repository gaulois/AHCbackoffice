---

## **Fonctionnalités Principales**

### **Gestion des Utilisateurs**
- **Créer un utilisateur** : Formulaire pour ajouter un nouvel utilisateur.
- **Lister les utilisateurs** : Affiche tous les utilisateurs avec options pour les éditer ou les supprimer.
- **Modifier un utilisateur** : Formulaire pré-rempli pour modifier un utilisateur existant.
- **Supprimer un utilisateur** : Bouton avec confirmation pour supprimer un utilisateur.

### **Gestion des Clients**
- **Créer un client** : Formulaire pour ajouter un nouveau client.
- **Lister les clients** : Affiche tous les clients avec options pour les éditer ou les supprimer.
- **Modifier un client** : Formulaire pré-rempli pour modifier un client existant.
- **Supprimer un client** : Bouton avec confirmation pour supprimer un client.

---

## **Technologies Utilisées**
- **Backend :** Flask
- **Base de Données :** MongoDB
- **Frontend :** Bootstrap 5
- **Langage :** Python

---

## **Installation et Lancement**

### 1. **Cloner le projet**
```bash
git clone https://github.com/ton-utilisateur/AHCbackoffice.git
cd AHCbackoffice

pip install -r requirements.txt

Créer un fichier .env basé sur l’exemple suivant
ENV=DEV
MONGO_USERNAME=ton_nom_utilisateur
MONGO_PASSWORD=ton_mot_de_passe
DEV_MONGO_HOST=localhost:27017
DEV_MONGO_DATABASE=AhcDB
PROD_MONGO_HOST=node1.mongodb.net
PROD_MONGO_DATABASE=AhcDB
