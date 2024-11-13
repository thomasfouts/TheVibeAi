"""VibeAI flask routes"""
import flask
from vibe import app, utils
from flask import request, session
import uuid
import hashlib


@app.route('/')
def show_index():
    """Return the index page."""
    messages = session.get('messages', [])
    print(messages)
    return flask.render_template("index.html")


@app.route('/user_input', methods=['POST'])
def user_input():

    message_body = flask.request.form['userinput']

    if 'messages' not in flask.session:
        flask.session['messages'] = []

    session['messages'].append(message_body)
    session.modified = True
    
    return flask.redirect(flask.url_for('show_index'))


@app.route('/auth/')
def auth():
    """Authorize username."""
    if "username" not in flask.session:
        flask.abort(403)
    return '', 200


@app.route('/catch_vibe')
def catch_vibe():
    """Return the join vibe page."""
    #TODO: Create html and handle authentication for vibe room, handle database
    return 

@app.route('/start_vibe')
def start_vibe():
    """Return the start vibe page."""
    #TODO: Create html and handle authentication for vibe room, handle database/playlist, settings
    #Generate identifier
    return


@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    flask.session.clear()
    return flask.redirect(flask.url_for('show_index'))


@app.route("/generate_playlist", methods=["POST"])
def generate_playlist():
    if 'username' not in flask.session:
        return flask.render_template("index.html")
    preferences = flask.request.form['preferences']
    playlist = flask.session["dj"].generate_playlist(preferences)
    #TODO: Do something with playlist, keep track of current


