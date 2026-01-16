# RAFFLERi - Weighted Live Chat Raffle System

RAFFLERi is a web-based raffle tool that fetches live chat messages from active YouTube live streams, weights entries by message count (max 5 per user), and randomly selects one winner per raffle. The winner's comment text is displayed along with their username.

## Features

- Fetches live chat messages from active YouTube live streams
- Checks if a video is currently live before processing
- Weights entries based on message count (1-5 entries per user)
- Randomly selects one winner from the weighted pool
- Displays the winning comment text along with the winner's username
- Beautiful animated UI with Tailwind CSS
- Each raffle is independent - no tracking of previous winners
- Optional: Check if a YouTube channel has an active live stream

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- YouTube Data API v3 key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd raffleri
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:
```bash
YOUTUBE_API_KEY=your_youtube_api_key_here
```

### Getting a YouTube API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Click "Select a project" dropdown → "New Project"
4. Enter project name (e.g., "RAFFLERi") → Click "Create"
5. Wait for project creation, then select it from the dropdown
6. Navigate to "APIs & Services" → "Library" (or use search)
7. Search for "YouTube Data API v3"
8. Click on "YouTube Data API v3" → Click "Enable"
9. Go to "APIs & Services" → "Credentials"
10. Click "+ CREATE CREDENTIALS" → Select "API key"
11. Copy the generated API key
12. (Optional) Click "Restrict key" to limit usage to YouTube Data API v3
13. Create `.env` file in project root: `YOUTUBE_API_KEY=your_api_key_here`
14. For production (Render): Add `YOUTUBE_API_KEY` in Render dashboard → Environment tab

## Running the Application

### Local Development

1. Make sure your virtual environment is activated
2. Run the FastAPI server:
```bash
uvicorn app.main:app --reload
```

3. Open your browser and navigate to:
```
http://localhost:8000
```

### Production (Render)

1. Set the `YOUTUBE_API_KEY` environment variable in Render dashboard
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Usage

1. Enter a YouTube live stream URL (must be an active live stream)
2. Click "Run Raffle"
3. Wait for the animation to complete
4. View the winner, their winning comment, and statistics

**Note:** Only active live streams are supported. Archived live streams are not accessible via the official YouTube API.

## Project Structure

```
raffleri/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── youtube_api.py      # YouTubeAPI class (active live streams only)
│   ├── services/
│   │   ├── __init__.py
│   │   └── raffle.py           # Platform-agnostic raffle logic
│   ├── models/
│   │   ├── __init__.py
│   │   └── raffle.py           # Pydantic models (with comment text)
│   └── utils/
│       ├── __init__.py
│       └── youtube.py           # YouTube URL parsing utilities
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── images/                 # Directory for user-added images
├── templates/
│   └── index.html
├── .env                        # Local environment variables (gitignored)
├── .env.example
├── requirements.txt
├── .gitignore
└── README.md
```

## API Endpoints

### GET /
Serves the main HTML page.

### POST /api/youtube/entries
Runs a raffle for YouTube live chat messages from an active live stream.

**Request Body:**
```json
{
  "video_url": "https://www.youtube.com/watch?v=...",
  "winners": 1
}
```

**Response:**
```json
{
  "winner": {
    "platform": "youtube",
    "user_id": "...",
    "username": "...",
    "entries": 3,
    "comment_text": "This is the winning comment!"
  },
  "total_entries": 150,
  "total_participants": 45,
  "platform": "youtube"
}
```

**Error Responses:**
- `400 Bad Request`: Video is not live, live chat not enabled, or stream has ended
- `404 Not Found`: No live chat messages found

### POST /api/youtube/channel
Check if a YouTube channel has an active live stream (optional feature).

**Request Body:**
```json
{
  "channel_url": "https://www.youtube.com/@channelname"
}
```
or
```json
{
  "channel_id": "UC..."
}
```

**Response:**
```json
{
  "is_live": true,
  "video_id": "...",
  "video_url": "https://www.youtube.com/watch?v=...",
  "live_chat_id": "..."
}
```

**Error Responses:**
- `400 Bad Request`: Invalid channel URL/ID or API error
- `404 Not Found`: No active live stream found for this channel

## License

MIT
