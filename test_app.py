import os
from app import app, db
from models import User, Article, Document, Tag

def test_environment():
    """Vérifie l'environnement de l'application"""
    print("\n=== Test de l'environnement ===")
    print(f"Mode Debug : {app.debug}")
    print(f"Base de données : {app.config['SQLALCHEMY_DATABASE_URL']}")
    print(f"Dossier uploads : {app.config['UPLOAD_FOLDER']}")
    
    # Vérification du dossier uploads
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        print("✅ Le dossier uploads existe")
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        print(f"   - {len(files)} fichiers trouvés")
    else:
        print("❌ Le dossier uploads n'existe pas")

def test_database():
    """Vérifie la base de données"""
    print("\n=== Test de la base de données ===")
    with app.app_context():
        try:
            # Test de connexion
            db.session.execute("SELECT 1")
            print("✅ Connexion à la base de données OK")
            
            # Test des tables
            tables = db.metadata.tables.keys()
            print(f"\nTables trouvées : {len(tables)}")
            for table in tables:
                print(f"- {table}")
            
            # Test des données
            print("\nDonnées dans la base :")
            print(f"- Articles : {Article.query.count()}")
            print(f"- Documents : {Document.query.count()}")
            print(f"- Tags : {Tag.query.count()}")
            print(f"- Utilisateurs : {User.query.count()}")
            
        except Exception as e:
            print(f"❌ Erreur de base de données : {str(e)}")

def test_routes():
    """Vérifie les routes principales"""
    print("\n=== Test des routes ===")
    with app.test_client() as client:
        # Test de la page d'accueil
        response = client.get('/')
        print(f"Route / : {response.status_code}")
        
        # Test de la page de login
        response = client.get('/login')
        print(f"Route /login : {response.status_code}")
        
        # Test de la page admin (doit rediriger car non connecté)
        response = client.get('/admin')
        print(f"Route /admin : {response.status_code}")

if __name__ == '__main__':
    print("=== Diagnostic de l'application ===")
    test_environment()
    test_database()
    test_routes()
