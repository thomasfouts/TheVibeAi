import json
import networkx as nx
from collections import deque
import spotipy

class ArtistGraph:
    def __init__(self, nodes_file, edges_file, access_token=None):
        self.user_artist_hist = {}
       
        self.sp = None
        if access_token:
            # Authenticate using the user's access token
            self.sp = spotipy.Spotify(auth=access_token)
        else:
            raise ValueError("Access token must be provided")

        self.get_user_artists()
        
        self.graph = nx.Graph() 
        self.load_graph(nodes_file, edges_file)
        
    def get_user_artists(self):
        try:
            results = self.sp.current_user_saved_tracks()
        except:
            return
            
        for item in results['items']:
            for artist in item['track']['artists']:
                try:
                    if artist['uri'] not in self.user_artist_hist:
                        self.user_artist_hist[artist['uri']] = 0
                    self.user_artist_hist[artist['uri']] += 1
                except:
                    continue

        
    def load_graph(self, nodes_file, edges_file):
        # Load nodes
        failed_artists = []
        artist_popularity = {}  
        with open(nodes_file, 'r') as f:
            for line in f:
                try:
                    artist = json.loads(line.strip(','))
                    artist_id = artist["uri"]
                    artist_name = artist["name"]
                    popularity = artist.get("popularity", 0)  # Default to 0 if not present
                    artist_popularity[artist_id] = popularity
                    self.graph.add_node(artist_id, name=artist_name, popularity=popularity)
                except json.JSONDecodeError:
                    failed_artists.append(line.strip())

        #print(f'failed to load {len(failed_artists)} artists')

        # Load edges
        popular_diffs = []
        with open(edges_file, 'r') as f:
            for line in f:
                try:
                    edge = json.loads(line.strip(','))
                    for artist_id, related_artists in edge.items():
                        for related_artist in related_artists:
                            if artist_id in artist_popularity and related_artist in artist_popularity:
                                popularity_diff = artist_popularity[artist_id] - artist_popularity[related_artist]
                                popular_diffs.append(popularity_diff)
                                weight = 1 + abs(popularity_diff) / 100.0
                            else:
                                weight = 1 + abs(sum(popular_diffs) / len(popular_diffs))/100
                                
                            weight /= self.user_artist_hist.get(artist_id, 1)
                            weight /= self.user_artist_hist.get(related_artist, 1)
                            
                            self.graph.add_edge(artist_id, related_artist, weight=weight)
                except json.JSONDecodeError:
                    continue
                    
        #print(sum(popular_diffs) / len(popular_diffs))

    def bfs_to_nearest_connected_artist(self, artist, sp):
        visited = set()
        queue = deque([artist])
        
        while queue:
            current_artist = queue.popleft()
            try:
                results = self.sp.artist_related_artists(current_artist)
            except Exception as e:
                print(f"Error fetching related artists: {e}")
                continue
            
            related_artist_ids = [related_artist['uri'] for related_artist in results['artists']]
            for related_artist in results['artists']:
                related_artist_id = related_artist['uri']
                if related_artist_id in self.graph:
                    # Found a connected artist
                    return related_artist_id
                if related_artist_id not in visited:
                    visited.add(related_artist_id)
                    queue.append(related_artist_id)
                    # Add this artist to the graph
                    self.graph.add_node(related_artist_id, name=related_artist['name'], popularity=related_artist.get('popularity', 0))
            
            # Update nodes.js and edges.js
            self.update_nodes_file_bulk(results['artists'])
            self.update_edges_file_bulk(current_artist, related_artist_ids)
                    
        return None


    def update_nodes_file_bulk(self, artists):
        with open('data/nodes.js', 'a') as f:
            for artist in artists:
                new_node = {
                    "genres": artist.get("genres", []),
                    "name": artist["name"],
                    "external_urls": artist.get("external_urls", {}),
                    "popularity": artist.get("popularity", 0),
                    "uri": artist["uri"],
                    "href": artist.get("href", ""),
                    "followers": artist.get("followers", {}),
                    "images": artist.get("images", []),
                    "type": artist.get("type", "artist"),
                    "id": artist.get("id", "")
                }
                f.write(json.dumps(new_node) + ',\n')

    def update_edges_file_bulk(self, current_artist, related_artist_ids):
        # Load existing edges from file
        edges = {}
        try:
            with open('data/edges.js', 'r') as f:
                for line in f:
                    line = line.strip(',\n')
                    if line:
                        edge = json.loads(line)
                        edges.update(edge)
        except FileNotFoundError:
            pass

        # Update the edges dictionary
        if current_artist in edges:
            edges[current_artist].extend([artist_id for artist_id in related_artist_ids if artist_id not in edges[current_artist]])
        else:
            edges[current_artist] = related_artist_ids

        # Write updated edges back to the file
        with open('data/edges.js', 'w') as f:
            for artist_id, related_artists in edges.items():
                f.write(json.dumps({artist_id: related_artists}) + ',\n')

    def get_path(self, artist1, artist2):
        # Find artist URIs from names
        artist1_id = self.get_artist_id_by_name(artist1)
        if artist1_id is None:
            artist1_id = self.bfs_to_nearest_connected_artist(artist1)
        artist2_id = self.get_artist_id_by_name(artist2)
        if artist2_id is None:
            artist2_id = self.bfs_to_nearest_connected_artist(artist2)

        if not artist1_id or not artist2_id:
            return []

        # Use NetworkX shortest path to find the path with weights
        try:
            path_ids = nx.shortest_path(self.graph, source=artist1_id, target=artist2_id, weight='weight')
            #names = [self.graph.nodes[artist_id]['name'] for artist_id in path_ids]
            return path_ids
            return [(artist_id, self.graph.nodes[artist_id]['name']) for artist_id in path_ids]
        except nx.NetworkXNoPath:
            return []

    def get_artist_id_by_name(self, name):
        for artist_id, data in self.graph.nodes(data=True):
            if data['name'].lower() == name.lower():
                return artist_id
        return None
