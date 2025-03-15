from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, make_response, abort
import datetime
import os
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from models import db, Tag, Article, Document, User
from urllib.parse import urlparse
import logging
from flask_migrate import Migrate

# Chargement des variables d'environnement
load_dotenv()

# Configuration des uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'svg'}
THUMBNAIL_SIZE = 40  # Hauteur en pixels (même que le bouton)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def resize_image(image_path, output_path):
    """Redimensionne une image pour qu'elle soit carrée avec la hauteur spécifiée."""
    try:
        from PIL import Image
        
        # Ouvrir l'image
        with Image.open(image_path) as img:
            # Si c'est un SVG, on ne fait pas de redimensionnement
            if image_path.lower().endswith('.svg'):
                img.save(output_path)
                return True
                
            # Calculer les nouvelles dimensions
            ratio = THUMBNAIL_SIZE / float(img.size[1])
            new_width = int(float(img.size[0]) * ratio)
            
            # Redimensionner l'image en conservant les proportions
            img = img.resize((new_width, THUMBNAIL_SIZE), Image.Resampling.LANCZOS)
            
            # Créer une image carrée avec fond transparent
            square_size = THUMBNAIL_SIZE
            square_img = Image.new('RGBA', (square_size, square_size), (255, 255, 255, 0))
            
            # Centrer l'image redimensionnée
            x_offset = (square_size - new_width) // 2
            square_img.paste(img, (x_offset, 0))
            
            # Sauvegarder l'image
            square_img.save(output_path, format='PNG')
            return True
            
    except Exception as e:
        logger.error(f"Erreur lors du redimensionnement de l'image : {str(e)}")
        return False

# Initialisation de l'application Flask
app = Flask(__name__)

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de la base de données
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///blog.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# Configuration du dossier d'upload
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
logger.info(f"Dossier d'upload configuré : {UPLOAD_FOLDER}")

# Configuration des options de connexion PostgreSQL
if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
    connect_args = {
        'connect_timeout': 10,
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
        'sslmode': 'require'
    }
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': connect_args,
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20
    }

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key_123')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=60)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialisation de la base de données et du login manager
db.init_app(app)
migrate = Migrate(app, db)
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

# Fonction pour migrer les fichiers
def migrate_files():
    try:
        # Récupérer tous les documents
        documents = Document.query.all()
        
        # Pour chaque document
        for document in documents:
            old_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', document.filename)
            new_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filename)
            
            # Si le fichier existe dans l'ancien dossier et pas dans le nouveau
            if os.path.exists(old_path) and not os.path.exists(new_path):
                try:
                    # Copier le fichier
                    os.makedirs(os.path.dirname(new_path), exist_ok=True)
                    with open(old_path, 'rb') as src, open(new_path, 'wb') as dst:
                        dst.write(src.read())
                    app.logger.info(f"Fichier migré avec succès : {document.filename}")
                except Exception as e:
                    app.logger.error(f"Erreur lors de la migration du fichier {document.filename}: {str(e)}")
    except Exception as e:
        app.logger.error(f"Erreur lors de la migration des fichiers : {str(e)}")

# Appeler la migration au démarrage
with app.app_context():
    migrate_files()

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
    try:
        app.logger.info("Début de la route login")
        
        # Vérification de l'authentification
        if current_user.is_authenticated:
            app.logger.info("Utilisateur déjà connecté, redirection vers la page d'accueil")
            return redirect(url_for('home'))
        
        # Traitement du formulaire
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            app.logger.info(f"Tentative de connexion pour l'utilisateur : {username}")
            
            try:
                # Recherche de l'utilisateur
                user = User.query.filter_by(username=username).first()
                app.logger.info(f"Recherche de l'utilisateur : {'trouvé' if user else 'non trouvé'}")
                
                if user and user.check_password(password):
                    try:
                        # Tentative de connexion
                        login_user(user)
                        app.logger.info(f"Connexion réussie pour l'utilisateur : {username}")
                        flash('Connexion réussie !', 'success')
                        next_page = request.args.get('next')
                        return redirect(next_page if next_page else url_for('home'))
                    except Exception as login_error:
                        app.logger.error(f"Erreur lors du login_user : {str(login_error)}")
                        app.logger.error(f"Type d'erreur : {type(login_error).__name__}")
                        raise
                else:
                    app.logger.warning(f"Échec de connexion pour l'utilisateur : {username}")
                    flash('Nom d\'utilisateur ou mot de passe incorrect', 'error')
            except Exception as db_error:
                app.logger.error(f"Erreur lors de la requête base de données : {str(db_error)}")
                app.logger.error(f"Type d'erreur : {type(db_error).__name__}")
                raise
        
        # Affichage du formulaire
        app.logger.info("Affichage du formulaire de connexion")
        try:
            return render_template('login.html')
        except Exception as template_error:
            app.logger.error(f"Erreur lors du rendu du template : {str(template_error)}")
            app.logger.error(f"Type d'erreur : {type(template_error).__name__}")
            raise
            
    except Exception as e:
        app.logger.error(f"Erreur générale lors de la connexion : {str(e)}")
        app.logger.error(f"Type d'erreur : {type(e).__name__}")
        import traceback
        app.logger.error(f"Traceback complet : {traceback.format_exc()}")
        raise

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
        # Récupérer le tag sélectionné depuis les paramètres de l'URL
        selected_tag = request.args.get('tag')
        
        if selected_tag:
            # Si un tag est sélectionné, filtrer les documents par ce tag
            tag = Tag.query.filter_by(name=selected_tag).first()
            if tag:
                documents = tag.documents
            else:
                documents = []
        else:
            # Récupérer tous les documents si aucun tag n'est sélectionné
            documents = Document.query.order_by(Document.upload_date.desc()).all()
        
        # Récupérer tous les tags pour le filtre
        tags = Tag.query.order_by(Tag.name).all()
        
        return render_template('documents.html', 
                             documents=documents, 
                             tags=tags, 
                             selected_tag=selected_tag)
    except Exception as e:
        app.logger.error(f"Erreur lors de l'affichage des documents : {str(e)}")
        flash(str(e), 'error')
        return render_template('documents.html', documents=[], tags=[], selected_tag=None)

