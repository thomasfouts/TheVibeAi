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
        } else {
            console.error('Failed to connect to Spotify.');
            document.getElementById("status-message").innerText = 'Failed to connect to Spotify.';
        }
    });
};

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


function togglePlay() {
    player.getCurrentState().then(state => {
        if (!state) {
            console.error('User is not connected to the player.');
            document.getElementById("status-message").innerText = 'User is not connected to the player.';
            return;
        }

        if (state.paused) {
            player.resume().then(() => {
                console.log('Playback resumed');
                document.getElementById("status-message").innerText = 'Playback resumed.';
            }).catch(error => {
                console.error('Failed to resume playback:', error);
                document.getElementById("status-message").innerText = 'Failed to resume playback. See console.';
            });
        } else {
            player.pause().then(() => {
                console.log('Playback paused');
                document.getElementById("status-message").innerText = 'Playback paused.';
            }).catch(error => {
                console.error('Failed to pause playback:', error);
                document.getElementById("status-message").innerText = 'Failed to pause playback. See console.';
            });
        }
    });
}
