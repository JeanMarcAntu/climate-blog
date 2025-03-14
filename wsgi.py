from app import app, db

# Création des tables de la base de données au démarrage
with app.app_context():
    db.create_all()
    print("Base de données initialisée avec succès")

if __name__ == "__main__":
    app.run()
