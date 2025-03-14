#!/usr/bin/env bash
# Exit on error
set -o errexit

# Création du dossier pour les uploads s'il n'existe pas
mkdir -p uploads

# Installation des dépendances Python
pip install -r requirements.txt

# Initialisation de la base de données uniquement si nécessaire
python << END
from app import app
from models import db, User

with app.app_context():
    # On s'assure que les tables existent
    db.create_all()
    print("Structure de la base de données vérifiée.")
    
    # On vérifie si l'administrateur existe, sinon on le crée
    admin = User.query.filter_by(username='JMA').first()
    if not admin:
        print("Création du compte administrateur...")
        admin = User(username='JMA')
        admin.set_password('ChoniqueYouche88!')
        db.session.add(admin)
        db.session.commit()
        print("Compte administrateur créé !")
    else:
        print("Le compte administrateur existe déjà.")
END

# Lancement de l'application avec Gunicorn
# --workers : nombre de processus (2 x nb de cœurs + 1)
# --timeout : temps maximum pour traiter une requête
# --access-logfile : logs des accès
# --error-logfile : logs des erreurs
exec gunicorn --workers=4 --timeout=60 --access-logfile=- --error-logfile=- --bind=:10000 wsgi:app
