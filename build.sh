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
from models import db, User, Article, Document, Tag

with app.app_context():
    try:
        # On s'assure que les tables existent
        db.create_all()
        print("Structure de la base de données vérifiée.")
        
        # Affichage des tables existantes
        print("\nTables dans la base de données :")
        for table in db.metadata.tables.keys():
            print(f"- {table}")
            
        # On vérifie si l'administrateur existe, sinon on le crée
        admin = User.query.filter_by(username='JMA').first()
        if not admin:
            print("\nCréation du compte administrateur...")
            admin = User(username='JMA')
            admin.set_password('ChoniqueYouche88!')
            db.session.add(admin)
            db.session.commit()
            print("Compte administrateur créé !")
        else:
            print("\nLe compte administrateur existe déjà.")
            
    except Exception as e:
        print(f"\nErreur lors de l'initialisation de la base de données : {e}")
        raise
END

# Lancement de l'application avec Gunicorn en utilisant le fichier de configuration
exec gunicorn -c gunicorn.conf.py wsgi:app
