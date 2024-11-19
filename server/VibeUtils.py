import os
import getpass
from langchain import hub
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI

# Setup OpenAI API keys
def setup_openai_api():
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")

# Load and create vectorstore for retriever
def get_vectorstore():
    loader = WebBaseLoader(web_path="https://spotipy.readthedocs.io/en/2.24.0/")
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    return Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings())

# Configure LLM
def configure_llm():
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

# Utility function to format documents
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# Prompt templates

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
