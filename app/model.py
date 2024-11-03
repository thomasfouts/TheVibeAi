"""VibeAI model (database) API."""
import app
from flask import g, current_app


def get_db():
    """Open a new MongoDB connection if there isn't one already."""
    #if 'db' not in flask.g:
        #db_filename = current_app.config['DATABASE_FILENAME']
    #...
    #TODO

    
@app.vibe.teardown_appcontext
def close_db(error):
    """Close the connection at the end of a request."""
    #TODO