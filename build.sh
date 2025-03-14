#!/usr/bin/env bash
# Exit on error
set -o errexit

# Création du dossier pour les uploads s'il n'existe pas
mkdir -p uploads

# Installation des dépendances Python
pip install -r requirements.txt

# Initialisation de la base de données uniquement si nécessaire
python << END
from app import app, db
from app.models import Article  # Importation du modèle Article

with app.app_context():
    # Vérifie si les tables existent déjà
    if not Article.query.first():
        print("Aucun article trouvé - Création des tables dans la base de données...")
        db.create_all()
        print("Base de données initialisée avec succès !")
    else:
        print("Base de données déjà initialisée - Conservation des données existantes")
END

# Création du compte administrateur
python init_admin.py

# Message de confirmation
echo "Configuration terminée ! Le blog est prêt à être utilisé."
