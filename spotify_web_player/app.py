from flask import Flask, redirect, request, session, render_template, url_for
from flask import jsonify
import requests
import base64
import os
import urllib.parse  # Use this for encoding URL parameters
import sys
import requests
import threading
import time

# Add the parent directory of the 'server' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import server.Vibe

# Spotify endpoint to get the current song
CURRENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"

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

SCOPE = 'user-read-playback-state user-modify-playback-state user-read-currently-playing app-remote-control streaming playlist-read-private playlist-modify-private playlist-modify-public user-library-read user-read-recently-played'

# Global variable for the Vibe instance
vibe_instance = None
global_access_token = None
global_current_song = None

# Function to update session data with current song details
def update_current_song():
    """Background task to fetch current song every .7 seconds."""
    global global_access_token, global_current_song

    while True:
        if global_access_token:
            headers = {'Authorization': f"Bearer {global_access_token}"}
            response = requests.get(CURRENTLY_PLAYING_URL, headers=headers)

            if response.status_code == 200:
                try:
                    song_data = response.json()
                    global_current_song = {
                        'song_name': song_data['item']['name'],
                        'artist_name': song_data['item']['artists'][0]['name'],
                        'album_image_url': song_data['item']['album']['images'][0]['url']
                    }
                except Exception as e:
                    print("Error parsing Spotify response:", e)
            elif response.status_code == 204:
                global_current_song = None  # No song playing
            elif response.status_code == 401:
                print("Token expired, refreshing...")
                global_access_token = refresh_token(session.get('refresh_token'))
            else:
                print("Spotify API error:", response.status_code, response.text)
        time.sleep(.7)

# Start a thread for the background task
def start_background_task():
    thread = threading.Thread(target=update_current_song, daemon=True)
    thread.start()

# Initialize background task at app startup
start_background_task()

@app.route('/')
def show_index():
    """Return the index page."""
    if 'access_token' not in session:
        return redirect(url_for('login'))
    
    global vibe_instance
    global global_access_token
    global_access_token = session['access_token']
    # Initialize the global Vibe instance if it doesn't exist
    if vibe_instance is None:
        vibe_instance = server.Vibe.Vibe(access_token=session["access_token"])

     # Initialize the 'messages' list in the session if it doesn't exist
    if 'messages' not in session:
        session['messages'] = []
    
    # Retrieve the last three messages to display
    messages = session['messages'][-1:]
    
    return render_template('index.html', token=session['access_token'], messages=messages)

@app.after_request
def apply_cookie_settings(response):
    response.headers["Set-Cookie"] = "session=your_session_data; SameSite=None; Secure"
    return response

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

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "message": "Input processed successfully", "new_message": message_body})
    else:
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

@app.route('/current_song')
def current_song():
    if global_current_song:
        return jsonify(global_current_song)
    # Example of the song data. This should come from the actual Spotify API request in a real scenario.
    song_data = {
        'item': {
            'name': 'Time Shrinks',
            'artists': [{'name': 'Arcy Drive'}],
            'album': {
                'images': [
                    {'url': 'https://i.scdn.co/image/ab67616d0000b2733555830b1708a3e347bd3c73'}
                ]
            }
        }
    }

    # Extract song details
    song_name = song_data['item']['name']
    artist_name = song_data['item']['artists'][0]['name']
    album_image_url = song_data['item']['album']['images'][0]['url']

    # Return the song name, artist name, and album image URL in JSON format
    return jsonify({
        'song_name': song_name,
        'artist_name': artist_name,
        'album_image_url': album_image_url
    })

threading.Thread(target=update_current_song, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True)
