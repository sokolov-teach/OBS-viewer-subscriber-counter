# OBS Python Script for Displaying Twitch and YouTube Viewers and Subscribers
# Author: Sokolov Sviatoslav
# Description: This script integrates with OBS to display live viewers and subscriber counts from Twitch and YouTube.

import obspython as obs
import urllib.request
import urllib.parse
import json
import time
import threading
import logging
import os
import datetime

# Variables for user-defined settings
YOUTUBE_API_KEY = ""
TWITCH_CLIENT_ID = ""
TWITCH_CLIENT_SECRET = ""
TWITCH_CHANNEL_ID = ""
YOUTUBE_CHANNEL_ID = ""
YOUTUBE_STREAM_ID = ""

# Global variables for the text sources
source_youtube_viewers = ""
source_twitch_viewers = ""
source_youtube_subs = ""
source_twitch_subs = ""

#Updates every 60 seconds. Do not change this! If you do, you can run out of Youtube API points very quickly!
update_frequency = 60

# To store Twitch OAuth token
twitch_oauth_token = None
broadcaster_id = None
stop_thread = False  # Global flag to control the thread
thread = None  # Global variable to hold the thread
update_thread = None  # Initialize the update thread

# Logging configuration
# Get the directory of the current script
script_directory = os.path.dirname(os.path.abspath(__file__))

# Define the log file path in the same directory as the script
log_file_path = os.path.join(script_directory, 'obs_channel_stats_log.txt')

# Configure the logging to use the defined file path
logging.basicConfig(filename=log_file_path, filemode='a', format='%(asctime)s - %(message)s', level=logging.INFO)

def log(*args, **kwargs):
    # Get the current time and format it
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Print the timestamp along with the original message
    print(f"[{current_time}]", *args, **kwargs)
    logging.info(*args, **kwargs)

def script_description():
    return "Twitch and Youtube Viewers and Subscribers counter. If you want to output the total number of subscribers/viewers from both platforms, assign them both to a one text source."

# YOUTUBE PART
def fetch_youtube_live_stream_id(channel_id):
    global YOUTUBE_STREAM_ID
    
    if not YOUTUBE_API_KEY:
        log('YouTube API key is missing. Skipping fetch_youtube_live_stream_id.')
        return 0

    url = f'https://www.googleapis.com/youtube/v3/search?part=id&eventType=live&type=video&channelId={channel_id}&key={YOUTUBE_API_KEY}'
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            log(f'fetch_youtube_live_stream_id: {data}')
            items = data.get('items', [])
            if items:
                YOUTUBE_STREAM_ID = items[0]['id']['videoId']
                log(f'Ongoing YouTube live stream found: {YOUTUBE_STREAM_ID}')
            else:
                log('No ongoing live stream found on YouTube channel.')
    except urllib.error.URLError as e:
        log(f'Error in fetch_youtube_live_stream_id: {e.reason}')

def get_youtube_viewers():
    if not YOUTUBE_API_KEY:
        log('YouTube API key is missing. Skipping fetch_youtube_live_stream_id.')
        return 0

    url = f'https://www.googleapis.com/youtube/v3/videos?part=liveStreamingDetails&id={YOUTUBE_STREAM_ID}&key={YOUTUBE_API_KEY}'

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            log(f'get_youtube_viewers: {data}')
            items = data.get('items', [])
            if items:
                return int(items[0]['liveStreamingDetails']['concurrentViewers'])
            return 0
    except urllib.error.URLError as e:
        log(f'Error in get_youtube_viewers: {e.reason}')
        return 0

    log('No valid YouTube live stream ID available')
    return 0

def get_youtube_subscribers_count():
    if not YOUTUBE_API_KEY:
        log('YouTube API key is missing. Skipping fetch_youtube_live_stream_id.')
        return 0

    url = f'https://www.googleapis.com/youtube/v3/channels?part=statistics&id={YOUTUBE_CHANNEL_ID}&key={YOUTUBE_API_KEY}'

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            log(f'get_youtube_subscribers_count: {data}')
            items = data.get('items', [])
            if items:
                return int(items[0]['statistics']['subscriberCount'])
            return 0
    except urllib.error.URLError as e:
        log(f'Error in get_youtube_subscribers_count: {e.reason}')
        return 0

# TWITCH PART
def get_twitch_oauth_token(client_id, client_secret):
    if not client_id or not client_secret:
        log('Twitch Client ID or Client Secret is missing. Skipping get_twitch_oauth_token.')
        return None

    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            log(f'get_twitch_oauth_token: {data}')
            return data.get('access_token', None)
    except urllib.error.URLError as e:
        log(f'Error in get_twitch_oauth_token: {e.reason}')
        return None

