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
from app.models import Article, User, Document, Tag

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

# Message de confirmation
echo "Configuration terminée ! Le blog est prêt à être utilisé."
