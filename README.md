# OBS viewer/subscriber counter from Youtube/Twitch

![Interface of OBS-channel-stats](interface.png?raw=true)

## Overview
This OBS script displays live viewer counts on YouTube and Twitch, as well as the total number of YouTube subscribers and Twitch followers. It was originally developed for a client but has been expanded and improved for broader use.

**Note**: The YouTube subscriber count may not be exact for channels with over 1,000 subscribers, as the count is rounded due to limitations in Google's API. (because Google takes your data, but doesn't want to provide it back)

## Features
- Live viewer count from YouTube and Twitch.
- Subscriber count from YouTube and follower count from Twitch.
- Separate or combined text sources for YouTube and Twitch statistics.

## Limitations
- Due to YouTube API rate limits, care should be taken with the frequency of API calls. Google provides 10,000 points daily. A search call costs 100 points, and regular updates for viewers and subscribers consume 2 points per minute.

## Installation
### Prerequisites
- [OBS 30](https://obsproject.com/) installed.
- [Python 3.10.6](https://www.python.org/downloads/release/python-3106/) installed and added to PATH.
- Active accounts on YouTube/Twitch.

### Setup Guide
#### YouTube
1. **Channel ID**: Your YouTube channel ID is required (not the channel name). Find it at [YouTube Account Advanced](https://www.youtube.com/account_advanced) or for any channel using [Comment Picker](https://commentpicker.com/youtube-channel-id.php).
2. **API Key**: Follow this tutorial by WebbyFan: [YouTube API Key Tutorial](https://www.youtube.com/watch?v=N18czV5tj5o).

#### Twitch
1. **Channel Name**: This is your Twitch channel name as it appears in your Twitch channel URL.
2. **API Key and Secret**: Follow this tutorial by CaptZorro: [Twitch API Key Tutorial](https://www.youtube.com/watch?v=dJwrFcBKvJw).

### Script Configuration
1. Create text sources in OBS for YouTube and Twitch viewers and subscribers.
2. In OBS, go to `Tools` > `Scripts` and add the script.
3. Configure the script settings with your API keys, channel IDs, and text sources.
4. Start your stream on Youtube and Twitch.
5. Click the `START` button to begin fetching data.

## Usage
- The script updates viewer and subscriber counts every 60 seconds.
- Press the `START` button after you started streaming to initialize data fetching.
- Logs are stored in the same directory as the script for troubleshooting.

## Platform Compatibility
- **Windows**: Works on my machine.
- **macOS**: I helped a client run this script successfully on an Apple M1 laptop, but this was tedious because it is hard to make OBS find the right version of Python on Mac. I don't have a Mac machine, so I can't really help with this. Also, I've added logs since this time, so I don't know how Apple handles the creation of text files in their system by OBS scripts.

## Contributing
Your suggestions and contributions are welcome! Please feel free to leave feature requests or issues on GitHub, and I'll try to implement them.

## Limitations and Points to Note
- Pressing the `START` button consumes 100 API points each time due to a search call to the YouTube API. It's advisable to use this button sparingly (ideally only once at the start of each stream).
- Running the script continuously for 24 hours will consume approximately 2,880 points, well within the daily limit provided by Google, assuming the `START` button is not overused.

## Acknowledgements
- Thanks to [WebbyFan](https://www.youtube.com/watch?v=N18czV5tj5o) and [CaptZorro](https://www.youtube.com/watch?v=dJwrFcBKvJw) for their tutorials on API key setup.
- A big thanks to [hmeneses](https://obsproject.com/forum/members/hmeneses.227186/) and his [Youtube chat and channel updater](https://obsproject.com/forum/resources/youtube-chat-and-channel-updater.894/) for the idea of using `urllib.request` instead of `requests`

## Contact
For support or inquiries, please open an issue on GitHub or contact me at sokolov.teach@gmail.com
