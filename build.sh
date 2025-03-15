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
import sqlalchemy as sa
from sqlalchemy import inspect

print("Démarrage de la migration...")

with app.app_context():
    # Vérification de l'existence des tables
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    if 'document' not in tables:
        print("Création initiale des tables...")
        db.create_all()
    else:
        print("Ajout des nouvelles colonnes...")
        # Ajout des colonnes si elles n'existent pas
        columns = [c['name'] for c in inspector.get_columns('document')]
        with db.engine.connect() as conn:
            if 'file_content' not in columns:
                conn.execute(sa.text('ALTER TABLE document ADD COLUMN file_content BYTEA'))
            if 'file_type' not in columns:
                conn.execute(sa.text('ALTER TABLE document ADD COLUMN file_type VARCHAR(50)'))
            conn.commit()
    
    # Vérification/création du compte admin
    if not User.query.filter_by(username='JMA').first():
        print("Création du compte administrateur...")
        admin = User(username='JMA')
        admin.set_password('ChoniqueYouche88!')
        db.session.add(admin)
        db.session.commit()
        print("Compte administrateur créé !")
    
    # Migration des fichiers existants
    print("Migration des fichiers...")
    documents = Document.query.all()
    for document in documents:
        if document.file_content is None:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        document.file_content = f.read()
                        document.file_type = 'application/pdf'  # Par défaut pour les anciens fichiers
                        print(f"Migration réussie : {document.filename}")
                except Exception as e:
                    print(f"Erreur lors de la migration de {document.filename}: {str(e)}")
    
    try:
        db.session.commit()
        print("Migration terminée avec succès !")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde : {str(e)}")
        db.session.rollback()
        raise

END

echo "Build terminé avec succès !"
