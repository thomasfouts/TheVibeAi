# spotify utils
from SpotifyUtils import *

# langchain
from langchain import hub
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI

# artist graph
from artistgraph import ArtistGraph
from songmanager import SongManager
from SpotifyUtils import SpotifyUtils

# python
import getpass
import os
import spotipy

# setup openai keys
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")

loader = WebBaseLoader(
    web_path="https://spotipy.readthedocs.io/en/2.24.0/"
)
docs = loader.load()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
splits = text_splitter.split_documents(docs)
vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings())
retriever = vectorstore.as_retriever()
prompt = hub.pull("rlm/rag-prompt")
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# configure llm
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# prompt
PLAYLIST_PROMPT_TEMPLATE = (
'''
You are a DJ assistant tasked with using the SpotiPy API to write a Python function that returns a list containing song URIs from a user prompt specifying what type of music a user wants in their playlist. Return only the function, with no other text. Make sure to add code to check that none of the returned songs have the same name. The length of the playlist should be 10 songs at most.

API LIMITATIONS TO NOTE
* When requesting track information, the limit is 50 at a time
* When requesting audio features, the limit is 100 at a time
* When selecting multiple artists, the limit is 50 at a time
* When asking for recommendations, the limit is 100 at a time

Here is an example of what the code should look like for the prompt "Make a playlist with 10 upbeat songs from The Weeknd":
def solution():
    """Make a playlist with 10 upbeat songs from The Weeknd"""
    # Search for The Weeknd's tracks
    search results = self.sp.search(q='The Weeknd', type='track', limit=50)
    tracks = search_results['tracks']['items']
    
    # Get audio features for the tracks
    track_uris = [track['uri'] for track in tracks]
    audio_features = self.sp.audio_features(track_uris)
    
    # Combine track info with audio features
    track_info = []
    for track, features in zip(tracks, audio_features):
        track_info.append({{  
            'song_name': track['name'],
            'artist_name': track['artists'][0]['name'],
            'uri': track['uri'],
            'valence': features ['valence']
        }})
        
    # Sort tracks by valence (upbeatness)
    sorted_tracks = sorted(track_info, key=lambda x: x['valence'], reverse=True)
    upbeat_tracks = sorted_tracks[:10]
    
    # Return the top 10 upbeat tracks
    output_tracks = []
    for track in upbeat_tracks:
        if track['name'] not in output_tracks:
            output_tracks.append(track['uri'])
    return output_tracks

Prompt: {question}

# solution in Python:
'''.strip()
    + "\n\n\n"
)

ARTIST_PROMPT_TEMPLATE = (
        '''
        You are a DJ assistant tasked with using the SpotiPy API to write a Python function that returns one artist URI from a user prompt specifying what artist the user wants added to their playlist. Return only the function, with no other text.
        
        API LIMITATIONS TO NOTE
        * When requesting track information, the limit is 50 at a time
        * When requesting audio features, the limit is 100 at a time
        * When selecting multiple artists, the limit is 50 at a time
        * When asking for recommendations, the limit is 100 at a time
        
        Here is an example of what the code should look like for the prompt "I want to listen to songs by The Weeknd":
        def solution():
            """I want to listen to songs by The Weeknd"""
            results = sp.search(q='The Weeknd', type='artist')
            return results['artists']['items'][0]['uri']
            

        Prompt: {question}
        
        # solution in Python:
        '''.strip()
        + "\n\n\n"
)

DECIDE_PROMPT_TEMPLATE = (
'''
You are a DJ assistant tasked with deciding which action to perform based on a user prompt. You can either generate a new playlist, or transition to a new artist. Please respond with only "generate" or "transition" depending on which action you choose.

Example 1:
Prompt: "Give me a playlist of 15 upbeat pop songs"
Reason: The user wants a playlist made with a specific genre of song
Response: generate

Example 2:
Prompt: "I want to listen to The Weeknd"
Reason: The user wants to listen to a specific artist
Response: transition

Example 3:
Prompt: "Play songs rap and hip hop songs"
Reason: The user wants to listen to a specific genre
Response: transition

Example 4:
Prompt: "Play something more upbeat that people can dance to"
Reason: The user wants to listen to a specific mood
Response: transition

Example 5:
Prompt: "Make a playlist with 10 songs that are good for studying"
Reason: The user wants a playlist made with a specific activity in mind
Response: generate

Prompt: {question}
Your Response:
'''.strip()
+ "\n\n\n"
)