# Route pour télécharger un document
@app.route('/download/<int:document_id>')
def download_document(document_id):
    try:
        logger.info(f"Tentative de téléchargement du document {document_id}")
        document = Document.query.get_or_404(document_id)
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filename)
        logger.info(f"Chemin du fichier : {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"Fichier non trouvé : {file_path}")
            # Liste tous les fichiers dans le dossier pour le debug
            files = os.listdir(app.config['UPLOAD_FOLDER'])
            logger.info(f"Fichiers dans le dossier : {files}")
            flash("Le fichier n'existe pas sur le serveur.", 'error')
            return redirect(url_for('documents'))
            
        try:
            logger.info(f"Envoi du fichier : {document.original_filename}")
            return send_from_directory(
                app.config['UPLOAD_FOLDER'],
                document.filename,
                as_attachment=True,
                download_name=document.original_filename
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du fichier : {str(e)}")
            flash("Erreur lors du téléchargement du fichier.", 'error')
            return redirect(url_for('documents'))
            
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement : {str(e)}")
        flash("Une erreur s'est produite lors du téléchargement.", 'error')
        return redirect(url_for('documents'))

# Route pour uploader un document
@app.route('/admin/upload', methods=['GET', 'POST'])
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
        
        if file and allowed_file(file.filename, ALLOWED_EXTENSIONS):
            try:
                # Sécurisation du nom de fichier
                filename = secure_filename(file.filename)
                # Ajout d'un timestamp pour éviter les doublons
                filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                
                # Sauvegarde du fichier
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logger.info(f"Sauvegarde du fichier : {file_path}")
                file.save(file_path)
                
                # Gestion de l'image
                image_filename = None
                if 'image' in request.files:
                    image = request.files['image']
                    if image.filename != '' and allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
                        # Sécurisation du nom de l'image
                        image_filename = secure_filename(image.filename)
                        image_filename = f"img_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{image_filename}"
                        
                        # Sauvegarde de l'image originale
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                        logger.info(f"Sauvegarde de l'image : {image_path}")
                        image.save(image_path)
                        
                        # Création du thumbnail
                        thumb_filename = f"thumb_{image_filename}"
                        thumb_path = os.path.join(app.config['UPLOAD_FOLDER'], thumb_filename)
                        if resize_image(image_path, thumb_path):
                            # Si le redimensionnement a réussi, on utilise le thumbnail
                            image_filename = thumb_filename
                            # On peut supprimer l'image originale
                            os.remove(image_path)
                        else:
                            # En cas d'erreur, on garde l'image originale
                            logger.warning("Échec du redimensionnement, utilisation de l'image originale")
                
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
                    image_filename=image_filename,
                    title=title,
                    author=author,
                    year=year if year and year.isdigit() else None,
                    description=description,
                    tags=tags
                )
                
                db.session.add(document)
                db.session.commit()
                logger.info(f"Document créé avec succès : {document.id}")
                
                flash('Document uploadé avec succès!', 'success')
                return redirect(url_for('documents'))
            except Exception as e:
                logger.error(f"Erreur lors de l'upload : {str(e)}")
                flash("Une erreur s'est produite lors de l'upload.", 'error')
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
@app.route('/admin/delete/document/<int:document_id>', methods=['GET', 'POST'])
@login_required
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Suppression de l'entrée dans la base de données
    db.session.delete(document)
    db.session.commit()
    
    flash('Document supprimé avec succès!', 'success')
    return redirect(url_for('documents'))

# Route pour servir les images
@app.route('/uploads/<filename>')
def serve_image(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        logger.error(f"Erreur lors de l'accès à l'image {filename}: {str(e)}")
        abort(404)

@app.after_request
def add_no_cache_headers(response):
    """Ajoute les en-têtes pour désactiver le cache sur les réponses HTTP"""
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

if __name__ == '__main__':
    # Configuration pour le développement local
    app.run(
        host='127.0.0.1',     # N'écoute que les connexions locales
        port=8000,            # Utilisation du port 8000 pour éviter les conflits
        debug=True,           # Mode debug pour voir les erreurs
        use_reloader=True     # Recharge automatiquement si le code change
    )
