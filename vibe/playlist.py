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

# spotipy
import spotipy
from spotipy import CacheFileHandler, prompt_for_user_token
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util as util

# python
import getpass
import os

# setup openai keys
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")

# setup spotify keys
if not os.environ.get("SPOTIPY_CLIENT_ID"):
    os.environ["SPOTIPY_CLIENT_ID"] = getpass.getpass("Enter your SpotiPy Client ID: ")
if not os.environ.get("SPOTIPY_CLIENT_SECRET"):
    os.environ["SPOTIPY_CLIENT_SECRET"] = getpass.getpass("Enter your SpotiPy Client Secret: ")
username = input("What is your Spotify username?\n")
token = prompt_for_user_token(
    username=username,
    scope='playlist-modify-private, playlist-modify-public',
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
SPOTIPY_PROMPT_TEMPLATE = (
'''
You are a DJ assistant tasked with using the SpotiPy API to write a Python function that returns a dictionary containing track, artist, and URI from a user prompt specifying what type of music a user wants in their playlist. Return only the function, with no other text. The keys in the returned dictionary should be 'song_name', 'artist_name', and 'uri'.

API LIMITATIONS TO NOTE
* When requesting track information, the limit is 50 at a time
* When requesting audio features, the limit is 100 at a time
* When selecting multiple artists, the limit is 50 at a time
* When asking for recommendations, the limit is 100 at a time

Here is an example of what the code should look like for the prompt "List the 3 most downbeat songs from The Clash's Combat Rock":
def solution():
    """List the 3 most downbeat songs from The Clash's Combat Rock"""
    # Get the URI for the album
    search_results = sp.search(q='The Clash Combat Rock', type='album')
    album = search_results['albums']['items'][0]
    album_uri = album['uri']
    # Get the album tracks
    album_tracks = sp.album_tracks(album_uri)['items']
    # Sort the tracks by valence (downbeatness)
    tracks = []
    for i, track in enumerate(album_tracks):
        audio_details = sp.audio_features([track['uri']])[0]
        tracks.append({{
            'song_name': track.get('name'),
            'artist_name': track.get('artist'),
            'song_uri': track.get('uri'),
        }})
    sorted_tracks = sorted(tracks, key=lambda x: x['valence'])
    downbeat_tracks = sorted_tracks[:3]
    return downbeat_tracks

Prompt: {question}

# solution in Python:
'''.strip()
    + "\n\n\n"
)

PROMPT = PromptTemplate(input_variables=["question"], template=SPOTIPY_PROMPT_TEMPLATE)
result = []

rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | PROMPT
        | llm
        | StrOutputParser()
)

class Playlist:
    playlist_songs = []
    def __init__(self):
        # create playlist on user account
        playlist_name = "Vibe AI Playlist"
        playlist_description = "Automatically generated with AI"
        self.playlist_id = sp.user_playlist_create(username, playlist_name, public=True, description=playlist_description)["id"]

    def generate_playlist(self, request : str):
        # Generate solution() function using llm
        message = rag_chain.invoke(request)
        message = message.strip("```python\n").strip("```\n")
        # print(message)
        # Run solution() function to get dict of songs
        try:
            exec(message + "\nresult = solution()", globals())
        except:
            # If the llm generated code fails to run, try again
            print("An error occured in the generated code, retrying")
            return self.generate_playlist(request)
        # If no results are found, try again
        if not result:
            self.generate_playlist(request)

        # add songs to playlist
        self.playlist_songs.append(result)
        print("Your playlist: ")
        for line in result:
            print("Name: " + line['song_name'])
            print("Artist: " + line['artist_name'])
            sp.playlist_add_items(self.playlist_id, [line['uri']])

    def transition_songs(self, request : str):
        # todo: figure out how to transition between requests with the song history
        pass

# for testing
def main():
    dj = Playlist()
    dj.generate_playlist(input("What would you like me to play?\n"))
    # Make a playlist with 5 upbeat songs from The Weeknd

if __name__=="__main__":
    main()