import os
import requests
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

load_dotenv()
print("TEMP: Environment variables loaded")
print("TEMP: Database URL:", os.getenv("DATABASE_URL"))

from app.models.raffle import (
    RaffleRequest,
    RaffleResponse,
    ChannelRequest,
    ChannelResponse,
    ChannelStreamsResponse,
    ChannelStats,
    CollectorSetSessionRequest,
    CollectorStatusResponse
    ,LiveChatIdRequest
    ,LiveChatIdResponse
)
from app.api.youtube_api import YouTubeAPI
from app.db import (
    init_db,
    get_db_session,
    get_current_stream_session,
    clear_stream_data,
    get_or_create_stream_session,
    StreamMessage
)
from app.services.raffle import pick_winner
from app.services.live_chat_collector import LiveChatCollector
from app.utils.youtube import extract_video_id

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

# Initialize FastAPI app
app = FastAPI(title="RAFFLERi", description="Comment Raffle System", lifespan=lifespan)

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
collector = None

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


def get_collector() -> LiveChatCollector:
    global collector
    if collector is None:
        collector = LiveChatCollector(get_youtube_api())
    return collector


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main HTML page."""
    html_content = render_template("index.html", {"request": request})
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/testing", response_class=HTMLResponse)
async def read_testing(request: Request):
    """Serve the testing HTML page with URL type selection."""
    html_content = render_template("testing.html", {"request": request})
    return HTMLResponse(content=html_content)


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

        # Stop background collection when raffle starts
        try:
            get_collector().stop()
        except Exception:
            pass

        def raffle_from_db_or_fallback():
            db = get_db_session()
            try:
                current_session = get_current_stream_session(db)
                if current_session:
                    rows = (
                        db.query(StreamMessage)
                        .filter(StreamMessage.session_id == current_session.id)
                        .all()
                    )
                    if rows:
                        user_data = {}
                        for row in rows:
                            username = row.username
                            comment_text = row.comment_text
                            key = f"user_{username}"
                            if key not in user_data:
                                user_data[key] = {"username": username, "count": 0, "comments": []}
                            if user_data[key]["count"] < 5:
                                user_data[key]["count"] += 1
                                user_data[key]["comments"].append(comment_text)

                        entries = []
                        user_comments_map = {}
                        # Build entries (import model locally to avoid import cycles)
                        from app.models.raffle import RaffleEntry as EntryModel
                        for _, info in user_data.items():
                            if info["count"] > 0:
                                entries.append(EntryModel(
                                    platform="youtube",
                                    user_id=None,
                                    username=info["username"],
                                    entries=info["count"],
                                    comment_text=None
                                ))
                                user_comments_map[info["username"]] = info["comments"]

                        total_comments = len(rows)
                        return entries, user_comments_map, total_comments
                return api.get_user_entries(request.video_url)
            finally:
                db.close()

        entries, user_comments_map, total_comments = await loop.run_in_executor(None, raffle_from_db_or_fallback)
        
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
    
    db = None
    try:
        api = get_youtube_api()
        db = get_db_session()
        current_session = get_current_stream_session(db)
        streams = []
        
        if current_session and current_session.live_chat_id and current_session.video_url and current_session.video_id:
            expected_channel_id = None
            if request.channel_url:
                expected_channel_id = api.resolve_channel_id_from_url(request.channel_url)

            still_active = False
            try:
                meta = api.get_video_live_metadata(current_session.video_id)
                is_live = meta.get("live_broadcast_content") == "live"
                active_live_chat_id = meta.get("active_live_chat_id")
                video_channel_id = meta.get("channel_id")

                if expected_channel_id and video_channel_id and video_channel_id != expected_channel_id:
                    print("TEMP: Cached stream is live but belongs to another channel; clearing DB")
                    still_active = False
                else:
                    still_active = bool(is_live and active_live_chat_id and active_live_chat_id == current_session.live_chat_id)
            except Exception:
                still_active = False

            if still_active:
                print("TEMP: Reusing cached live chat", current_session.live_chat_id)
                streams = [{
                    'video_id': current_session.video_id or "",
                    'video_url': current_session.video_url,
                    'live_chat_id': current_session.live_chat_id,
                    'title': "Live Stream"
                }]
            else:
                print("TEMP: Cached live chat invalid/offline, clearing stored data")
                clear_stream_data(db)
        
        if not streams:
            print("TEMP: No cached live chat, running YouTube channel search for", request.channel_url or request.channel_id)
            streams = api.get_active_live_streams(
                channel_url=request.channel_url,
                channel_id=request.channel_id
            )
            if streams:
                first_stream = streams[0]
                get_or_create_stream_session(
                    db,
                    first_stream['live_chat_id'],
                    reset_on_new_live_chat=True,
                    video_id=first_stream['video_id'],
                    video_url=first_stream['video_url']
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
    finally:
        if db:
            db.close()


@app.post("/api/youtube/livechatid", response_model=LiveChatIdResponse)
async def youtube_livechatid(request: LiveChatIdRequest):
    api = get_youtube_api()
    video_id = extract_video_id(request.video_url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid video URL")
    if not api.check_if_live(video_id):
        raise HTTPException(status_code=400, detail="Video is not live")
    live_chat_id = api.get_live_chat_id(video_id)
    if not live_chat_id:
        raise HTTPException(status_code=404, detail="No active live chat found")
    return LiveChatIdResponse(video_id=video_id, live_chat_id=live_chat_id)


@app.post("/api/collector/set_session")
async def collector_set_session(request: CollectorSetSessionRequest):
    # Stop collector first so we don't fight over DB locks while clearing/resetting
    try:
        get_collector().stop()
    except Exception:
        pass
    db = get_db_session()
    try:
        current_session = get_current_stream_session(db)
        # If main page is setting session and the existing session came from a different place/channel,
        # clear so main always uses its own stream.
        if current_session and request.origin == "main":
            if (current_session.origin and current_session.origin != "main") or (
                current_session.channel_url and request.channel_url and current_session.channel_url != request.channel_url
            ):
                print("TEMP: Main page session mismatch, clearing stored data")
                clear_stream_data(db)
                current_session = None

        # If testing is trying to override an existing main session, refuse.
        if current_session and request.origin == "testing" and current_session.origin == "main":
            raise HTTPException(status_code=409, detail="Main session active; testing will not override it.")

        if not current_session or current_session.live_chat_id != request.live_chat_id:
            print("TEMP: Setting new session, clearing old data")
            clear_stream_data(db)
            get_or_create_stream_session(
                db,
                request.live_chat_id,
                reset_on_new_live_chat=False,
                video_id=request.video_id,
                video_url=request.video_url,
                origin=request.origin,
                channel_url=request.channel_url
            )
        else:
            # Same live chat: just ensure metadata is up to date
            print("TEMP: Session unchanged, not clearing data")
            from app.db import update_stream_session
            update_stream_session(db, current_session, video_id=request.video_id, video_url=request.video_url)
            current_session.origin = request.origin
            current_session.channel_url = request.channel_url
            db.commit()
    finally:
        db.close()
    # Auto-start collector so UI doesn't depend on a separate call
    try:
        get_collector().start(request.live_chat_id)
    except Exception as e:
        print("TEMP: Failed to auto-start collector:", str(e))
    return {"ok": True}


@app.post("/api/collector/start")
async def collector_start():
    db = get_db_session()
    try:
        current_session = get_current_stream_session(db)
        if not current_session:
            raise HTTPException(status_code=404, detail="No active stream session in DB")
        get_collector().start(current_session.live_chat_id)
        return {"ok": True}
    finally:
        db.close()


@app.post("/api/collector/stop")
async def collector_stop():
    get_collector().stop()
    return {"ok": True}


@app.get("/api/collector/status", response_model=CollectorStatusResponse)
async def collector_status():
    state = get_collector().status()
    db = get_db_session()
    try:
        current_session = get_current_stream_session(db)
        if current_session:
            total_comments = db.query(StreamMessage).filter(StreamMessage.session_id == current_session.id).count()
        else:
            total_comments = 0
    finally:
        db.close()
    return CollectorStatusResponse(
        collecting=bool(state.get("collecting")),
        live_chat_id=state.get("live_chat_id"),
        total_comments=total_comments,
        last_error=state.get("last_error")
    )