END_ARTIST_TEMPLATE = (
'''
You are a DJ assistant tasked with choosing an artist for the user to listen to based on their current listening preferences and prompt. Use up to the last 5 artists the user has been listening to, as well as the prompt provided. Your response should only contain the name of the artist, with no additional text or explanations.

Considerations:
1. The user might provide a prompt that specifies mood, genre, energy, or style.
2. Use the previous artists to determine their general taste and make a suitable transition.
3. Do not include any commentary or reasoning in your response, just the artist's name.

Example 1:
Previous Artists: ["Morgan Wallen"]
Prompt: "Play country music that sounds less like pop and more acoustic and vocal"
Response: Zach Bryan

Example 2:
Previous Artists: ["Daft Punk", "Calvin Harris", "Kygo"]
Prompt: "Play something more upbeat"
Response: David Guetta

Example 3:
Previous Artists: ["Adele", "Taylor Swift", "Ed Sheeran"]
Prompt: "Play an older artist"
Response: Elton John

Example 4:
Previous Artists: ["The Beatles", "Queen", "Led Zeppelin"]
Prompt: "Play music with more energy"
Response: AC/DC

Previous Artists: {previous_artists}
Prompt: {question}
Your Response:
'''.strip()
+ "\n\n\n"
)


PLAYLIST_PROMPT = PromptTemplate(input_variables=["question"], template=PLAYLIST_PROMPT_TEMPLATE)
DECIDE_PROMPT = PromptTemplate(input_variables=["question"], template=DECIDE_PROMPT_TEMPLATE)
ARTIST_PROMPT = PromptTemplate(input_variables=["question"], template=ARTIST_PROMPT_TEMPLATE)
END_ARTIST_PROMPT = PromptTemplate(input_variables=["previous_artists", "question"], template=END_ARTIST_TEMPLATE)

result = []

class Vibe:
    def __init__(self, sp_utils = None, sp = None, access_token = None, artist_graph = None, song_manager = None):
       
        self.artist_graph = artist_graph
        self.song_manager = song_manager
        self.utils = sp_utils
        
        if(sp):
            self.sp = None
        elif access_token:
            # Authenticate using the user's access token
            self.sp = spotipy.Spotify(auth=access_token)
        
        if(sp_utils == None):
            self.utils = SpotifyUtils(access_token=access_token)
            
        if(self.artist_graph == None):
            self.artist_graph = ArtistGraph('server/data/nodes.js', 'server/data/edges.js', access_token=access_token)
        
        if(self.song_manager == None):
            self.song_manager = SongManager(artist_top_tracks_file='server/data/artisttoptracks.js', access_token = access_token)
            #SongManager(access_token=access_token)
            

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
    
    def generate_playlist(self, request: str):
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
            return self.generate_playlist(request)

        # If no results are found, try again
        if not result:
            return self.generate_playlist(request)

        # Add songs to playlist
        print('Adding songs to playlist')
        self.utils.add_songs(result)

        
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
            print(f"Error fetching artist path: {e}")
            print(artist1, artist2)
            return

        # Retrieve the path of songs between the artists using SongManager
        try:
            song_path = self.song_manager.get_path_of_songs(path_ids, current_song)
        except Exception as e:
            print(f"Error fetching song path: {e}")
            return

        # Add the songs in the path to the user's Spotify queue
        try:
            for song in song_path:
                self.sp.add_to_queue(song)
            print("Songs successfully added to the queue.")
        except Exception as e:
            print(f"Error adding songs to the queue: {e}")

        