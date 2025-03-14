from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Chargement des variables d'environnement
load_dotenv()

# Configuration des uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}

# Initialisation de l'application Flask
app = Flask(__name__)

# Configuration de la base de données
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    # Render ajoute postgres://, mais SQLAlchemy attend postgresql://
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # En local, on utilise SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'

# Définition d'une clé secrète stable pour le développement
app.config['SECRET_KEY'] = 'dev_secret_key_123'  # Ne pas utiliser en production
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Création du dossier uploads s'il n'existe pas
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialisation de la base de données
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Table d'association pour les tags des documents
document_tags = db.Table('document_tags',
    db.Column('document_id', db.Integer, db.ForeignKey('document.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# Modèle pour les tags
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    def __repr__(self):
        return f'<Tag {self.name}>'

# Modèle pour les articles
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Article {self.title}>'

# Modèle pour les documents
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=True)
    year = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    tags = db.relationship('Tag', secondary=document_tags, lazy='subquery',
        backref=db.backref('documents', lazy=True))
    
    def __repr__(self):
        return f'<Document {self.title}>'

# Modèle pour les utilisateurs
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Fonction utilitaire pour gérer les tags
def get_or_create_tags(tag_names):
    tags = []
    for name in tag_names:
        name = name.strip().lower()
        if name:
            tag = Tag.query.filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name)
                db.session.add(tag)
            tags.append(tag)
    return tags

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route pour la page d'accueil
@app.route('/')
def home():
    articles = Article.query.order_by(Article.created_date.desc()).all()
    return render_template('home.html', articles=articles)

# Route pour afficher un article
@app.route('/article/<int:article_id>')
def article(article_id):
    article = Article.query.get_or_404(article_id)
    return render_template('article.html', article=article)

# Route pour la page de connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Connexion réussie !', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('home'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'error')
    
    return render_template('login.html')

# Route pour la déconnexion
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('home'))

# Route pour créer un nouvel article
@app.route('/admin/new', methods=['GET', 'POST'])
@login_required
def new_article():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        article = Article(title=title, content=content)
        db.session.add(article)
        db.session.commit()
        
        flash('Article créé avec succès!', 'success')
        return redirect(url_for('home'))
    
    return render_template('new_article.html')

# Route pour la recherche
@app.route('/search')
def search():
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')  # 'all', 'articles', ou 'documents'
    
    if query:
        if search_type == 'articles' or search_type == 'all':
            articles = Article.query.filter(
                (Article.title.ilike(f'%{query}%')) |
                (Article.content.ilike(f'%{query}%'))
            ).order_by(Article.created_date.desc()).all()
        else:
            articles = []
            
        if search_type == 'documents' or search_type == 'all':
            documents = Document.query.filter(
                (Document.title.ilike(f'%{query}%')) |
                (Document.description.ilike(f'%{query}%'))
            ).order_by(Document.upload_date.desc()).all()
        else:
            documents = []
    else:
        articles = []
        documents = []
        
    return render_template('search.html', 
                         articles=articles, 
                         documents=documents, 
                         query=query, 
                         search_type=search_type)

# Route pour la page des documents
@app.route('/documents')
def documents():
    try:
        selected_tag = request.args.get('tag')
        if selected_tag:
            # Filtrer les documents par tag
            tag = Tag.query.filter_by(name=selected_tag.lower()).first_or_404()
            documents = tag.documents
        else:
            # Récupérer tous les documents
            documents = Document.query.order_by(Document.upload_date.desc()).all()
        
        # Récupérer tous les tags pour le filtre
        tags = Tag.query.order_by(Tag.name).all()
        
        return render_template('documents.html', 
                             documents=documents, 
                             tags=tags, 
                             selected_tag=selected_tag)
    except Exception as e:
        flash(str(e), 'error')
        return render_template('documents.html', documents=[], tags=[])

# Route pour télécharger un document
@app.route('/download/<int:document_id>')
def download_document(document_id):
    document = Document.query.get_or_404(document_id)
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                             document.filename,
                             as_attachment=True,
                             download_name=document.original_filename)

# Route pour uploader un document
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    if request.method == 'POST':
        if 'document' not in request.files:
            flash('Aucun fichier sélectionné', 'error')
            return redirect(request.url)
            
        file = request.files['document']
        if file.filename == '':
            flash('Aucun fichier sélectionné', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                # Génération d'un nom unique pour le fichier
                unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                
                # Récupération des données du formulaire
                title = request.form.get('title', filename)
                author = request.form.get('author')
                year = request.form.get('year')
                description = request.form.get('description')
                tags = request.form.get('tags', '').split(',')
                
                # Sauvegarde du fichier
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                
                # Création du document dans la base de données
                document = Document(
                    filename=unique_filename,
                    original_filename=filename,
                    title=title,
                    author=author,
                    year=year if year else None,
                    description=description
                )
                
                # Gestion des tags
                document.tags = get_or_create_tags(tags)
                
                db.session.add(document)
                db.session.commit()
                
                flash('Document uploadé avec succès!', 'success')
                return redirect(url_for('documents'))
            except Exception as e:
                flash(f'Erreur lors de l\'upload : {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Type de fichier non autorisé', 'error')
            return redirect(request.url)
            
    return render_template('upload.html')

# Route pour éditer un document
@app.route('/admin/edit_document/<int:document_id>', methods=['GET', 'POST'])
@login_required
def edit_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    if request.method == 'POST':
        document.title = request.form.get('title')
        document.author = request.form.get('author')
        document.year = request.form.get('year') if request.form.get('year') else None
        document.description = request.form.get('description')
        
        # Mise à jour des tags
        tags = request.form.get('tags', '').split(',')
        document.tags = get_or_create_tags(tags)
        
        db.session.commit()
        flash('Document modifié avec succès!', 'success')
        return redirect(url_for('documents'))
    
    return render_template('edit_document.html', document=document)

# Route pour supprimer un article
@app.route('/admin/delete_article/<int:article_id>', methods=['POST'])
@login_required
def delete_article(article_id):
    article = Article.query.get_or_404(article_id)
    try:
        db.session.delete(article)
        db.session.commit()
        flash('Article supprimé avec succès !', 'success')
    except Exception as e:
        flash(f'Erreur lors de la suppression : {str(e)}', 'error')
    return redirect(url_for('home'))

# Route pour supprimer un document
@app.route('/admin/delete_document/<int:document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)
    try:
        # Supprimer le fichier physique
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Supprimer l'entrée dans la base de données
        db.session.delete(document)
        db.session.commit()
        flash('Document supprimé avec succès !', 'success')
    except Exception as e:
        flash(f'Erreur lors de la suppression : {str(e)}', 'error')
    return redirect(url_for('documents'))

if __name__ == '__main__':
    # Création des dossiers nécessaires
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Création de la base de données si elle n'existe pas
    with app.app_context():
        db.create_all()
    
    # Lancement du serveur en mode développement
    app.run(debug=True)
