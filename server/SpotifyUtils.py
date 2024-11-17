# spotipy
import spotipy
from spotipy import CacheFileHandler, prompt_for_user_token
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util as util

# python
import getpass
import os

# setup spotify keys
# if not os.environ.get("SPOTIPY_CLIENT_ID"):
#     os.environ["SPOTIPY_CLIENT_ID"] = getpass.getpass("Enter your SpotiPy Client ID: ")
# if not os.environ.get("SPOTIPY_CLIENT_SECRET"):
#     os.environ["SPOTIPY_CLIENT_SECRET"] = getpass.getpass("Enter your SpotiPy Client Secret: ")
# username = input("What is your Spotify username?\n")
# token = prompt_for_user_token(
#     username=username,
#     scope='playlist-modify-private, playlist-modify-public, user-modify-playback-state',
#     client_id=os.environ["SPOTIPY_CLIENT_ID"],
#     client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
#     redirect_uri="http://localhost:3000",
# )
# sp = spotipy.Spotify(auth=token)
# auth = SpotifyClientCredentials(
#     client_id=os.environ['SPOTIPY_CLIENT_ID'],
#     client_secret=os.environ['SPOTIPY_CLIENT_SECRET']
# )
# sp = spotipy.Spotify(auth_manager=auth)

# load spotipy documentation for rag

class SpotifyUtils:
    def __init__(self, access_token=None):
        self.playlist_id = 0
        self.playlist_uri = []
        self.playlist_artist_tracks = []

        self.sp = None
        if access_token:
            # Authenticate using the user's access token
            self.sp = spotipy.Spotify(auth=access_token)

        # Retrieve the user ID
        self.user_id = self.get_user_id()

        # Create playlist using the user's actual ID
        self.create_playlist()

    def get_user_id(self):
        """Gets the current user's Spotify ID."""
        try:
            user_data = self.sp.current_user()
            return user_data["id"]
        except Exception as e:
            print(f"Error fetching user ID: {e}")
            return None

    def create_playlist(self):
        """Create a playlist on the user's account."""
        if not self.user_id:
            raise ValueError("User ID is not available. Cannot create a playlist.")

        playlist_name = "Vibe AI Playlist -- New"
        playlist_description = "Automatically generated with AI"

        try:
            playlist = self.sp.user_playlist_create(
                self.user_id, playlist_name, public=True, description=playlist_description
            )
            self.playlist_id = playlist["id"]
        except Exception as e:
            print(f"Error creating playlist: {e}")

    def add_songs(self, uri_list: list):
        """Add songs to local playlist and the user's Spotify account."""
        for uri in uri_list:
            # Add songs and artists to local playlist
            self.playlist_uri.append(uri)
            track_data = self.sp.track(uri)
            song_name = track_data['name']
            artist_name = track_data['artists'][0]['name']
            self.playlist_artist_tracks.append({'song_name': song_name, 'artist_name': artist_name})

        # Add songs to user's Spotify account playlist
        try:
            self.sp.playlist_add_items(self.playlist_id, uri_list)
        except Exception as e:
            print(f"Error adding songs to playlist: {e}")

    def print_playlist(self):
        """Print songs in the playlist."""
        print("Your playlist:")
        for line in self.playlist_artist_tracks:
            print("Name: " + line['song_name'])
            print("Artist: " + line['artist_name'])

    def play_playlist(self):
        """Start playback of the user's playlist."""
        try:
            self.sp.start_playback(context_uri=f"spotify:playlist:{self.playlist_id}")
        except Exception as e:
            print(f"Error starting playback: {e}")

    def get_last_artist(self) -> str:
        """Return the last artist for song transitions."""
        if len(self.playlist_uri) > 0:
            track_data = self.sp.track(self.playlist_uri[-1])
            return track_data['artists'][0]['uri']
        return ""
