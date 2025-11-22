# --- Gunicorn Starter: gunicorn_starter.py ---
# This file is the required entry point for the Gunicorn WSGI server.

# It imports the Flask app instance named 'app' from app.py 
# and aliases it as 'application', which is the standard variable 
# name Gunicorn looks for to start the server.

from app import app as application
