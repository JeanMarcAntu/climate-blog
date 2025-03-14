from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, make_response
from datetime import datetime
import os
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from models import db, Tag, Article, Document, User

# Chargement des variables d'environnement
load_dotenv()

# Configuration des uploads
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'))
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}

# Initialisation de l'application Flask
app = Flask(__name__)

# Configuration de la base de données
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///blog.db'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key_123')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Création du dossier uploads s'il n'existe pas
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialisation de la base de données et du login manager
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Fonction utilitaire pour gérer les tags
def get_or_create_tags(tag_names):
    tags = []
    for name in tag_names:
        name = name.strip()
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

# Route pour la modification d'un article
@app.route('/admin/edit/<int:article_id>', methods=['GET', 'POST'])
@login_required
def edit_article(article_id):
    article = Article.query.get_or_404(article_id)
    if request.method == 'POST':
        article.title = request.form['title']
        article.content = request.form['content']
        db.session.commit()
        flash('Article modifié avec succès!', 'success')
        return redirect(url_for('article', article_id=article.id))
    return render_template('edit_article.html', article=article)

# Route pour supprimer un article
@app.route('/admin/delete/article/<int:article_id>', methods=['GET', 'POST'])
@login_required
def delete_article(article_id):
    article = Article.query.get_or_404(article_id)
    db.session.delete(article)
    db.session.commit()
    flash('Article supprimé avec succès!', 'success')
    return redirect(url_for('home'))

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
@app.route('/admin/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Aucun fichier sélectionné', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Aucun fichier sélectionné', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Sécurisation du nom de fichier
            filename = secure_filename(file.filename)
            # Ajout d'un timestamp pour éviter les doublons
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            
            # Sauvegarde du fichier
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Création du document dans la base de données
            title = request.form.get('title', filename)
            author = request.form.get('author', '')
            year = request.form.get('year', None)
            description = request.form.get('description', '')
            
            # Gestion des tags
            tag_names = request.form.get('tags', '').split(',')
            tags = get_or_create_tags(tag_names)
            
            document = Document(
                filename=filename,
                original_filename=file.filename,
                title=title,
                author=author,
                year=year if year and year.isdigit() else None,
                description=description,
                tags=tags
            )
            
            db.session.add(document)
            db.session.commit()
            
            flash('Document uploadé avec succès!', 'success')
            return redirect(url_for('documents'))
            
        flash('Type de fichier non autorisé', 'error')
        return redirect(request.url)
        
    return render_template('upload_document.html')

# Route pour éditer un document
@app.route('/admin/edit/document/<int:document_id>', methods=['GET', 'POST'])
@login_required
def edit_document(document_id):
    document = Document.query.get_or_404(document_id)
    if request.method == 'POST':
        document.title = request.form.get('title', document.title)
        document.author = request.form.get('author', document.author)
        document.year = request.form.get('year', document.year)
        document.description = request.form.get('description', document.description)
        
        # Mise à jour des tags
        tag_names = request.form.get('tags', '').split(',')
        document.tags = get_or_create_tags(tag_names)
        
        db.session.commit()
        flash('Document modifié avec succès!', 'success')
        return redirect(url_for('documents'))
        
    return render_template('edit_document.html', document=document)

# Route pour supprimer un document
@app.route('/admin/delete/document/<int:document_id>')
@login_required
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Suppression du fichier physique
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Suppression de l'entrée dans la base de données
    db.session.delete(document)
    db.session.commit()
    
    flash('Document supprimé avec succès!', 'success')
    return redirect(url_for('documents'))

@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    # Création des dossiers nécessaires
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Création des tables de la base de données
    with app.app_context():
        db.create_all()
        print("Base de données initialisée avec succès")
    
    # Lancement du serveur en mode développement
    app.run(debug=True)
