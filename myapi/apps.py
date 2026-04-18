import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class MyapiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapi'

    def ready(self):
        # Register Django signals
        import myapi.signals  # noqa: F401

        # Initialize Firebase Admin SDK (once)
        try:
            import os
            import json
            import firebase_admin
            from firebase_admin import credentials

            if not firebase_admin._apps:
                firebase_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                
                if firebase_creds and firebase_creds.strip().startswith('{'):
                    # Case 1: Raw JSON string from environment variable (like on Railway)
                    try:
                        creds_dict = json.loads(firebase_creds)
                        cred = credentials.Certificate(creds_dict)
                    except json.JSONDecodeError:
                        logger.error("GOOGLE_APPLICATION_CREDENTIALS starts with '{' but is not valid JSON.")
                        cred = credentials.ApplicationDefault()
                else:
                    # Case 2: Path to a file (Standard behavior)
                    cred = credentials.ApplicationDefault()
                
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully.")
        except Exception:
            logger.warning(
                "Firebase Admin SDK failed to initialize. "
                "Push notifications will not work. Check GOOGLE_APPLICATION_CREDENTIALS.",
                exc_info=True,
            )
