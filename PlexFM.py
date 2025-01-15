import discord
from discord.ext import commands, tasks
from plexapi.server import PlexServer
import asyncio
import pylast
import time

# Set up Plex connection
PLEX_URL = '<<YOUR PLEX URL>>'
PLEX_TOKEN = '<<PLEX API TOKEN>>'
plex = PlexServer(PLEX_URL, PLEX_TOKEN)

# Set up Last.fm connection using pylast
API_KEY = "<<YOUR LAST.FM API_KEY>>"
API_SECRET = "<<YOUR LAST.FM API_SECRET>>"
username = "<<YOUR LAST.FM USERNAME>>"
password_hash = pylast.md5("<<YOUR LAST.FM PASSWORD>>")
network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET, username=username, password_hash=password_hash)

# Setup Discord client
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Function to format seconds into MM:SS
def format_time(seconds):
    minutes = seconds // 60  # Integer division for minutes
    remaining_seconds = int(seconds % 60)  # Remainder for seconds
    return f"{int(minutes):02}:{remaining_seconds:02}"
    
# Function to get current song and playback time
def get_current_song():
    try:
        # Get the current playing media
        playing = plex.sessions()
        
        # Debugging: Log the list of sessions to see what data we are getting
        print(f"Current sessions: {playing}")

        # Check if there is any media playing
        if playing:
            # Get the first playing session
            current_playing = playing[0]
            
            # Debugging: Log the type and full details of the session
            print(f"Current session type: {current_playing.type}")  # Log the type of media
            print(f"Current session details: {current_playing}")  # Log all the session details
            
            # Look for more detailed classification of the media
            print(f"Current session 'Media Type': {getattr(current_playing, 'mediaType', 'Unknown')}")
            print(f"Current session 'Is Music': {getattr(current_playing, 'isMusic', 'Unknown')}")

            # Check if it's a music track
            if 'track' in current_playing.type.lower() or getattr(current_playing, 'mediaType', '').lower() == 'music':
                # Try fetching more details about the media (e.g., artist, album, etc.)
                song_title = current_playing.title
                artist_name = current_playing.grandparentTitle  # or use 'parentTitle' if appropriate
                album_name = current_playing.parentTitle  # or adjust based on Plex data structure
                current_time_seconds = current_playing.viewOffset / 1000 # Use viewOffset instead of time for playback position
                formatted_time = format_time(current_time_seconds)  # Convert seconds to MM:SS format


                if not artist_name:
                    artist_name = "Unknown Artist"

                song_details = {
                    "title": song_title,
                    "artist": artist_name,
                    "album": album_name,
                    "current_time": formatted_time
                }

                print(f"Currently playing song: {song_title} by {artist_name}, Time: {formatted_time}")  # Debugging: Log the song title and artist
                return song_details
            else:
                print("Currently playing media is not a music track.")  # Debugging: Log when it's not a music track
                return None
        else:
            print("No media is currently playing.")  # Debugging: Log when no media is playing
            return None
    except Exception as e:
        print(f"Error retrieving current song: {e}")  # Log the error if any
        return None

# Convert formatted time (MM:SS) to seconds
def time_to_seconds(formatted_time):
    minutes, seconds = map(int, formatted_time.split(":"))
    return minutes * 60 + seconds

# Function to update Discord Rich Presence
@tasks.loop(seconds=10)
async def update_presence():
    song_data = get_current_song()
    if song_data:
        song_title = song_data["title"]
        artist = song_data["artist"]
        formatted_time = song_data["current_time"]
        
        # Convert formatted time (MM:SS) to seconds
        current_time_seconds = time_to_seconds(formatted_time)  # Now this is in seconds

        print(f"Updating presence: {song_title} by {artist} ({current_time_seconds}s)")  # Debugging line
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name=f"{song_title} by {artist} \n({formatted_time})")
        )
    else:
        print("Nothing playing. Updating presence.")  # Debugging line
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Nothing playing"))


# Function to scrobble the song to Last.fm using pylast
def scrobble_to_lastfm(song_title, artist_name, timestamp):
    try:
        track = network.get_track(artist_name, song_title)
        track.scrobble(timestamp=timestamp)
        print(f"Scrobbled {song_title} by {artist_name} to Last.fm.")
    except Exception as e:
        print(f"Error scrobbling to Last.fm: {e}")

# Monitor playback and scrobble when a song ends (Asynchronous)
async def monitor_playback():
    previous_song = None
    while True:
        song_data = get_current_song()
        if song_data:
            song_title = song_data["title"]
            if song_title != previous_song:
                if previous_song:
                    scrobble_to_lastfm(previous_song, song_data["artist"], time.time())
                previous_song = song_title
        await asyncio.sleep(10)  # Sleep asynchronously without blocking the event loop

# Start the loop and monitoring when the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    update_presence.start()  # Start the task loop when the bot is ready
    print("Starting monitor playback...")  # Add debug line
    bot.loop.create_task(monitor_playback())

# Start the bot
bot.run('<<DISCORD BOT API KEY>>')
