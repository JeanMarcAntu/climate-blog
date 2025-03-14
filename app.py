from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dotenv import load_dotenv
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

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'votre_clé_secrète_par_défaut')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Création du dossier uploads s'il n'existe pas
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialisation de la base de données
db = SQLAlchemy(app)

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

# Route pour créer un nouvel article
@app.route('/admin/new', methods=['GET', 'POST'])
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
                # Sécurisation du nom de fichier
                filename = secure_filename(file.filename)
                # Ajout d'un timestamp pour éviter les doublons
                filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
                
                # Sauvegarde du fichier
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                
                # Traitement des tags
                tag_names = [t.strip() for t in request.form.get('tags', '').split(',')]
                tags = get_or_create_tags(tag_names)
                
                # Création de l'entrée dans la base de données
                document = Document(
                    filename=filename,
                    original_filename=file.filename,
                    title=request.form['title'],
                    author=request.form.get('author'),
                    year=int(request.form.get('year')) if request.form.get('year') else None,
                    description=request.form.get('description'),
                    tags=tags
                )
                db.session.add(document)
                db.session.commit()
                
                flash('Document uploadé avec succès!', 'success')
                return redirect(url_for('documents'))
            except Exception as e:
                flash(f'Erreur lors de l\'upload : {str(e)}', 'error')
                return redirect(request.url)
                
        flash('Type de fichier non autorisé', 'error')
        return redirect(request.url)
        
    return render_template('upload_document.html', current_year=datetime.utcnow().year)

# Route pour éditer un document
@app.route('/edit_document/<int:document_id>', methods=['GET', 'POST'])
def edit_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    if request.method == 'POST':
        try:
            document.title = request.form['title']
            document.author = request.form.get('author')
            year = request.form.get('year', '')
            document.year = int(year) if year.strip() else None
            document.description = request.form.get('description')
            
            # Mise à jour des tags
            tag_names = [t.strip() for t in request.form.get('tags', '').split(',')]
            document.tags = get_or_create_tags(tag_names)
            
            db.session.commit()
            flash('Document modifié avec succès!', 'success')
            return redirect(url_for('documents'))
            
        except Exception as e:
            flash(f'Erreur lors de la modification : {str(e)}', 'error')
            return redirect(url_for('documents'))
    
    return render_template('edit_document.html', document=document)

# Route pour supprimer un article
@app.route('/admin/delete_article/<int:article_id>', methods=['POST'])
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
