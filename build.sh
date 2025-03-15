#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Début du script de build..."

# Création du dossier pour les uploads s'il n'existe pas
mkdir -p uploads
echo "Dossier uploads vérifié"

# Installation des dépendances Python
pip install -r requirements.txt
echo "Dépendances installées"

# Création du dossier d'upload dans le dossier de l'utilisateur
mkdir -p $HOME/uploads
chmod 777 $HOME/uploads

# Initialisation de la base de données et migration des fichiers
python << END
from app import app, db
from models import Document, User, Article, Tag
import os

print("Démarrage de la migration...")

with app.app_context():
    print("Suppression des tables existantes...")
    db.drop_all()
    print("Création des nouvelles tables...")
    db.create_all()
    
    # Recréation de l'utilisateur admin
    if not User.query.filter_by(username='JMA').first():
        admin = User(username='JMA')
        admin.set_password('ChoniqueYouche88!')
        db.session.add(admin)
        db.session.commit()
        print("Utilisateur admin recréé")

    print("Migration terminée avec succès !")

END

echo "Build terminé avec succès !"
