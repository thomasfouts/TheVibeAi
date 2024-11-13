import json

class SongManager:
    def __init__(self, sp, artist_top_tracks_file='data/artisttoptracks.js'):
        self.artist_top_tracks_file = artist_top_tracks_file
        self.sp = sp
        self.artist_top_tracks = {}
        self.load_artist_top_tracks()
        self.cached_artist_tracks = {}  # Cache to store artist tracks after the first call

    def load_artist_top_tracks(self):
        # Load top tracks from the artist_top_tracks_file
        try:
            with open(self.artist_top_tracks_file, 'r') as f:
                for line in f:
                    line = line.strip(',\n')
                    if line:
                        artist_tracks = json.loads(line)
                        self.artist_top_tracks.update(artist_tracks)
        except FileNotFoundError:
            print("artist_top_tracks_file not found, starting with an empty dictionary.")

    def get_artist_top_tracks(self, artist_id):
        if artist_id in self.cached_artist_tracks:
            return self.cached_artist_tracks[artist_id]
        
        # Check if artist_id is in the artist_top_tracks dictionary
        if artist_id in self.artist_top_tracks:
            self.cached_artist_tracks[artist_id] = self.artist_top_tracks[artist_id]
            return self.artist_top_tracks[artist_id]
        
        try:
            results = self.sp.artist_top_tracks(artist_id)
            track_ids = [track['id'] for track in results['tracks']]
            self.update_artist_top_tracks_file(artist_id, track_ids)
            self.cached_artist_tracks[artist_id] = track_ids
            return track_ids
        except Exception as e:
            print(f"Error fetching top tracks for artist {artist_id}: {e}")
            return []

    def update_artist_top_tracks_file(self, artist_id, track_ids):
        # Update the artist_top_tracks_file with new track IDs
        self.artist_top_tracks[artist_id] = track_ids
        with open(self.artist_top_tracks_file, 'a') as f:
            f.write(json.dumps({artist_id: track_ids}) + ',\n')
    
    def song_difference(self, v1, v2):
        # Compute the difference between two songs based on their audio feature vectors
        weight_vector = [1, 1, 0.1, 0.5, 1, 1, 1, 1, 1, 0.01]
        difference = 0
        for i in range(len(v1)):
            difference += weight_vector[i] * (v1[i] - v2[i]) ** 2
        return difference

    def get_audio_features(self, track_ids):
        try:
            features = self.sp.audio_features(track_ids)
            return {track['id']: track for track in features if track is not None}
        except Exception as e:
            print(f"Error fetching audio features: {e}")
            return {}

    def get_audio_analysis(self, track_ids):
        audio_analysis = {}
        for track_id in track_ids:
            try:
                analysis = self.sp.audio_analysis(track_id)
                audio_analysis[track_id] = analysis
            except Exception as e:
                print(f"Error fetching audio analysis for track {track_id}: {e}")
        return audio_analysis

    def select_best_tracks(self, artist_ids, current_song=None):
        track_lists = []

        for artist_id in artist_ids:
            track_ids = self.get_artist_top_tracks(artist_id)
            if not track_ids:
                continue

            audio_features = self.get_audio_features(track_ids)
            track_vectors = [
                [
                    features['danceability'],
                    features['energy'],
                    features['loudness'],
                    features['mode'],
                    features['speechiness'],
                    features['acousticness'],
                    features['instrumentalness'],
                    features['liveness'],
                    features['valence'],
                    features['tempo']
                ]
                for track_id, features in audio_features.items() if features is not None
            ]
            track_lists.append(track_vectors)

        n = len(track_lists)
        if n == 0:
            return []

        # Dynamic programming to find the path of tracks that minimizes difference
        m = len(track_lists[0])
        dp = [[float('inf')] * len(track_lists[i]) for i in range(n)]
        choice = [[-1] * len(track_lists[i]) for i in range(n)]

        for j in range(len(track_lists[0])):
            if current_song is None or j == self.cached_artist_tracks[artist_ids[0]].index(current_song):
                dp[0][j] = 0

        for i in range(1, n):
            for j in range(len(track_lists[i])):
                for k in range(len(track_lists[i - 1])):
                    cost = self.song_difference(track_lists[i][j], track_lists[i - 1][k])
                    if dp[i][j] > dp[i - 1][k] + cost:
                        dp[i][j] = dp[i - 1][k] + cost
                        choice[i][j] = k

        min_cost = float('inf')
        last_choice = -1
        for j in range(len(track_lists[n - 1])):
            if dp[n - 1][j] < min_cost:
                min_cost = dp[n - 1][j]
                last_choice = j

        # Reconstruct the path
        result_indices = [None] * n
        result_indices[n - 1] = last_choice
        for i in range(n - 2, -1, -1):
            last_choice = choice[i + 1][last_choice]
            result_indices[i] = last_choice

        # Get the track IDs
        selected_tracks = []
        for i in range(n):
            track_ids = self.cached_artist_tracks.get(artist_ids[i], [])
            if result_indices[i] is not None and result_indices[i] < len(track_ids):
                selected_tracks.append(track_ids[result_indices[i]])

        return selected_tracks

    def get_path_of_songs(self, artist_path, current_song=None):
        # Given a list of artist UIDs, generate a path of songs
        artist_ids = artist_path 
        return self.select_best_tracks(artist_ids, current_song)
