import os
from app import app, db
from models import User, Article, Document, Tag

print("\n=== Configuration de l'application ===")
print(f"Mode de base de données : {'PostgreSQL' if 'DATABASE_URL' in os.environ else 'SQLite'}")
print(f"Dossier d'upload configuré : {app.config['UPLOAD_FOLDER']}")

# Création des tables de la base de données au démarrage
with app.app_context():
    try:
        print("\n=== Initialisation de la base de données ===")
        db.create_all()
        
        # Affichage des tables
        print("\nTables créées :")
        for table in db.metadata.tables.keys():
            print(f"- {table}")
            
        # Vérification des données existantes
        articles_count = Article.query.count()
        documents_count = Document.query.count()
        tags_count = Tag.query.count()
        users_count = User.query.count()
        
        print(f"\nStatistiques :")
        print(f"- Articles : {articles_count}")
        print(f"- Documents : {documents_count}")
        print(f"- Tags : {tags_count}")
        print(f"- Utilisateurs : {users_count}")
        
        print("\nBase de données initialisée avec succès !")
        
    except Exception as e:
        print(f"\n ERREUR lors de l'initialisation : {str(e)}")
        raise

if __name__ == "__main__":
    app.run()
