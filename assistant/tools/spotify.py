import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os


os.environ['SPOTIPY_CLIENT_ID'] = '1623bb0d6fa24a8fbe4d8bf3eff226f9'
os.environ['SPOTIPY_CLIENT_SECRET'] = '3789fe6c0113432499076997c95362e2'
os.environ['SPOTIPY_REDIRECT_URI'] = 'http://localhost:8000'
scope = "user-read-playback-state,user-modify-playback-state"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))


def play_song(song_name, artist_name=None, device_name="dell") -> str:
    """
    Play a song on the specified device.

    Args:
        song_name (str): Name of the song to play
        artist_name (str, optional): Name of the artist (helps with search accuracy)
        device_name (str, optional): Name of the device to play on (defaults to "dell")
    """
    print(song_name)
    devices = sp.devices()
    device_id = None

    for device in devices['devices']:
        if device['name'].lower() == device_name.lower():
            device_id = device['id']
            break

    if not device_id:
        return "Device not found"

    # Search for the song
    query = song_name
    if artist_name:
        query += f" artist:{artist_name}"

    results = sp.search(q=query, type="track", limit=1)

    if not results['tracks']['items']:
        return "Song not found"

    track_uri = results['tracks']['items'][0]['uri']

    sp.start_playback(device_id=device_id, uris=[track_uri])

    return "OK"


# Stop playback
def stop_playback(device_name="dell") -> str:
    """
    Stop the current playback on the specified device.

    Args:
        device_name (str, optional): Name of the device (defaults to "dell")
    """
    # Get device ID
    devices = sp.devices()
    device_id = None

    for device in devices['devices']:
        if device['name'].lower() == device_name.lower():
            device_id = device['id']
            break

    if not device_id:
        return "Device not found"

    try:
        sp.pause_playback(device_id=device_id)
        return "Playback stopped"
    except Exception as e:
        return "Error occured"


def change_volume(percent: float = 0.1, device_name: str = "dell"):
    """
    Increase the volume by 10% on the specified device.

    Args:
        percent: By how many percent to increase or decrease the volume
        device_name (str, optional): Name of the device (defaults to "dell")
    """
    devices = sp.devices()
    device_id = None
    current_volume = None

    for device in devices['devices']:
        if device['name'].lower() == device_name.lower():
            device_id = device['id']
            current_volume = device['volume_percent']
            break

    if not device_id:
        return {"error": f"Device '{device_name}' not found"}

    new_volume = min(100, current_volume * (1 + percent))

    sp.volume(new_volume, device_id=device_id)

    return "OK"



def previous_song(device_name="dell"):
    """
    Skip to the previous song on the specified device.

    Args:
        device_name (str, optional): Name of the device (defaults to "dell")
    """
    # Get device ID
    devices = sp.devices()
    device_id = None

    for device in devices['devices']:
        if device['name'].lower() == device_name.lower():
            device_id = device['id']
            break

    if not device_id:
        return {"error": f"Device '{device_name}' not found"}

    try:
        sp.previous_track(device_id=device_id)

        # Get current track info
        current_playback = sp.current_playback()
        if current_playback and current_playback.get('item'):
            track_name = current_playback['item']['name']
            artist_name = current_playback['item']['artists'][0]['name']
            return {
                "success": True,
                "message": f"Skipped to previous track: {track_name} by {artist_name}"
            }
        else:
            return {"success": True, "message": "Skipped to previous track"}
    except Exception as e:
        return {"error": str(e)}


# Go to next song
def next_song(device_name="dell"):
    """
    Skip to the next song on the specified device.

    Args:
        device_name (str, optional): Name of the device (defaults to "dell")
    """
    # Get device ID
    devices = sp.devices()
    device_id = None

    for device in devices['devices']:
        if device['name'].lower() == device_name.lower():
            device_id = device['id']
            break

    if not device_id:
        return {"error": f"Device '{device_name}' not found"}

    try:
        sp.next_track(device_id=device_id)

        # Get current track info
        current_playback = sp.current_playback()
        if current_playback and current_playback.get('item'):
            track_name = current_playback['item']['name']
            artist_name = current_playback['item']['artists'][0]['name']
            return {
                "success": True,
                "message": f"Skipped to next track: {track_name} by {artist_name}"
            }
        else:
            return {"success": True, "message": "Skipped to next track"}
    except Exception as e:
        return {"error": str(e)}


if __name__ == '__main__':
    play_song('Ghost Division', artist_name='Sabaton')
