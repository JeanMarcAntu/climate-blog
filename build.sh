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
import json
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import inspect

print("Démarrage de la migration...")

def serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

with app.app_context():
    # Sauvegarde des données existantes
    print("Sauvegarde des données existantes...")
    data = {
        'documents': [],
        'articles': [],
        'tags': []
    }
    
    # Sauvegarde des tags
    for tag in Tag.query.all():
        data['tags'].append({
            'id': tag.id,
            'name': tag.name
        })
    
    # Sauvegarde des documents
    for doc in Document.query.all():
        data['documents'].append({
            'id': doc.id,
            'filename': doc.filename,
            'original_filename': doc.original_filename,
            'title': doc.title,
            'author': doc.author,
            'year': doc.year,
            'description': doc.description,
            'upload_date': doc.upload_date,
            'tag_names': [tag.name for tag in doc.tags]
        })
    
    # Sauvegarde des articles
    for article in Article.query.all():
        data['articles'].append({
            'id': article.id,
            'title': article.title,
            'content': article.content,
            'created_date': article.created_date
        })
    
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
    
    # Restauration des données
    print("Restauration des données...")
    
    # Restauration des tags
    for tag_data in data['tags']:
        if not Tag.query.get(tag_data['id']):
            tag = Tag(name=tag_data['name'])
            db.session.add(tag)
    db.session.commit()
    
    # Restauration des articles
    for article_data in data['articles']:
        if not Article.query.get(article_data['id']):
            article = Article(
                title=article_data['title'],
                content=article_data['content'],
                created_date=datetime.fromisoformat(article_data['created_date'])
            )
            db.session.add(article)
    db.session.commit()
    
    # Restauration des documents
    for doc_data in data['documents']:
        if not Document.query.get(doc_data['id']):
            # Récupération des tags
            tags = []
            for tag_name in doc_data['tag_names']:
                tag = Tag.query.filter_by(name=tag_name).first()
                if tag:
                    tags.append(tag)
            
            # Création du document
            doc = Document(
                filename=doc_data['filename'],
                original_filename=doc_data['original_filename'],
                title=doc_data['title'],
                author=doc_data['author'],
                year=doc_data['year'],
                description=doc_data['description'],
                upload_date=datetime.fromisoformat(doc_data['upload_date']),
                tags=tags
            )
            
            # Migration du fichier
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_data['filename'])
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        doc.file_content = f.read()
                        doc.file_type = 'application/pdf'  # Par défaut pour les anciens fichiers
                        print(f"Migration réussie : {doc.filename}")
                except Exception as e:
                    print(f"Erreur lors de la migration de {doc.filename}: {str(e)}")
            
            db.session.add(doc)
    
    # Vérification/création du compte admin
    if not User.query.filter_by(username='JMA').first():
        print("Création du compte administrateur...")
        admin = User(username='JMA')
        admin.set_password('ChoniqueYouche88!')
        db.session.add(admin)
    
    try:
        db.session.commit()
        print("Migration terminée avec succès !")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde : {str(e)}")
        db.session.rollback()
        raise

END

echo "Build terminé avec succès !"
