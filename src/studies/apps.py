import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class StudiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'studies'

    def ready(self):
        try:
            from .logic.ai import initialize
            initialize()
            logger.info("Gemini client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")

