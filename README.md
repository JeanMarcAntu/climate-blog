# Blog Climat & Entreprises

Un blog moderne pour documenter et partager des informations sur les réponses des entreprises au changement climatique.

## Fonctionnalités

- **Articles**
  - Création et édition d'articles
  - Recherche dans les articles
  - Interface moderne et responsive

- **Bibliothèque de Documents**
  - Upload de documents (PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT)
  - Organisation par tags
  - Recherche dans les documents
  - Métadonnées : auteur, année, description
  - Filtrage par tags

## Installation

1. Cloner le repository :
```bash
git clone [URL_DU_REPO]
cd climate_blog
```

2. Créer un environnement virtuel Python :
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Créer le dossier pour les uploads :
```bash
mkdir uploads
```

5. Lancer l'application :
```bash
python app.py
```

L'application sera accessible à l'adresse : http://127.0.0.1:5000

## Structure du Projet

```
climate_blog/
├── app.py              # Application principale
├── requirements.txt    # Dépendances Python
├── uploads/           # Dossier des documents uploadés
└── templates/         # Templates HTML
    ├── base.html
    ├── home.html
    ├── article.html
    ├── documents.html
    └── ...
```

## Technologies Utilisées

- **Backend** : Python avec Flask
- **Base de données** : SQLite avec SQLAlchemy
- **Frontend** : HTML, Bootstrap 5
- **Icônes** : Font Awesome
