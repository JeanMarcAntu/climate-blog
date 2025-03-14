#!/usr/bin/env bash
# Exit on error
set -o errexit

# Création du dossier pour les uploads s'il n'existe pas
mkdir -p uploads

# Installation des dépendances Python
pip install -r requirements.txt

# Initialisation de la base de données
python << END
from app import app, db
with app.app_context():
    print("Création des tables dans la base de données...")
    db.create_all()
    print("Base de données initialisée avec succès !")
END

# Message de confirmation
echo "Configuration terminée ! Le blog est prêt à être utilisé."
