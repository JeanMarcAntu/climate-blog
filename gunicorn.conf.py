import os

# Configuration des workers
workers = int(os.environ.get('GUNICORN_WORKERS', '2'))  # Par défaut 2 workers
worker_class = 'sync'  # Type de worker
worker_connections = 1000  # Nombre maximum de connexions simultanées par worker

# Configuration du serveur
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
timeout = 120  # Timeout en secondes
keepalive = 65  # Durée de maintien des connexions en secondes

# Configuration des logs
accesslog = '-'  # Logs d'accès vers stdout
errorlog = '-'   # Logs d'erreur vers stderr
loglevel = 'info'

# Configuration de la sécurité
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
