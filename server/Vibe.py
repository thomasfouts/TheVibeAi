# spotify utils
from .SpotifyUtils import *

# artist graph
from .artistgraph import ArtistGraph
from .songmanager import SongManager
from .SpotifyUtils import SpotifyUtils

# python
import getpass
import os
import spotipy

# utils
from .VibeUtils import (
    setup_openai_api,
    get_vectorstore,
    format_docs,
    configure_llm,
    PLAYLIST_PROMPT,
    DECIDE_PROMPT,
    ARTIST_PROMPT,
    END_ARTIST_PROMPT
)

# Setup OpenAI API keys
setup_openai_api()

# Load vectorstore and configure LLM
vectorstore = get_vectorstore()
retriever = vectorstore.as_retriever()
llm = configure_llm()


from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

result = []
print('Vibe loaded')

class Vibe:
    def __init__(self, sp_utils = None, sp = None, access_token = None, artist_graph = None, song_manager = None):
        print('Creating Vibe')
        self.artist_graph = artist_graph
        self.song_manager = song_manager
        self.utils = sp_utils

        if(sp):
            self.sp = sp
        elif access_token:
            # Authenticate using the user's access token
            print('Creating Spotify instance')
            self.sp = spotipy.Spotify(auth=access_token)
        
        if(sp_utils == None):
            print('Creating Spotify utils')
            self.utils = SpotifyUtils(access_token=access_token)
            
        base_dir = os.path.dirname(os.path.abspath(__file__))
        nodes_file = os.path.join(base_dir, "data/nodes.js")
        artist_top_tracks_file = os.path.join(base_dir, "data/artisttoptracks.js")
        if(self.artist_graph == None):
            print('Creating artist graph')
            self.artist_graph = ArtistGraph(nodes_file=nodes_file, access_token=access_token)
        
        if(self.song_manager == None):
            print('Creating song manager')
            self.song_manager = SongManager(artist_top_tracks_file=artist_top_tracks_file, access_token = access_token)
            

    def handle_request(self, request: str):
        llm_chain = (
                {"question": RunnablePassthrough()}
                | DECIDE_PROMPT
                | llm
                | StrOutputParser()
        )
        # Pick function using llm
        message = llm_chain.invoke(request)
        print(message)
        if "generate" in message:
            self.generate_playlist(request)
            return
        if "transition" in message:
            self.generate_queue(request)
            return
        # If the llm does not return a valid option, try again
        return self.handle_request(request)
    
    def get_songs_for_vibe(self, request: str):
        # Configure chain
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | PLAYLIST_PROMPT
            | llm
            | StrOutputParser()
        )
        # Generate solution() function using LLM
        message = rag_chain.invoke(request)
        
        # Replace 'self.sp' with 'sp' in the generated message
        message = message.replace('self.sp', 'sp')
        
        # Strip any markdown formatting that might exist
        message = message.strip("```python\n").strip("```\n")
        print(message)
        
        # Execute the generated code
        try:
            # Create a dictionary of global variables for execution context
            exec_globals = {
                "sp": self.sp,  # pass the Spotify instance to the generated code
                "result": None  # initialize result to None to avoid any NameError
            }
            exec(message + "\nresult = solution()", exec_globals)
            
            # Get the result from the execution context
            result = exec_globals["result"]
            
        except Exception as e:
            # If the LLM-generated code fails to run, retry
            print(f"An error occurred in the generated code, retrying: {e}")
            print("--------------------")
            return
        return result



    def generate_playlist(self, request: str):
        num_requests = 0
        result = []
        while len(result) == 0 and num_requests < 5:
            result = self.get_songs_for_vibe(request)
            num_requests += 1
        
        if len(result) == 0:
            print("No songs found, please try again.")
            return
        
        # Add songs to playlist
        print('Adding songs to playlist')
        playlist_name = "Vibe AI Playlist"
        playlist_description = "Automatically generated with AI"
        self.utils.make_playlist(result, playlist_name, playlist_description)
        print("Playlist created successfully.")

        
    def pick_next_artist(self, user_prompt):
        # Retrieve the current playing track
        current_track = None
        try:
            current_track_data = self.sp.current_user_playing_track()
            if current_track_data:
                current_track = current_track_data['item']['artists'][0]['name']
        except Exception as e:
            print(f"Error fetching current track: {e}")

        # Retrieve the four most recently played tracks
        recent_artists = []
        try:
            recent_tracks = self.sp.current_user_recently_played(limit=4)
            for item in recent_tracks['items']:
                artist_name = item['track']['artists'][0]['name']
                if artist_name not in recent_artists:
                    recent_artists.append(artist_name)
        except Exception as e:
            print(f"Error fetching recently played tracks: {e}")

        # Create a list of previous artists including the current artist
        previous_artists = []
        if current_track:
            previous_artists.append(current_track)
        previous_artists.extend(recent_artists)

        # Limit to a maximum of 5 artists, as required by the LLM
        previous_artists = previous_artists[:5]

        # Format previous_artists as a string for the prompt
        previous_artists_str = ", ".join(f'"{artist}"' for artist in previous_artists)

        # Prepare the input dictionary for the prompt
        input_dict = {
            "previous_artists": previous_artists_str,
            "question": user_prompt
        }

        # Use the END_ARTIST_PROMPT to determine the next artist
        llm_chain = (
            END_ARTIST_PROMPT
            | llm
            | StrOutputParser()
        )

        # Get the suggested artist from the LLM using invoke()
        next_artist = llm_chain.invoke(input_dict)

        return next_artist

   
    def generate_queue(self, user_prompt):
        # Retrieve the current playing track
        current_track_data = None
        try:
            current_track_data = self.sp.current_user_playing_track()
            if not current_track_data or not current_track_data['is_playing']:
                print("No track is currently playing.")
                return
        except Exception as e:
            print(f"Error fetching current track: {e}")
            return

        # Extract the artist of the current track
        artist1 = current_track_data['item']['artists'][0]['name']
        current_song = current_track_data['item']['id']

        # Use the pick_next_artist method to determine the next artist
        artist2 = self.pick_next_artist(user_prompt)
        try:
            path_ids = self.artist_graph.get_path(artist1, artist2)
        except Exception as e:
            print('error in vibe')
            print(artist1, artist2)
            print(f"Error fetching artist path: {e}")
            print(artist1, artist2)
            return

        # Retrieve the path of songs between the artists using SongManager
        try:
            song_path = self.song_manager.get_path_of_songs(path_ids, current_song)
        except Exception as e:
            print('error in vibe')
            print(path_ids, current_song)
            print(f"Error fetching song path: {e}")
            return

        # Add the songs in the path to the user's Spotify queue
        try:
            for song in song_path:
                self.sp.add_to_queue(song)
            print("Songs successfully songmanager songs to the queue.")
            print("Song path:", song_path)
        except Exception as e:
            print(f"Error adding songs to the queue: {e}")

        try:
            next_songs = self.get_songs_for_vibe(user_prompt)
            for song in next_songs:
                if(song not in song_path):
                    self.sp.add_to_queue(song)

            print("Songs successfully added to the queue.")
            print("Next songs:", next_songs)
                    
        except Exception as e:
            print(f"Error fetching songs for after the queue: {e}")

        