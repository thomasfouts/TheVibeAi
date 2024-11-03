"""VibeAI flask routes"""
import flask
import app
from flask import request
import playlist
import uuid
import hashlib
import utils


@app.vibe.route('/')
def show_index():
    """Return the index page."""
    return flask.render_template("index.html")

@app.vibe.route('/create_account_page')
def create_account_page():
    """Return Registration page"""
    #TODO
    if 'username' in flask.session:
        return flask.redirect(flask.url_for('edit_account'))
    return flask.render_template("create_account.html")  # Assumes a registration page

@app.vibe.route('/create_account', methods=['POST'])
def create_account():
    """Handle new user registration"""
    username = flask.request.form['username']
    password = flask.request.form['password']
    email = flask.request.form['email']
    password_hash = utils.hash_password(password)
    #spotify_authentication = ____
    #authenticare spotify
    #insert into database
    flask.session['username'] = username

    #TODO: Create session, authorize spotify
    return

@app.vibe.route('/auth/')
def auth():
    """Authorize username."""
    if "username" not in flask.session:
        flask.abort(403)
    return '', 200

#FIX  
@app.vibe.route('/forgot_password', methods=['POST'])
def forgot_password():
    """Send email to with code to update password"""
    email = request.form.get('email')
    # Check if the email exists in the database
    user = utils.find_user_by_email(email)  # This function should query the database for the user by email
    if not user:
        flask.flash("This email is not registered.", "error")
        return flask.redirect(flask.url_for('forgot_password_page'))

    # Generate a password reset token (e.g., a secure random token or UUID)
    reset_token = utils.generate_reset_token(email)
    
    # Save the reset token in the database or cache with an expiration time
    utils.save_reset_token(email, reset_token)  # Implement this function based on your database setup

    # Send an email with the reset link (use a real email-sending library in production)
    reset_link = flask.url_for('reset_password', token=reset_token, _external=True)
    utils.send_reset_email(email, reset_link)  # Implement an email-sending function to send the link

    # Inform the user to check their email
    flask.flash("A password reset link has been sent to your email.", "info")
    return flask.redirect(flask.url_for('show_index'))

@app.vibe.route('/reset_password/<token>', methods=['POST'])
def reset_password(token):
    """Allow the user to reset their password via a reset token."""
    if request.method == 'POST':
        # Get the new password from the form
        new_password = request.form.get('password')
        # Verify the token, retrieve the user's email from it, and update their password
        email = utils.verify_reset_token(token)  # Implement this function to validate the token and retrieve the associated email
        if not email:
            flask.flash("The reset link is invalid or has expired.", "error")
            return flask.redirect(flask.url_for('forgot_password_page'))
        
        # Hash the new password and save it to the database
        new_password_hash = utils.hash_password(new_password)
        utils.update_user_password(email, new_password_hash)  # Implement this to update the user's password in the database
        
        flask.flash("Your password has been reset. Please log in.", "success")
        return flask.redirect(flask.url_for('login_page'))

@app.vibe.route('/forgot_password_page', methods=['GET'])
def forgot_password_page():
    """Return the forgot password page."""
    return flask.render_template('landing.html')


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


@app.vibe.route('/logout')
def logout():
    # remove the username from the session if it's there
    flask.session.clear()
    return flask.redirect(flask.url_for('show_index'))


@app.vibe.route("/generate_playlist", methods=["POST"])
def generate_playlist():
    if 'username' not in flask.session:
        return flask.render_template("index.html")
    preferences = flask.request.form['preferences']
    playlist = flask.session["dj"].generate_playlist(preferences)
    #TODO: Do something with playlist, keep track of current

@app.vibe.route("/transition_songs", methods=["POST"])
def transition_songs():
    """Provide new preferences"""
    #TODO
    return

@app.vibe.route("/end_vibe", methods=["POST"])
def end():
    """End vibe"""
    #TODO
    return

@app.vibe.route("/skip", methods=["POST"])
def skip():
    """Vote to skip"""
    #TODO
    return

@app.vibe.route("/find_playlist", methods=["POST"])
def find_playlist():
    """Retrieve a previous playlist"""
    #TODO
    return

@app.vibe.route('/login', methods=['POST'])
def login():
    connection = "FIXME"
    username = flask.request.form['username']
    password = flask.request.form['password']
    if not username or not password:
        flask.flash("Username and password are required.", "error")
        return flask.redirect(request.url)
    #user = find from database
    #password_hash = user['password']

    #if not verify_password(password, password_hash):
        #flask.abort(403)
    flask.session['username'] = username
    flask.session['dj'] = playlist.Playlist()
    
    #TODO
    #Verify Password and create session, redirect to options page
    return flask.render_template('landing.html')