def get_broadcaster_id(client_id, oauth_token, channel_name):
    if not client_id or not oauth_token:
        log('Twitch Client ID or OAuth token is missing. Skipping get_broadcaster_id.')
        return None

    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {oauth_token}'
    }
    req = urllib.request.Request(
        f'https://api.twitch.tv/helix/users?login={channel_name}', 
        headers=headers
    )
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            log(f'get_broadcaster_id (twitch): {data}')
            users = data.get('data', [])
            if users:
                return users[0].get('id')
            return None
    except urllib.error.URLError as e:
        log(f'Error in get_broadcaster_id: {e.reason}')
        return None

def get_twitch_viewers_count(client_id, oauth_token, user_login):
    if not client_id or not oauth_token:
        log('Twitch Client ID or OAuth token is missing. Skipping get_broadcaster_id.')
        return None

    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {oauth_token}'
    }
    params = urllib.parse.urlencode({'user_login': user_login})
    req = urllib.request.Request(
        f'https://api.twitch.tv/helix/streams?{params}', 
        headers=headers
    )
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            log(f'get_twitch_viewers_count: {data}')
            streams = data.get('data', [])
            if streams:
                return streams[0].get('viewer_count', 0)
            return 0
    except urllib.error.URLError as e:
        log(f'Error in get_twitch_viewers_count: {e.reason}')
        return 0

def get_twitch_viewers():
    if twitch_oauth_token:
        return int(get_twitch_viewers_count(TWITCH_CLIENT_ID, twitch_oauth_token, TWITCH_CHANNEL_ID))
    return 0  # Return 0 if failed to obtain OAuth Token

def get_twitch_followers_count(client_id, oauth_token, broadcaster_id):
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {oauth_token}'
    }
    req = urllib.request.Request(
        f'https://api.twitch.tv/helix/channels/followers?broadcaster_id={broadcaster_id}', 
        headers=headers
    )
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            log(f'get_twitch_followers_count: {data}')
            return data.get('total', 0)
    except urllib.error.URLError as e:
        log(f'Error in get_twitch_followers_count: {e.reason}')
        return 0

def get_twitch_followers():
    global twitch_oauth_token
    global broadcaster_id
    if twitch_oauth_token:
        if broadcaster_id:
            return int(get_twitch_followers_count(TWITCH_CLIENT_ID, twitch_oauth_token, broadcaster_id))
    return 0  # Return 0 if failed to obtain OAuth Token or Broadcaster ID

