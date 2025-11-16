import os

# Gunicorn config variables
loglevel = os.environ.get("LOG_LEVEL", "info")
workers = os.environ.get("WORKERS", "1")
bind = os.environ.get("BIND", "0.0.0.0:8000")
accesslog = os.environ.get("ACCESS_LOG", "-")
errorlog = os.environ.get("ERROR_LOG", "-")
