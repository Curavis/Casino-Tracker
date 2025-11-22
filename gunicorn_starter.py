# --- Gunicorn Starter: gunicorn_starter.py ---
# This file serves as the required entry point for the Gunicorn WSGI server.
# It ensures the application object is named 'app' to match the default Gunicorn startup command 
# used by the deployment environment (gunicorn gunicorn_starter:app).

from app import app
# The Flask application instance is now correctly imported as 'app'.