def script_properties():
    props = obs.obs_properties_create()

    # Text Source dropdowns for YouTube and Twitch viewers
    p_youtube_viewers = obs.obs_properties_add_list(props, "source_youtube_viewers", "Text Source for YouTube Viewers", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(p_youtube_viewers, "[No text source]", "[No text source]")

    p_twitch_viewers = obs.obs_properties_add_list(props, "source_twitch_viewers", "Text Source for Twitch Viewers", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(p_twitch_viewers, "[No text source]", "[No text source]")
    
    # Text Source dropdowns for YouTube subscribers and Twitch followers
    p_youtube_subs = obs.obs_properties_add_list(props, "source_youtube_subs", "Text Source for YouTube Subscribers", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(p_youtube_subs, "[No text source]", "[No text source]")

    p_twitch_subs = obs.obs_properties_add_list(props, "source_twitch_subs", "Text Source for Twitch Followers", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(p_twitch_subs, "[No text source]", "[No text source]")

    # Populate the lists with Text Sources
    sources = obs.obs_enum_sources()
    if sources:
        for source in sources:
            source_id = obs.obs_source_get_unversioned_id(source)
            if source_id in ("text_gdiplus", "text_ft2_source"):
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(p_youtube_viewers, name, name)
                obs.obs_property_list_add_string(p_twitch_viewers, name, name)
                obs.obs_property_list_add_string(p_youtube_subs, name, name)
                obs.obs_property_list_add_string(p_twitch_subs, name, name)
        obs.source_list_release(sources)
    
    # Other API information
    obs.obs_properties_add_text(props, "YOUTUBE_API_KEY", "YouTube API Key", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "TWITCH_CLIENT_ID", "Twitch Client ID", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "TWITCH_CLIENT_SECRET", "Twitch Client Secret", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "YOUTUBE_CHANNEL_ID", "YouTube Channel ID", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "TWITCH_CHANNEL_ID", "Twitch Channel ID", obs.OBS_TEXT_DEFAULT)

    obs.obs_properties_add_button(props, "start_button", "START", start_button_pressed)
    obs.obs_properties_add_button(props, "stop_button", "STOP", stop_button_pressed)
    
    return props

# Additional function that updates text source. Used in update()
def update_text_source(source_name, text):
    source_obj = obs.obs_get_source_by_name(source_name)
    if source_obj:
        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "text", text)
        obs.obs_source_update(source_obj, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source_obj)

def update():
    youtube_viewers = get_youtube_viewers() if YOUTUBE_API_KEY else 0
    twitch_viewers = get_twitch_viewers() if TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET else 0
    youtube_subscribers = get_youtube_subscribers_count() if YOUTUBE_API_KEY else 0
    twitch_followers = get_twitch_followers() if TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET else 0

    log(f'Youtube Viewers: {youtube_viewers}')
    log(f'Twitch Viewers: {twitch_viewers}')
    log(f'YouTube Subscribers: {youtube_subscribers}')
    log(f'Twitch Followers: {twitch_followers}')
    log(f'Active threads: {threading.active_count()}')

    # Check if YouTube and Twitch viewers sources are the same or not
    # Update them based on what was fetched
    if source_youtube_viewers == source_twitch_viewers and source_youtube_viewers != "":
        total_viewers = youtube_viewers + twitch_viewers
        update_text_source(source_youtube_viewers, str(total_viewers))
    else:
        if source_youtube_viewers != "":
            update_text_source(source_youtube_viewers, str(youtube_viewers))
        if source_twitch_viewers != "":
            update_text_source(source_twitch_viewers, str(twitch_viewers))

    # Check if YouTube subsribers and Twitch followers are the same or not
    # Update them based on what was fetched
    if source_youtube_subs == source_twitch_subs and source_youtube_subs != "":
        total_subs = youtube_subscribers + twitch_followers
        update_text_source(source_youtube_subs, str(total_subs))
    else:
        if source_youtube_subs != "":
            update_text_source(source_youtube_subs, str(youtube_subscribers))
        if source_twitch_subs != "":
            update_text_source(source_twitch_subs, str(twitch_followers))

def threaded_update():
    global stop_thread
    global update_frequency
    global twitch_oauth_token
    while True:
        if stop_thread:
            break
        
        start_time = time.time()
        try:
            update()
        except Exception as e:
            log(f'Active threads: {e}')
        
        # Calculate the remaining time to sleep
        elapsed_time = time.time() - start_time
        sleep_time = max(0, update_frequency - elapsed_time)
        
        # Sleep in small intervals to allow responding quickly to the stop_thread flag
        while sleep_time > 0 and not stop_thread:
            time.sleep(min(1, sleep_time))
            sleep_time = max(0, update_frequency - (time.time() - start_time))

def start_button_pressed(props, prop):
    global update_thread
    global stop_thread
    global twitch_oauth_token
    global broadcaster_id
    log("Start button pressed")

    if YOUTUBE_CHANNEL_ID and YOUTUBE_API_KEY:
        fetch_youtube_live_stream_id(YOUTUBE_CHANNEL_ID)

    if TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET:
            twitch_oauth_token = get_twitch_oauth_token(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
            broadcaster_id = get_broadcaster_id(TWITCH_CLIENT_ID, twitch_oauth_token, TWITCH_CHANNEL_ID)
    
    # If there is an existing thread, stop it
    if update_thread is not None and update_thread.is_alive():
        stop_thread = True
        update_thread.join()  # Wait for the existing thread to exit
        log("Existing thread stopped")
    
    # Reset the stop_thread flag and start a new thread
    stop_thread = False
    update_thread = threading.Thread(target=threaded_update)
    update_thread.daemon = True  # set the thread as a daemon so it will close when OBS closes
    update_thread.start()
    log("New update thread started")

def stop_button_pressed(props, prop):
    global stop_thread
    log("Stop button pressed")
    stop_thread = True


# OBS internal: called when the script’s settings (if any) have been changed by the user.
def script_update(settings):
    global YOUTUBE_API_KEY
    global TWITCH_CLIENT_ID
    global TWITCH_CLIENT_SECRET
    global YOUTUBE_CHANNEL_ID
    global TWITCH_CHANNEL_ID
    global source_youtube_viewers
    global source_twitch_viewers
    global source_youtube_subs
    global source_twitch_subs
    
    # Read user-defined settings
    YOUTUBE_API_KEY = obs.obs_data_get_string(settings, "YOUTUBE_API_KEY")
    TWITCH_CLIENT_ID = obs.obs_data_get_string(settings, "TWITCH_CLIENT_ID")
    TWITCH_CLIENT_SECRET = obs.obs_data_get_string(settings, "TWITCH_CLIENT_SECRET")
    YOUTUBE_CHANNEL_ID = obs.obs_data_get_string(settings, "YOUTUBE_CHANNEL_ID")
    TWITCH_CHANNEL_ID = obs.obs_data_get_string(settings, "TWITCH_CHANNEL_ID")

    source_youtube_viewers = obs.obs_data_get_string(settings, "source_youtube_viewers")
    source_twitch_viewers = obs.obs_data_get_string(settings, "source_twitch_viewers")
    source_youtube_subs = obs.obs_data_get_string(settings, "source_youtube_subs")
    source_twitch_subs = obs.obs_data_get_string(settings, "source_twitch_subs")
