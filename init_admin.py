from app import app, db, User

def init_admin():
    with app.app_context():
        # Vérifier si les tables existent
        db.create_all()
        
        # Vérifier si l'administrateur existe déjà
        admin = User.query.filter_by(username='JMA').first()
        if not admin:
            # Créer l'administrateur
            admin = User(username='JMA')
            admin.set_password('ChoniqueYouche88!')
            db.session.add(admin)
            db.session.commit()
            print("Compte administrateur créé avec succès !")
        else:
            print("Le compte administrateur existe déjà !")

if __name__ == '__main__':
    init_admin()
