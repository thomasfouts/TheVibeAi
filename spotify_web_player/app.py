from flask import Flask, redirect, request, session, render_template, url_for
import requests
import base64
import os
import urllib.parse  # Use this for encoding URL parameters
import sys
import os

# Add the parent directory of the 'server' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import server.Vibe

app = Flask(__name__)
app.secret_key = os.urandom(16)

# Spotify API credentials
#new playback testing api
CLIENT_ID = 'fee896cd565d4fb490a1fea0b2c2eda5'
CLIENT_SECRET = 'e245a021a9ec4748aec1d80b3507cfc8'
# CLIENT_ID = 'd934b45cb01f46458666c207060c29e0'
# CLIENT_SECRET  = '979d682e62634c41a04b974af0cf6eec'
REDIRECT_URI = 'http://127.0.0.1:5000/callback'

# Spotify endpoints
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
# SCOPE = 'user-read-playback-state user-modify-playback-state user-library-read user-read-currently-playing'
# SCOPE = 'user-read-playback-state user-modify-playback-state user-library-read user-read-currently-playing streaming playlist-read-private playlist-modify-private'

SCOPE = 'user-read-playback-state user-modify-playback-state user-read-currently-playing app-remote-control streaming playlist-read-private playlist-modify-private playlist-modify-public user-library-read'

# Global variable for the Vibe instance
vibe_instance = None

@app.route('/')
def show_index():
    """Return the index page."""
    if 'access_token' not in session:
        return redirect(url_for('login'))
    
    global vibe_instance
    
    # Initialize the global Vibe instance if it doesn't exist
    if vibe_instance is None:
        vibe_instance = server.Vibe.Vibe(access_token=session["access_token"])

     # Initialize the 'messages' list in the session if it doesn't exist
    if 'messages' not in session:
        session['messages'] = []
    
    # Retrieve the last three messages to display
    messages = session['messages'][-1:]
    
    return render_template('index.html', token=session['access_token'], messages=messages)

@app.route('/login')
def login():
    # Redirect to Spotify's authentication page
    auth_query_params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPE,
        'show_dialog': 'true'  # Forces the reauthorization dialog
    }
    query_string = urllib.parse.urlencode(auth_query_params)
    return redirect(f"{AUTH_URL}?{query_string}")


@app.route('/user_input', methods=['POST'])
def user_input():

    message_body = request.form['userinput']

    if 'messages' not in session:
        session['messages'] = []

    session['messages'].append(message_body)
    session.modified = True

    if vibe_instance:
        vibe_instance.handle_request(message_body)
    
    return redirect(url_for('show_index'))


@app.route('/callback')
def callback():
    # Get the authorization code from the URL
    code = request.args.get('code')
    
    if not code:
        return f"Error: No code received. Response: {request.args}"

    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    # Exchange the authorization code for access and refresh tokens
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }

    token_headers = {
        'Authorization': f'Basic {auth_header}'
    }

    response = requests.post(TOKEN_URL, data=token_data, headers=token_headers)
    response_data = response.json()

    # Log response data to check for errors
    print(response_data)

    if response.status_code != 200:
        return f"Error: {response_data.get('error', 'Unknown error')}"

    # Store the tokens in the session
    session['access_token'] = response_data['access_token']
    session['refresh_token'] = response_data['refresh_token']
    # Reinitialize the Vibe instance with the new access token
    vibe_instance = server.Vibe.Vibe(access_token=session['access_token'])
    return redirect(url_for('show_index'))


@app.route('/player')
def player():
    if 'access_token' not in session:
        return redirect(url_for('login'))
    # Pass the access token to the HTML template
    return render_template('index.html', token=session['access_token'])

@app.route('/logout')
def logout():
    session.clear()  # Clear the session to remove tokens
    vibe_instance = None  # Clear the global Vibe instance
    return redirect(url_for('login'))  # Redirect to the login page


def refresh_token():
    refresh_data = {
        'grant_type': 'refresh_token',
        'refresh_token': session['refresh_token']
    }
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    token_headers = {
        'Authorization': f'Basic {auth_header}'
    }

    response = requests.post(TOKEN_URL, data=refresh_data, headers=token_headers)
    response_data = response.json()
    session['access_token'] = response_data['access_token']

if __name__ == '__main__':
    app.run(debug=True)
