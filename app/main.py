import os
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

from app.models.raffle import RaffleRequest, RaffleResponse, ChannelRequest, ChannelResponse, ChannelStreamsResponse, ChannelStats
from app.api.youtube_api import YouTubeAPI
from app.services.raffle import pick_winner

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="RAFFLERi", description="Weighted Comment Raffle System")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
jinja_env = Environment(loader=FileSystemLoader("templates"))

def render_template(template_name: str, context: dict) -> str:
    """Render a Jinja2 template."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)

# Initialize API clients (will be created lazily or raise error on first use)
youtube_api_key = os.getenv("YOUTUBE_API_KEY")
youtube_api = None

def get_youtube_api():
    """Get YouTube API client, raising error if API key is missing."""
    global youtube_api
    if youtube_api is None:
        if not youtube_api_key:
            raise HTTPException(
                status_code=500,
                detail="YOUTUBE_API_KEY environment variable is required. Please set it in your .env file or environment variables."
            )
        podcast_playlist_id = os.getenv("PODCAST_PLAYLIST_ID") or "PLTigWTFUFrepryTKKY2Kua5iEYXcCnnEK"
        youtube_api = YouTubeAPI(youtube_api_key, podcast_playlist_id=podcast_playlist_id)
    return youtube_api


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main HTML page."""
    html_content = render_template("index.html", {"request": request})
    return HTMLResponse(content=html_content)


# @app.get("/testing", response_class=HTMLResponse)
# async def read_testing(request: Request):
#     """Serve the testing HTML page with URL type selection."""
#     html_content = render_template("testing.html", {"request": request})
#     return HTMLResponse(content=html_content)


@app.post("/api/youtube/entries", response_model=RaffleResponse)
async def youtube_raffle(request: RaffleRequest):
    """
    Run a raffle for YouTube live chat messages.
    
    Args:
        request: RaffleRequest with video_url
        
    Returns:
        RaffleResponse with winner (including comment text) and statistics
    """
    import asyncio
    try:
        # Run the blocking API call in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        api = get_youtube_api()
        entries, user_comments_map, total_comments = await loop.run_in_executor(
            None, 
            api.get_user_entries, 
            request.video_url
        )
        
        if not entries:
            raise HTTPException(
                status_code=404,
                detail="No live chat messages found for this stream"
            )
        
        # Pick winner (with comment text)
        winner = pick_winner(entries, user_comments_map)
        
        # Calculate statistics
        total_participants = len(entries)
        
        return RaffleResponse(
            winner=winner,
            total_comments=total_comments,
            total_participants=total_participants,
            platform="youtube"
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"YouTube API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing raffle: {str(e)}")


@app.post("/api/youtube/channel", response_model=ChannelResponse)
async def youtube_channel(request: ChannelRequest):
    """
    Check if a YouTube channel has an active live stream.
    
    Args:
        request: ChannelRequest with channel_url or channel_id
        
    Returns:
        ChannelResponse with live stream information if found
    """
    try:
        api = get_youtube_api()
        result = api.get_active_live_stream(
            channel_url=request.channel_url,
            channel_id=request.channel_id
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="No active live stream found for this channel"
            )
        
        return ChannelResponse(
            is_live=True,
            video_id=result['video_id'],
            video_url=result['video_url'],
            live_chat_id=result['live_chat_id']
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"YouTube API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking channel: {str(e)}")


@app.post("/api/youtube/channel/streams", response_model=ChannelStreamsResponse)
async def youtube_channel_streams(request: ChannelRequest):
    """
    Get all active live streams for a YouTube channel.
    
    Args:
        request: ChannelRequest with channel_url or channel_id
        
    Returns:
        ChannelStreamsResponse with list of active streams
    """
    from app.models.raffle import StreamInfo
    
    try:
        api = get_youtube_api()
        streams = api.get_active_live_streams(
            channel_url=request.channel_url,
            channel_id=request.channel_id
        )
        channel_stats_data = api.get_channel_stats(
            channel_url=request.channel_url,
            channel_id=request.channel_id
        )
        
        # Convert to StreamInfo objects
        stream_infos = [
            StreamInfo(
                video_id=stream['video_id'],
                video_url=stream['video_url'],
                live_chat_id=stream['live_chat_id'],
                title=stream['title']
            )
            for stream in streams
        ]
        
        channel_stats = None
        if channel_stats_data:
            channel_stats = ChannelStats(**channel_stats_data)

        return ChannelStreamsResponse(streams=stream_infos, channel=channel_stats)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"YouTube API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching channel streams: {str(e)}")
