# spotipy
import spotipy
from spotipy import CacheFileHandler, prompt_for_user_token
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util as util

# python
import getpass
import os

# setup spotify keys
if not os.environ.get("SPOTIPY_CLIENT_ID"):
    os.environ["SPOTIPY_CLIENT_ID"] = getpass.getpass("Enter your SpotiPy Client ID: ")
if not os.environ.get("SPOTIPY_CLIENT_SECRET"):
    os.environ["SPOTIPY_CLIENT_SECRET"] = getpass.getpass("Enter your SpotiPy Client Secret: ")
username = input("What is your Spotify username?\n")
token = prompt_for_user_token(
    username=username,
    scope='playlist-modify-private, playlist-modify-public, user-modify-playback-state',
    client_id=os.environ["SPOTIPY_CLIENT_ID"],
    client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
    redirect_uri="http://localhost:9090",
)
sp = spotipy.Spotify(auth=token)
# auth = SpotifyClientCredentials(
#     client_id=os.environ['SPOTIPY_CLIENT_ID'],
#     client_secret=os.environ['SPOTIPY_CLIENT_SECRET']
# )
# sp = spotipy.Spotify(auth_manager=auth)

# load spotipy documentation for rag

class SpotifyUtils:
    def __init__(self):
        self.playlist_id = 0
        self.playlist_uri = []
        self.playlist_artist_tracks = []
        self.create_playlist()

    def create_playlist(self):
        # create playlist on user account
        playlist_name = "Vibe AI Playlist"
        playlist_description = "Automatically generated with AI"
        self.playlist_id = sp.user_playlist_create(username, playlist_name, public=True, description=playlist_description)["id"]

    def add_songs(self, uri_list : list):
        # add songs to local playlist and user account
        for uri in uri_list:
            # add songs and artists to local playlist
            self.playlist_uri.append(uri)
            track_data = sp.track(uri)
            song_name = track_data['name']
            artist_name = track_data['artists'][0]['name']
            self.playlist_artist_tracks.append({'song_name' : song_name, 'artist_name' : artist_name})
        # add songs to user's spotify account playlist
        sp.playlist_add_items(self.playlist_id, uri_list)

    def print_playlist(self):
        # print songs in playlist
        print("Your playlist: ")
        for line in self.playlist_artist_tracks:
            print("Name: " + line['song_name'])
            print("Artist: " + line['artist_name'])

    def play_playlist(self):
        sp.start_playback(self.playlist_id)

    def get_last_artist(self) -> str:
        # return the last artist for song transitions
        if len(self.playlist_uri) > 0:
            track_data = sp.track(self.playlist_uri[-1])
            return track_data['artists'][0]['uri']
        return ""