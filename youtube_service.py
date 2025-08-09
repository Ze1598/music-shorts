import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import os
import mimetypes
from datetime import datetime, timezone
import json

class VideoMetadata:
    def __init__(self):
        self.title = ""
        self.description = ""
        self.tags = []
        self.category_id = "10"  # Music category
        self.privacy_status = "private"  # private, unlisted, public
        self.publish_at = None  # ISO 8601 datetime for scheduling
        self.thumbnail = None
        self.shorts_format = False  # True for YouTube Shorts

class YouTubeService:
    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build('youtube', 'v3', credentials=credentials)
        
    def get_channel_info(self):
        """Get authenticated user's channel information"""
        try:
            response = self.service.channels().list(
                part='snippet,statistics,brandingSettings',
                mine=True
            ).execute()
            
            if response.get('items'):
                channel = response['items'][0]
                return {
                    'id': channel['id'],
                    'title': channel['snippet']['title'],
                    'description': channel['snippet'].get('description', ''),
                    'subscriber_count': channel['statistics'].get('subscriberCount', '0'),
                    'video_count': channel['statistics'].get('videoCount', '0'),
                    'view_count': channel['statistics'].get('viewCount', '0'),
                    'thumbnail': channel['snippet']['thumbnails'].get('default', {}).get('url', '')
                }
            return None
            
        except HttpError as e:
            st.error(f"Error fetching channel info: {e}")
            return None
    
    def validate_video_file(self, video_path):
        """Validate video file meets YouTube requirements"""
        if not os.path.exists(video_path):
            return False, "Video file not found"
            
        # Check file size (128GB max)
        file_size = os.path.getsize(video_path)
        max_size = 128 * 1024 * 1024 * 1024  # 128GB in bytes
        if file_size > max_size:
            return False, f"File too large: {file_size / (1024**3):.1f}GB (max 128GB)"
        
        # Check file format
        mime_type, _ = mimetypes.guess_type(video_path)
        allowed_types = [
            'video/mp4', 'video/quicktime', 'video/avi', 
            'video/x-msvideo', 'video/x-flv', 'video/webm'
        ]
        
        if mime_type not in allowed_types:
            return False, f"Unsupported format: {mime_type}"
            
        return True, "Valid"
    
    def detect_shorts_format(self, video_path):
        """Detect if video meets YouTube Shorts criteria"""
        try:
            from moviepy.editor import VideoFileClip
            
            with VideoFileClip(video_path) as clip:
                duration = clip.duration
                width, height = clip.size
                
                # YouTube Shorts criteria
                is_vertical = height > width  # Vertical orientation
                is_short_duration = duration <= 60  # 60 seconds or less
                aspect_ratio = height / width if width > 0 else 0
                is_correct_ratio = 1.5 <= aspect_ratio <= 2.0  # Roughly 9:16
                
                return {
                    'is_shorts': is_vertical and is_short_duration and is_correct_ratio,
                    'duration': duration,
                    'width': width,
                    'height': height,
                    'aspect_ratio': aspect_ratio,
                    'reasons': {
                        'vertical': is_vertical,
                        'short_duration': is_short_duration,
                        'correct_ratio': is_correct_ratio
                    }
                }
                
        except Exception as e:
            st.error(f"Error analyzing video: {e}")
            return None
    
    def validate_scheduled_time(self, publish_at):
        """Validate scheduled publication time"""
        if not publish_at:
            return True, "No scheduling specified"
            
        try:
            from datetime import datetime, timezone
            import pytz
            
            # Parse the RFC 3339 datetime format from YouTube
            if publish_at.endswith('Z'):
                # Remove Z and parse as UTC
                scheduled_time = datetime.fromisoformat(publish_at.replace('Z', ''))
                scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
            else:
                # Handle other ISO formats
                scheduled_time = datetime.fromisoformat(publish_at.replace('Z', '+00:00'))
                if scheduled_time.tzinfo is None:
                    scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
            
            now_utc = datetime.now(timezone.utc)
            
            # Check if time is in the future
            if scheduled_time <= now_utc:
                return False, "Scheduled time must be in the future"
                
            # Check if time is not too far in the future (YouTube limit: ~1 year)
            from datetime import timedelta
            max_future = now_utc + timedelta(days=365)
            if scheduled_time > max_future:
                return False, "Scheduled time cannot be more than 1 year in the future"
                
            return True, f"Valid scheduling for {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            
        except Exception as e:
            return False, f"Invalid scheduling format: {e}"

    def upload_video(self, video_path, metadata):
        """Upload video file to YouTube"""
        # Validate video file
        is_valid, message = self.validate_video_file(video_path)
        if not is_valid:
            st.error(message)
            return None
            
        # Validate scheduling if specified
        if metadata.publish_at:
            st.info(f"🔍 Scheduling timestamp: {metadata.publish_at}")
            is_valid_schedule, schedule_message = self.validate_scheduled_time(metadata.publish_at)
            if not is_valid_schedule:
                st.error(f"Scheduling error: {schedule_message}")
                return None
            else:
                st.info(f"✅ {schedule_message}")
                
            # Additional YouTube-specific validation
            try:
                from datetime import datetime, timezone, timedelta
                scheduled_time = datetime.fromisoformat(metadata.publish_at.replace('Z', ''))
                scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
                now_utc = datetime.now(timezone.utc)
                
                # YouTube requires at least 60 minutes in the future (conservative)
                min_future = now_utc + timedelta(minutes=60)
                if scheduled_time < min_future:
                    st.error("⚠️ YouTube requires scheduling at least 60 minutes in the future")
                    return None
                    
            except Exception as e:
                st.error(f"Error validating timestamp: {e}")
                return None
            
        try:
            # Prepare video metadata
            body = {
                'snippet': {
                    'title': metadata.title or "Untitled Video",
                    'description': metadata.description or "",
                    'tags': metadata.tags if metadata.tags else [],
                    'categoryId': metadata.category_id
                },
                'status': {
                    'privacyStatus': metadata.privacy_status
                }
            }
            
            # Add scheduling if specified
            if metadata.publish_at:
                body['status']['publishAt'] = metadata.publish_at
            
            # Add shorts-specific metadata if detected
            if metadata.shorts_format:
                if '#Shorts' not in metadata.tags:
                    body['snippet']['tags'].append('#Shorts')
                    
                # Add shorts indicator to description if not present
                if '#Shorts' not in metadata.description:
                    body['snippet']['description'] += "\n\n#Shorts"
            
            # Create media upload object
            media = MediaFileUpload(
                video_path,
                chunksize=-1,  # Upload in single chunk for simplicity
                resumable=True
            )
            
            # Execute upload
            insert_request = self.service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            response = None
            error = None
            retry = 0
            
            while response is None and retry < 3:
                try:
                    status, response = insert_request.next_chunk()
                    if status:
                        progress = status.progress() * 100
                        progress_bar.progress(progress / 100)
                        status_text.text(f"Upload progress: {progress:.1f}%")
                        
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        # Retriable error
                        retry += 1
                        st.warning(f"Upload error (retry {retry}/3): {e}")
                    else:
                        raise e
                        
            progress_bar.progress(1.0)
            status_text.text("Upload completed!")
            
            if response:
                video_id = response['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                return {
                    'video_id': video_id,
                    'video_url': video_url,
                    'title': response['snippet']['title'],
                    'status': response['status']['privacyStatus'],
                    'publish_at': response['status'].get('publishAt'),
                    'upload_status': response['status']['uploadStatus']
                }
            else:
                st.error("Upload failed after retries")
                return None
                
        except HttpError as e:
            error_content = json.loads(e.content.decode()) if e.content else {}
            error_message = error_content.get('error', {}).get('message', str(e))
            st.error(f"YouTube API Error: {error_message}")
            return None
        except Exception as e:
            st.error(f"Unexpected error during upload: {str(e)}")
            return None
    
    def upload_thumbnail(self, video_id, thumbnail_path):
        """Upload custom thumbnail for video"""
        if not os.path.exists(thumbnail_path):
            st.error("Thumbnail file not found")
            return False
            
        try:
            media = MediaFileUpload(thumbnail_path)
            
            self.service.thumbnails().set(
                videoId=video_id,
                media_body=media
            ).execute()
            
            st.success("Custom thumbnail uploaded successfully")
            return True
            
        except HttpError as e:
            st.error(f"Error uploading thumbnail: {e}")
            return False
    
    def validate_upload_quota(self):
        """Check YouTube API quota (basic estimation)"""
        # This is a simplified quota check
        # In production, you'd want more sophisticated quota tracking
        try:
            # A simple API call to check if we can make requests
            self.service.channels().list(
                part='id',
                mine=True,
                maxResults=1
            ).execute()
            return True, "API quota available"
            
        except HttpError as e:
            if e.resp.status == 403:
                error_content = json.loads(e.content.decode()) if e.content else {}
                if 'quotaExceeded' in str(error_content):
                    return False, "YouTube API quota exceeded"
            return False, f"API Error: {e}"
        except Exception as e:
            return False, f"Quota check failed: {e}"
    
    def get_video_categories(self, region_code='US'):
        """Get available video categories"""
        try:
            response = self.service.videoCategories().list(
                part='snippet',
                regionCode=region_code
            ).execute()
            
            categories = {}
            for item in response.get('items', []):
                categories[item['id']] = item['snippet']['title']
                
            return categories
            
        except HttpError as e:
            st.warning(f"Could not fetch video categories: {e}")
            # Return default categories
            return {
                '10': 'Music',
                '22': 'People & Blogs',
                '23': 'Comedy',
                '24': 'Entertainment'
            }