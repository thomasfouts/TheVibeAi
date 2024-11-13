import unittest
import spotipy
from SpotifyWrap import SpotifyUtils
from artistgraph import ArtistGraph
from songmanager import SongManager
from spotipy.oauth2 import SpotifyClientCredentials

class SongPathTests(unittest.TestCase):
    def setUp(self):
        # Set up SpotifyUtils, ArtistGraph, and SongManager instances for testing
        #self.spotify_utils = SpotifyUtils()
        # Define your credentials here
        CLIENT_ID = '7ed84fe5c068459bacefa1ba90c0871d'
        CLIENT_SECRET = '4b2d14fc86e544f7be67c7d55b4fd664'
        REDIRECT_URI = 'http://localhost:8080/callback'  # Can use the same one that caused the hang
        SCOPE = 'user-library-read'

        def connect_to_spotify():
            try:
                auth_manager = SpotifyClientCredentials(
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET
                )
                sp = spotipy.Spotify(auth_manager=auth_manager)
                return sp
            except Exception as e:
                print(f"An error occurred during Spotify connection: {e}")
                return None

        sp = connect_to_spotify()
        self.graph = ArtistGraph('server/data/nodes.js', 'server/data/edges.js', sp)
        self.song_manager = SongManager(sp)

    def test_song_path_generation(self):
        # Test case to generate a path of songs between two artists
        path_ids = self.graph.get_path('Ed Sheeran', 'Led Zeppelin')
        #print(path_ids)
        song_path = self.song_manager.get_path_of_songs(path_ids)
        expected_path = ['2DB4DdfCFMw1iaR6JaR03a', '2mKjs6s0Z1imKKb6gOk628', '4CTpAWFg3rFlOBvhMEZDVg', '3s9FRQEyUJoOsijNGiOTQQ', '5hrsqusQlSqlWpvtjJpxPq', '78lgmZwycJ3nzsdgmPPGNx']
        
        # Check if the generated song path matches the expected path
        self.assertEqual(song_path, expected_path)

if __name__ == "__main__":
    unittest.main()
