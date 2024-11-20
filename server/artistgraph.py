import json
import networkx as nx
from collections import deque
import spotipy
import math
from scipy.spatial.distance import euclidean
import pandas as pd
import numpy as np
from scipy.stats import gaussian_kde
import os


class ArtistGraph:
    def __init__(self, nodes_file, access_token=None):
        # Resolve base directory for the current file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Define paths relative to the base directory
        weighted_edges_file = os.path.join(base_dir, "data/base_edge_weights.json")
        unweighted_edges_file = os.path.join(base_dir, "data/edges.js")
        self.sp = None
        if access_token:
            # Authenticate using the user's access token
            self.sp = spotipy.Spotify(auth=access_token)
        else:
            raise ValueError("Access token must be provided")

        self.global_max_density = None
        self.genre_coordinates = None
        self.genre_densities = None
        self.use_user_data = True
        self.load_constants()
        
        self.graph = nx.Graph() 
        self.load_graph(nodes_file, weighted_edges_file, unweighted_edges_file)

    def load_constants(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
        enao_path = os.path.join(base_dir, "enao-genres-latest.csv")
        print('loading constants')
        enao_df = pd.read_csv(enao_path)
        enao_df['top'] = pd.to_numeric(enao_df['top'].str.replace('px', ''), errors='coerce')
        enao_df['left'] = pd.to_numeric(enao_df['left'].str.replace('px', ''), errors='coerce')
        enao_df['top'] = np.interp(enao_df['top'], (enao_df['top'].min(), enao_df['top'].max()), (100, 0))
        enao_df['left'] = np.interp(enao_df['left'], (enao_df['left'].min(), enao_df['left'].max()), (0, 100))
    
        all_coords = np.vstack([enao_df['left'], enao_df['top']])
        kde = gaussian_kde(all_coords)
        
        # Precompute maximum density across all genres in enao_df for normalization
        all_genre_densities = kde(all_coords).ravel()
        global_max_density = np.max(all_genre_densities)
        
        # Precompute genre coordinates and distances
        genre_coordinates = {
            row['genre']: (row['left'], row['top'])
            for _, row in enao_df.iterrows()
        }
        
        genre_densities = {}
        for genre in genre_coordinates.keys():
            left, top = genre_coordinates[genre]
            density = kde(np.array([[left], [top]]))[0]  # Extract the density value
            genre_densities[genre] = density
    
        self.global_max_density = global_max_density
        self.genre_coordinates = genre_coordinates
        self.genre_densities = genre_densities

        
    def load_graph(self, nodes_file, weighted_edges_file, unweighted_edges_file, user_data = True):
        print('loading graph')
        artist_data = {}
        with open(nodes_file, 'r') as f:
            for line in f:
                try:
                    artist = json.loads(line.strip(','))
                    artist_id = artist["uri"]
                    artist_name = artist["name"]
                    popularity = artist.get("popularity", 0)  # Default to 0 if not present
        
                    
                    #artist_popularity[artist_id] = popularity
                    genres = artist["genres"]
                    artist_data[artist_id] = {'popularity': popularity, 'genres':genres}
        
                    self.graph.add_node(artist_id, name = artist_name, popularity = popularity, genres = genres)
        
                    # #self.graph.add_node(artist_id, name=artist_name, popularity=popularity)
                except json.JSONDecodeError:
                    continue
        
        print('finished nodes, starting edges')
        # Precompute the edge weights and save to a JSON file
        if(not os.path.exists(weighted_edges_file)):
            print('Computing base weight for edges')
            self.get_base_edge_weights(artist_data, edges_file= unweighted_edges_file, weighted_edges_file=weighted_edges_file)
            
        
        #Load weighted edges from json file
        weight_scale = [0.8,1.5,1.2]
        #weighted_edges_file = 'data/base_edge_weights.json'
        with open(weighted_edges_file, 'r') as f:
            for line in f:
                try:
                    edge = json.loads(line.strip(','))
                    for artist1_id, related_artists in edge.items():
                        if artist1_id not in artist_data:
                            continue
                        
                        artist1 = artist_data[artist1_id]
                        for artist2_id, weights in related_artists.items():
                            try:
                                artist2 = artist_data[artist2_id]
                                pd_weight = weights['pd_weight']*weight_scale[0]
                                gs_weight = weights['gs_weight']*weight_scale[1]
                                weight = 1 + pd_weight + gs_weight
                            except:
                                continue

                            if(user_data): 
                                gd_weight = self.get_genre_density(artist1, artist2)*weight_scale[2]
                                weight += gd_weight
    
                            weight = max(0.0000001, weight)
                            self.graph.add_edge(artist1_id, artist2_id, weight=weight)
    
                            #ALL_WEIGHTS.append(weight)
                                
                except json.JSONDecodeError:
                    continue

    def get_base_edge_weights(self, artist_data, edges_file='server/data/edges.js', weighted_edges_file='server/data/base_edge_weights.json'):
        base_edge_weights = {}
        with open(edges_file, 'r') as f:
            for line in f:
                try:
                    edge = json.loads(line.strip(','))
                    for artist1_id, related_artists in edge.items():
                        if artist1_id not in artist_data:
                            continue
    
                        base_edge_weights[artist1_id] = {}
                        
                        artist1 = artist_data[artist1_id]
                        for artist2_id in related_artists:
                            if artist2_id not in artist_data:
                                continue
                            
                            artist2 = artist_data[artist2_id]
                            # Compute the popularity_diff_weight and genre_similarity_weight
                            pd_weight, gs_weight = self.compute_base_edge_weight(artist1, artist2)
    
                            base_edge_weights[artist1_id][artist2_id] ={'pd_weight':pd_weight, 'gs_weight':gs_weight}
                            
        
                except json.JSONDecodeError:
                    continue
                    
        with open(weighted_edges_file, 'w') as json_file:
            for artist_id, related_artists in base_edge_weights.items():
                # Create a dictionary for the artist and related artists
                line = json.dumps({artist_id: related_artists})
                json_file.write(line + '\n')

    def compute_base_edge_weight(self, artist1, artist2):
        # Extract popularity
        smoothed_popularity_diff = 1
        try:
            popularity_diff = artist1["popularity"] - artist2["popularity"]
            smoothed_popularity_diff = 1 / (1 + math.exp(-popularity_diff)) #sigmoid
        except:
            pass
    
        # Calculate genre similarity
        x1, y1, x2, y2 = None, None, None, None
        artist1_coords = []
        for genre in artist1["genres"]:
            try:
                artist1_coords.append(self.genre_coordinates[genre])
            except:
                continue
        if(len(artist1_coords) > 0):
            x1 = sum([x[0] for x in artist1_coords])/len(artist1_coords)
            y1 = sum([x[1] for x in artist1_coords])/len(artist1_coords)
        
        artist2_coords = []
        for genre in artist2["genres"]:
            try:
                artist2_coords.append(self.genre_coordinates[genre])
            except:
                continue
        if(len(artist2_coords)>0):
            x2 = sum([x[0] for x in artist2_coords])/len(artist2_coords)
            y2 = sum([x[1] for x in artist2_coords])/len(artist2_coords)
    
        genre_similarity_weight = 1
        if(x1 and x2):
            distance = euclidean((x1,y1), (x2,y2))
            genre_similarity_weight = distance / 100
    
        return smoothed_popularity_diff, genre_similarity_weight

    # Function to calculate the edge weight between two artists
    def calculate_artist_density(self, artist_genres): # , enao_df, kde, favorite_genres=None):
        # Initialize a list to store density values for each genre
        densities = []
        for genre in artist_genres:
            if(genre in self.genre_densities):
                densities.append(self.genre_densities[genre])
        if(densities):
            #normalized_densities = [density / global_max_density for density in densities]
            probability = np.mean(densities)/self.global_max_density
        else:
            probability = 0
        #probability = 1 / (1 + np.exp(-1 * (probability - 0.5)))
        # Linear scaling to expand the range of probability weights
    
        probability = 0.5 + 0.5 * (probability - 0.5)  # Scale to get a wider range
        return probability
        
    def get_genre_density(self, artist1, artist2):
        artist1_probability, artist2_probability = 0, 0
        # Calculate artist probability based on user's listening history
        if(len(artist1.get('genres',[])) > 0):
            artist1_probability = self.calculate_artist_density(artist1["genres"])
        if(len(artist2.get('genres',[])) > 0):
            artist2_probability = self.calculate_artist_density(artist2["genres"])
        
        average_probability = (artist1_probability + artist2_probability)/1.5
        return max(0, 1 - (average_probability))  # Scale to adjust the weight
        #return max(probability_weight, 0.000001)

    def add_new_edge(self, artist1, artist2, weight_scale = [0.8,1.5,1.2]):
        pd_weight, gs_weight = self.compute_base_edge_weight(artist1, artist2)
        weight = 1 + pd_weight*weight_scale[0] + gs_weight*weight_scale[1]

        if(self.use_user_data):
            gd_weight = self.get_genre_density(artist1, artist2)*weight_scale[2]
            weight += gd_weight
        
        artist1_id = artist1['uri']
        artist2_id = artist2['uri']
        weight = max(0.0000001, weight)
        self.graph.add_edge(artist1_id, artist2_id, weight=weight)


    def bfs_to_nearest_connected_artist(self, artist_name):
        print('BFS for artist: ', artist_name)
        try:
            search_results = self.sp.search(q=artist_name, type ='artist', limit=1)
            artist = search_results['artists']['items'][0]
        except Exception as e:
            print(f"Error from spotify fetching artist: {e}")
            return None
        
        artist_id = artist['uri']
        visited = set()
        queue = deque([artist])
        
        while queue:
            current_artist = queue.popleft()
            current_artist_id = current_artist['uri']
            try:
                results = self.sp.artist_related_artists(current_artist_id)
            except Exception as e:
                print(f"Error fetching related artists: {e}")
                continue
            
            #related_artist_ids = [related_artist['uri'] for related_artist in results['artists']]
            for related_artist in results['artists']:
                related_artist_id = related_artist['uri']
                if related_artist_id in self.graph:
                    self.add_new_edge(current_artist, related_artist)
                    return artist_id
                if related_artist_id not in visited:
                    visited.add(related_artist_id)
                    queue.append(related_artist_id)
                    # Add this artist to the graph
                    self.graph.add_node(related_artist_id, name=related_artist['name'], popularity=related_artist.get('popularity', 0), genres=related_artist.get('genres', []))
                    self.add_new_edge(current_artist, related_artist)
            
            # Update nodes.js and edges.js
            # self.update_nodes_file_bulk(results['artists'])
            # self.update_edges_file_bulk(current_artist, related_artist_ids)
                    
        return None


    def update_nodes_file_bulk(self, artists):
        with open('server/data/nodes.js', 'a') as f:
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
            with open('server/data/edges.js', 'r') as f:
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
        with open('server/data/edges.js', 'w') as f:
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
