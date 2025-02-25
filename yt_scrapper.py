
import os
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime
import time
import re

# Replace with your own API key
API_KEY = ''
# Get API Key - https://developers.google.com/youtube/v3/getting-started

# Replace with the channel ID
CHANNEL_ID = ''


# Find channel ID here - https://ytubetool.com/tools/youtube-channel-id

def get_youtube_service(api_key):
    return build('youtube', 'v3', developerKey=api_key)


def format_date(date_str):
    """ Convert ISO 8601 date string to separate date and time strings. """
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        formatted_date = date_obj.strftime('%B %d, %Y')
        formatted_time = date_obj.strftime('%I:%M %p')
        return formatted_date, formatted_time
    except ValueError:
        return 'No Date', 'No Time'


def get_channel_name(service, channel_id):
    """ Get the channel name using the channel ID. """
    request = service.channels().list(
        part='snippet',
        id=channel_id
    )
    response = request.execute()
    return response['items'][0]['snippet']['title']


def get_upload_playlist_id(service, channel_id):
    """ Get the playlist ID for the channel's uploads. """
    request = service.channels().list(
        part='contentDetails',
        id=channel_id
    )
    response = request.execute()
    playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    return playlist_id


def get_video_details(service, video_ids):
    """ Fetch detailed information about videos, including duration. """
    details_request = service.videos().list(
        part='snippet,statistics,contentDetails',
        id=','.join(video_ids)
    )
    return details_request.execute()


def classify_video(video):
    """ Classify video as 'short' or 'regular' based on duration. """
    duration = video['contentDetails']['duration']
    duration_seconds = 0

    if duration.startswith('PT'):
        duration = duration[2:]

    hours = re.findall(r'(\d+)H', duration)
    minutes = re.findall(r'(\d+)M', duration)
    seconds = re.findall(r'(\d+)S', duration)

    if hours:
        duration_seconds += int(hours[0]) * 3600
    if minutes:
        duration_seconds += int(minutes[0]) * 60
    if seconds:
        duration_seconds += int(seconds[0])

    return 'short' if duration_seconds <= 60 else 'regular'


def get_all_videos_from_playlist(service, playlist_id):
    videos = {'short': [], 'regular': []}
    next_page_token = None

    while True:
        request = service.playlistItems().list(
            part='snippet,contentDetails',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        video_ids = [item['contentDetails']['videoId'] for item in response.get('items', [])]

        if video_ids:
            details_response = get_video_details(service, video_ids)

            for item in details_response.get('items', []):
                video_id = item['id']
                video_type = classify_video(item)
                if video_type == 'short':
                    video_url = f'https://www.youtube.com/shorts/{video_id}'
                else:
                    video_url = f'https://www.youtube.com/watch?v={video_id}'

                title = item['snippet'].get('title', 'No Title')
                thumbnail = item['snippet']['thumbnails']['default']['url']
                upload_date_str = item['snippet'].get('publishedAt', 'No Date')
                upload_date, upload_time = format_date(upload_date_str)

                views = int(item['statistics'].get('viewCount', 0))
                comments = int(item['statistics'].get('commentCount', 0))

                videos[video_type].append({
                    'url': video_url,
                    'title': title,
                    'thumbnail': thumbnail,
                    'upload_date': upload_date,
                    'upload_time': upload_time,
                    'views': views,
                    'comments': comments
                })

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break
        time.sleep(1)

    return videos


def save_to_file(video_details, directory, filename):
    """ Save video details to a text file. """
    if not os.path.exists(directory):
        os.makedirs(directory)

    filepath = os.path.join(directory, filename)

    with open(filepath, 'w', encoding='utf-8') as file:
        for video in video_details:
            file.write(f"Title: {video['title']}\n")
            file.write(f"URL: {video['url']}\n")
            file.write(f"Thumbnail: {video['thumbnail']}\n")
            file.write(f"Upload Date: {video['upload_date']}\n")
            file.write(f"Upload Time: {video['upload_time']}\n")
            file.write(f"Views: {video['views']}\n")
            file.write(f"Comments: {video['comments']}\n")
            file.write('-' * 40 + '\n')


def save_to_excel(video_details, directory):
    """ Save video details to an Excel file. """
    if not os.path.exists(directory):
        os.makedirs(directory)

    for video_type, details in video_details.items():
        df = pd.DataFrame(details)
        df.to_excel(os.path.join(directory, f'{video_type}_videos.xlsx'), index=False)


if __name__ == '__main__':
    youtube_service = get_youtube_service(API_KEY)
    channel_name = get_channel_name(youtube_service, CHANNEL_ID)

    # Prompt user for folder name
    user_directory = input(f"Enter the directory name to save files for the channel '{channel_name}': ")
    playlist_id = get_upload_playlist_id(youtube_service, CHANNEL_ID)
    all_videos = get_all_videos_from_playlist(youtube_service, playlist_id)
    directory = user_directory.strip()

    # Save to text and Excel files
    save_to_file(all_videos['regular'], directory, 'regular_videos.txt')
    save_to_file(all_videos['short'], directory, 'shorts.txt')
    save_to_excel(all_videos, directory)

    print(f"⚔️ | Data for {channel_name} was saved successfully!")
    print(f"🎞️ | Found {len(all_videos['regular'])} Regular videos and {len(all_videos['short'])} Shorts!")