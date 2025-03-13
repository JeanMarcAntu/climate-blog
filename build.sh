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
    db.create_all()
END
