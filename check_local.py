from app import app
from models import db, User, Article, Document, Tag

print("\n=== Vérification de l'environnement local ===")

with app.app_context():
    # Vérification des tables
    print("\nTables dans la base de données :")
    for table in db.metadata.tables.keys():
        print(f"- {table}")
    
    # Vérification du compte admin
    admin = User.query.filter_by(username='JMA').first()
    if admin:
        print("\n✅ Le compte administrateur existe")
    else:
        print("\n❌ Le compte administrateur n'existe pas")
        print("Création du compte administrateur...")
        admin = User(username='JMA')
        admin.set_password('ChoniqueYouche88!')
        db.session.add(admin)
        db.session.commit()
        print("Compte administrateur créé !")
    
    # Statistiques
    print("\nContenu de la base de données :")
    print(f"- Articles : {Article.query.count()}")
    print(f"- Documents : {Document.query.count()}")
    print(f"- Tags : {Tag.query.count()}")
    print(f"- Utilisateurs : {User.query.count()}")
