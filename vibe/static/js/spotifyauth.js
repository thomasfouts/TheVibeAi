// https://github.com/kevin51jiang/react-spotify-auth

import React, { useState } from 'react';
import { SpotifyAuth } from 'react-spotify-auth';
import 'react-spotify-auth/dist/index.css'; // Import CSS for the login button
import './App.css'; // Import your custom CSS if needed

const clientId = '888537acce5947688ead39862ef45b7d';
const redirectUri = 'http://localhost:8000';
const scopes = ['user-read-currently-playing', 'user-read-playback-state'];

function App() {
  const [token, setToken] = useState(null);

  return (
    <div className="App">
      <header className="App-header">
        {!token ? (
          <>
            <h1>Spotify Web Player</h1>
            <h2>Login to view your currently playing songs</h2>
            <SpotifyAuth
              redirectUri={redirectUri}
              clientID={clientId}
              scopes={scopes}
              onAccessToken={(token) => {
                setToken(token);
                window.localStorage.setItem('spotifyAuthToken', token);
              }}
            />
          </>
        ) : (
          <div>
            <h1>Welcome!</h1>
            <p>Your Spotify token is: {token}</p>
          </div>
        )}
      </header>
    </div>
  );
}

export default App;
