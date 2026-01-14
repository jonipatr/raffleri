import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

from app.models.raffle import RaffleRequest, RaffleResponse
from app.api.youtube_api import YouTubeAPI
from app.api.tiktok_api import TikTokAPI
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
tiktok_api = TikTokAPI()

def get_youtube_api():
    """Get YouTube API client, raising error if API key is missing."""
    global youtube_api
    if youtube_api is None:
        if not youtube_api_key:
            raise HTTPException(
                status_code=500,
                detail="YOUTUBE_API_KEY environment variable is required. Please set it in your .env file or environment variables."
            )
        youtube_api = YouTubeAPI(youtube_api_key)
    return youtube_api


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main HTML page."""
    html_content = render_template("index.html", {"request": request})
    return HTMLResponse(content=html_content)


@app.post("/api/youtube/entries", response_model=RaffleResponse)
async def youtube_raffle(request: RaffleRequest):
    """
    Run a raffle for YouTube video comments.
    
    Args:
        request: RaffleRequest with video_url
        
    Returns:
        RaffleResponse with winner and statistics
    """
    try:
        # Fetch user entries from YouTube
        api = get_youtube_api()
        entries = api.get_user_entries(request.video_url)
        
        if not entries:
            raise HTTPException(
                status_code=404,
                detail="No comments found for this video"
            )
        
        # Pick winner
        winner = pick_winner(entries)
        
        # Calculate statistics
        total_entries = sum(entry.entries for entry in entries)
        total_participants = len(entries)
        
        return RaffleResponse(
            winner=winner,
            total_entries=total_entries,
            total_participants=total_participants,
            platform="youtube"
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing raffle: {str(e)}")


@app.post("/api/tiktok/entries")
async def tiktok_raffle(request: RaffleRequest):
    """
    Run a raffle for TikTok video comments (not implemented).
    
    Args:
        request: RaffleRequest with video_url
        
    Returns:
        501 Not Implemented
    """
    raise HTTPException(
        status_code=501,
        detail="TikTok support coming soon"
    )
