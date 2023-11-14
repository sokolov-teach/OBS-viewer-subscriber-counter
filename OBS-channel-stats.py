# OBS Python Script for Displaying Twitch and YouTube Viewers and Subscribers
# Author: Sokolov Sviatoslav
# Description: This script integrates with OBS to display live viewers and subscriber counts from Twitch and YouTube.

import obspython as obs
import requests
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
    return "Twitch and Youtube Viewers and Subscribers counter"

# YOUTUBE PART
def fetch_youtube_live_stream_id(channel_id):
    global YOUTUBE_STREAM_ID
    url = f'https://www.googleapis.com/youtube/v3/search?part=id&eventType=live&type=video&channelId={channel_id}&key={YOUTUBE_API_KEY}'
    response = requests.get(url)
    data = response.json()
    log(f'fetch_youtube_live_stream_id: {data}')
    items = data.get('items', [])
    if items:
        YOUTUBE_STREAM_ID = items[0]['id']['videoId']
        log(f'Ongoing YouTube live stream found: {YOUTUBE_STREAM_ID}')
    else:
        log('No ongoing live stream found on YouTube channel.')

def get_youtube_viewers():
    if YOUTUBE_STREAM_ID:
        url = f'https://www.googleapis.com/youtube/v3/videos?part=liveStreamingDetails&id={YOUTUBE_STREAM_ID}&key={YOUTUBE_API_KEY}'
        response = requests.get(url)
        data = response.json()
        log(f'get_youtube_viewers: {data}')
        items = data.get('items', [])
        if items:
            return int(items[0]['liveStreamingDetails']['concurrentViewers'])
        return 0
    log('No valid YouTube live stream ID available')
    return 0

def get_youtube_subscribers_count():
    url = f'https://www.googleapis.com/youtube/v3/channels?part=statistics&id={YOUTUBE_CHANNEL_ID}&key={YOUTUBE_API_KEY}'
    response = requests.get(url)
    data = response.json()
    log(f'get_youtube_subscribers_count: {data}')
    items = data.get('items', [])
    if items:
        return int(items[0]['statistics']['subscriberCount'])
    return 0

# TWITCH PART
def get_twitch_oauth_token(client_id, client_secret):
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, params=params)
    data = response.json()
    log(f'get_twitch_oauth_token: {data}')

    if data:
        return data.get('access_token', None)

    log('failed to obtain Twitch OAuth Token')
    return None

def get_broadcaster_id(client_id, oauth_token, channel_name):
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {oauth_token}'
    }
    url = f'https://api.twitch.tv/helix/users?login={channel_name}'
    response = requests.get(url, headers=headers)
    data = response.json()
    log(f'get_broadcaster_id (twitch): {data}')

    users = data.get('data', [])
    if users:
        return users[0].get('id')
    log('failed to obtain broadcaster id')
    return None

def get_twitch_viewers_count(client_id, oauth_token, user_login):
    url = 'https://api.twitch.tv/helix/streams'
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {oauth_token}'
    }
    params = {
        'user_login': user_login
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    log(f'get_twitch_viewers_count: {data}')

    streams = data.get('data', [])
    if streams:
        return streams[0].get('viewer_count', 0)

    log('no ongoing twitch live stream')
    return 0  # Return 0 if the channel is offline or not found

def get_twitch_viewers():
    if twitch_oauth_token:
        return int(get_twitch_viewers_count(TWITCH_CLIENT_ID, twitch_oauth_token, TWITCH_CHANNEL_ID))
    return 0  # Return 0 if failed to obtain OAuth Token

def get_twitch_followers_count(client_id, oauth_token, broadcaster_id):
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {oauth_token}'
    }
    url = f'https://api.twitch.tv/helix/channels/followers?broadcaster_id={broadcaster_id}'
    response = requests.get(url, headers=headers)
    data = response.json()
    log(f'get_twitch_followers_count: {data}')

    return data.get('total', 0)

def get_twitch_followers():
    global twitch_oauth_token
    global broadcaster_id
    if twitch_oauth_token:
        if broadcaster_id:
            return int(get_twitch_followers_count(TWITCH_CLIENT_ID, twitch_oauth_token, broadcaster_id))
    return 0  # Return 0 if failed to obtain OAuth Token or Broadcaster ID

def script_properties():
    props = obs.obs_properties_create()

    # Add text source dropdown for viewers
    p_viewers = obs.obs_properties_add_list(props, "source_viewers", "Text Source for Viewers", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(p_viewers, "[No text source]", "[No text source]")
    
    # Add text source dropdown for subscribers
    p_subs = obs.obs_properties_add_list(props, "source_subs", "Text Source for Subscribers", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(p_subs, "[No text source]", "[No text source]")

    # Populate the lists with Text Sources
    sources = obs.obs_enum_sources()
    if sources:
        for source in sources:
            source_id = obs.obs_source_get_unversioned_id(source)
            if source_id in ("text_gdiplus", "text_ft2_source"):
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(p_viewers, name, name)
                obs.obs_property_list_add_string(p_subs, name, name)
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

def update():
    youtube_viewers = get_youtube_viewers()
    twitch_viewers = get_twitch_viewers()
    twitch_followers = get_twitch_followers()
    youtube_subscribers = get_youtube_subscribers_count()
    log(f'Youtube Viewers: {youtube_viewers}')
    log(f'Twitch Viewers: {twitch_viewers}')
    log(f'YouTube Subscribers: {youtube_subscribers}')
    log(f'Twitch Followers: {twitch_followers}')
    log(f'Active threads: {threading.active_count()}')

    total_viewers = twitch_viewers + youtube_viewers
    total_followers = youtube_subscribers + twitch_followers

    # Update viewers count
    source_viewers_obj = obs.obs_get_source_by_name(source_viewers)
    if source_viewers_obj:
        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "text", f"{total_viewers}")
        obs.obs_source_update(source_viewers_obj, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source_viewers_obj)

    # Update subscribers count
    source_subs_obj = obs.obs_get_source_by_name(source_subs)
    if source_subs_obj:
        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "text", f"{total_followers}")
        obs.obs_source_update(source_subs_obj, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source_subs_obj)

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

    if YOUTUBE_CHANNEL_ID:
        fetch_youtube_live_stream_id(YOUTUBE_CHANNEL_ID)

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

def script_update(settings):
    global YOUTUBE_API_KEY
    global TWITCH_CLIENT_ID
    global TWITCH_CLIENT_SECRET
    global YOUTUBE_CHANNEL_ID
    global TWITCH_CHANNEL_ID
    global source_viewers
    global source_subs
    
    # Read user-defined settings
    YOUTUBE_API_KEY = obs.obs_data_get_string(settings, "YOUTUBE_API_KEY")
    TWITCH_CLIENT_ID = obs.obs_data_get_string(settings, "TWITCH_CLIENT_ID")
    TWITCH_CLIENT_SECRET = obs.obs_data_get_string(settings, "TWITCH_CLIENT_SECRET")
    YOUTUBE_CHANNEL_ID = obs.obs_data_get_string(settings, "YOUTUBE_CHANNEL_ID")
    TWITCH_CHANNEL_ID = obs.obs_data_get_string(settings, "TWITCH_CHANNEL_ID")

    source_viewers = obs.obs_data_get_string(settings, "source_viewers")
    source_subs = obs.obs_data_get_string(settings, "source_subs")