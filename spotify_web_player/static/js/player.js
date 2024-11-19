let player;

window.onSpotifyWebPlaybackSDKReady = () => {
    const token = document.getElementById('spotify-token').value;

    if (!token) {
        console.error("Access token is not available.");
        document.getElementById("status-message").innerText = 'Access token not found. Please login again.';
        return;
    }

    console.log("Spotify Web Playback SDK is ready.");
    console.log("Access Token:", token);

    player = new Spotify.Player({
        name: 'Flask Spotify Web Player',
        getOAuthToken: cb => { 
            console.log('Getting OAuth token...');
            cb(token); 
        },
        volume: 0.5
    });

    // Add event listeners
    player.addListener('ready', ({ device_id }) => {
        console.log('Player is ready with Device ID:', device_id);
        document.getElementById("play-button").dataset.deviceId = device_id;

        // Set this device as the active device
        setActiveDevice(token, device_id);
    });

    player.addListener('not_ready', ({ device_id }) => {
        console.log('Device ID has gone offline:', device_id);
    });

    player.addListener('player_state_changed', state => {
        if (state) {
            console.log('Player state changed:', state);
        } else {
            console.log('No player state information available.');
        }
    });

    player.addListener('initialization_error', ({ message }) => {
        console.error('Failed to initialize:', message);
        document.getElementById("status-message").innerText = 'Failed to initialize player. Please check logs.';
    });

    player.addListener('authentication_error', ({ message }) => {
        console.error('Failed to authenticate:', message);
        document.getElementById("status-message").innerText = 'Failed to authenticate. Check scopes or token.';
    });

    player.addListener('account_error', ({ message }) => {
        console.error('Failed to validate Spotify account:', message);
        document.getElementById("status-message").innerText = 'Failed to validate Spotify account. Ensure you have Spotify Premium.';
    });

    player.addListener('playback_error', ({ message }) => {
        console.error('Failed to perform playback:', message);
        document.getElementById("status-message").innerText = 'Playback error occurred. See console for details.';
    });

    // Connect the player
    player.connect().then(success => {
        if (success) {
            console.log('The Web Playback SDK successfully connected to Spotify!');
            document.getElementById("status-message").innerText = 'Player connected to Spotify. Select it as the active device.';
            fetchCurrentSong();  // Fetch the current song when the player is connected
        } else {
            console.error('Failed to connect to Spotify.');
            document.getElementById("status-message").innerText = 'Failed to connect to Spotify.';
        }
    });
};

// Function to set the active device
function setActiveDevice(token, device_id) {
    console.log('Activating device with Device ID:', device_id);
    fetch('https://api.spotify.com/v1/me/player', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            device_ids: [device_id],
            play: true  // Set to true to immediately start playback, or false if you want to activate without playing
        })
    }).then(response => {
        if (response.ok) {
            console.log('Device activated successfully.');
            document.getElementById("status-message").innerText = 'Device activated and ready to play.';
        } else {
            console.error('Failed to activate device:', response.status, response.statusText);
            response.json().then(data => {
                console.error('Detailed error:', data);
                document.getElementById("status-message").innerText = 'Failed to activate device. See console for details.';
            });
        }
    }).catch(error => {
        console.error('Error activating device:', error);
        document.getElementById("status-message").innerText = 'Error activating device. See console for details.';
    });
}
// Variable to track the play/pause state
let isPlaying = false;

// Function to toggle play/pause
function togglePlay() {
    const playButton = document.getElementById('play-button');
    
    player.getCurrentState().then(state => {
        if (!state) {
            console.error('User is not connected to the player.');
            document.getElementById("status-message").innerText = 'User is not connected to the player.';
            return;
        }

        // If the playback is paused, resume it; if it’s playing, pause it.
        if (state.paused) {
            player.resume().then(() => {
                console.log('Playback resumed');
                document.getElementById("status-message").innerText = 'Playback resumed.';
                playButton.textContent = '❚❚';  // Change to pause symbol
                isPlaying = true;
            }).catch(error => {
                console.error('Failed to resume playback:', error);
                document.getElementById("status-message").innerText = 'Failed to resume playback. See console.';
            });
        } else {
            player.pause().then(() => {
                console.log('Playback paused');
                document.getElementById("status-message").innerText = 'Playback paused.';
                playButton.textContent = '►';  // Change to play symbol
                isPlaying = false;
            }).catch(error => {
                console.error('Failed to pause playback:', error);
                document.getElementById("status-message").innerText = 'Failed to pause playback. See console.';
            });
        }
    });
}

// Function to fetch current song data from the backend
function fetchCurrentSong() {
    fetch('/current_song')
        .then(response => response.json())
        .then(data => {
            console.log('Fetched current song data:', data);  // Log the data for debugging
            
            // Check if the song and artist information is present
            const songName = data.song_name || "No song playing";
            const artistName = data.artist_name || "Unknown artist";
            
            // Update the UI with song and artist name
            document.getElementById('song-name').textContent = songName;
            document.getElementById('artist-name').textContent = artistName;
            document.getElementById('album-image').src = data.album_image_url;
        })
        .catch(error => console.error('Error fetching current song:', error));
}

// Set an interval to periodically update the current song
setInterval(fetchCurrentSong, 10000);  // Fetch every 10 seconds
