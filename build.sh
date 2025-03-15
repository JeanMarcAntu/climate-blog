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

# Initialisation de la base de données uniquement si nécessaire
python << END
from app import app, db
from models import User, Article, Document, Tag
import sqlalchemy

print("\nDébut de l'initialisation de la base de données...")

with app.app_context():
    try:
        # On s'assure que les tables existent
        print("Création/vérification des tables...")
        db.create_all()
        print("Structure de la base de données vérifiée.")
        
        # Affichage des tables existantes
        print("\nTables dans la base de données :")
        for table in db.metadata.tables.keys():
            print(f"- {table}")
            
        # On vérifie si l'administrateur existe, sinon on le crée
        print("\nVérification du compte administrateur...")
        admin = User.query.filter_by(username='JMA').first()
        if not admin:
            print("Création du compte administrateur...")
            admin = User(username='JMA')
            admin.set_password('ChoniqueYouche88!')
            db.session.add(admin)
            db.session.commit()
            print("Compte administrateur créé avec succès !")
        else:
            print("Le compte administrateur existe déjà.")
            
        # Vérification finale
        print("\nVérification finale de la base de données :")
        admin_check = User.query.filter_by(username='JMA').first()
        if admin_check:
            print(" Compte administrateur trouvé et accessible")
        else:
            print(" ERREUR : Compte administrateur non trouvé")
            
    except Exception as e:
        print(f"\nERREUR lors de l'initialisation de la base de données :")
        print(f"Type d'erreur : {type(e).__name__}")
        print(f"Message d'erreur : {str(e)}")
        raise
END

echo "Build terminé avec succès !"
