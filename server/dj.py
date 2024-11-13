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

# python
import getpass
import os

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
    search results = sp.search(q='The Weeknd', type='track', limit=50)
    tracks = search_results['tracks']['items']
    
    # Get audio features for the tracks
    track_uris = [track['uri'] for track in tracks]
    audio_features = sp.audio_features(track_uris)
    
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
Reason: The user wants to listen to a specific genre of song
Response: generate

Example 2:
Prompt: "I want to listen to The Weeknd"
Reason: The user wants to listen to a specific artist
Response: transition

Prompt: {question}
Your Response:
'''.strip()
+ "\n\n\n"
)

PLAYLIST_PROMPT = PromptTemplate(input_variables=["question"], template=PLAYLIST_PROMPT_TEMPLATE)
DECIDE_PROMPT = PromptTemplate(input_variables=["question"], template=DECIDE_PROMPT_TEMPLATE)
ARTIST_PROMPT = PromptTemplate(input_variables=["question"], template=ARTIST_PROMPT_TEMPLATE)
result = []

class DJ:
    def __init__(self):
        self.utils = SpotifyUtils()

    def handle_request(self, request: str):
        # If no songs are in the playlist, we need to generate a playlist
        if len(self.utils.playlist_uri) == 0:
            self.generate_playlist(request)
            return
        # Configure chain
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
            self.transition_songs(request)
            return
        # If the llm does not return a valid option, try again
        return self.handle_request(request)

    def generate_playlist(self, request : str):
        # Configure chain
        rag_chain = (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
                | PLAYLIST_PROMPT
                | llm
                | StrOutputParser()
        )
        # Generate solution() function using llm
        message = rag_chain.invoke(request)
        message = message.strip("```python\n").strip("```\n")
        print(message)
        # Run solution() function to get dict of songs
        try:
            exec(message + "\nresult = solution()", globals())
        except:
            # If the llm generated code fails to run, try again
            print("An error occurred in the generated code, retrying")
            return self.generate_playlist(request)
        # If no results are found, try again
        if not result:
            return self.generate_playlist(request)

        # add songs to playlist
        self.utils.add_songs(result)

    def transition_songs(self, request : str):
        next_artist = self.find_artist(request)
        prev_artist = self.utils.get_last_artist()
        print(prev_artist)
        print(next_artist)
        # todo: call function here to transition between artists
        # self.utils.add_songs(result)

    def find_artist(self, request : str):
        # Configure chain
        rag_chain = (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
                | ARTIST_PROMPT
                | llm
                | StrOutputParser()
        )
        # Generate solution() function using llm
        message = rag_chain.invoke(request)
        message = message.strip("```python\n").strip("```\n")
        print(message)
        # Run solution() function to get artist uri
        try:
            exec(message + "\nresult = solution()", globals())
        except:
            # If the llm generated code fails to run, try again
            print("An error occured in the generated code, retrying")
            return self.find_artist(request)
        # If no results are found, try again
        if not result:
            return self.find_artist(request)
        return result

# for testing
def main():
    dj = DJ()
    while(True):
        dj.handle_request(input("What would you like me to play?\n"))
        dj.utils.print_playlist()
        # Make a playlist with 5 upbeat songs from The Weeknd

if __name__=="__main__":
    main()