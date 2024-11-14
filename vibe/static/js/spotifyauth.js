// https://github.com/kevin51jiang/react-spotify-auth
import React from 'react';
import { SpotifyAuth, Scopes } from 'react-spotify-auth';
import 'react-spotify-auth/dist/index.css'; // CSS for the login button
import Cookies from 'universal-cookie';

const cookies = new Cookies();

const App = () => {
  const token = cookies.get('spotifyAuthToken');

  return (
    <div>
      {token ? (
        <div>
          <h1>You're authenticated!</h1>
          {/* Use the token to fetch data from Spotify's Web API */}
        </div>
      ) : (
        <SpotifyAuth
          redirectUri="http://localhost:3000/callback"
          clientID="888537acce5947688ead39862ef45b7d"
          scopes={[Scopes.userReadPrivate, Scopes.userReadEmail]} // Replace with your desired scopes
          onAccessToken={(accessToken) => console.log('Access Token:', accessToken)}
        />
      )}
    </div>
  );
};

export default App;
