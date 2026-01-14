# RAFFLERi - Weighted Comment Raffle System

RAFFLERi is a web-based raffle tool that fetches YouTube video comments, weights entries by comment count (max 5 per user), and randomly selects one winner per raffle.

## Features

- Fetches comments from YouTube videos
- Weights entries based on comment count (1-5 entries per user)
- Randomly selects one winner from the weighted pool
- Beautiful animated UI with Tailwind CSS
- Each raffle is independent - no tracking of previous winners

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

1. Select platform (currently only YouTube is supported)
2. Enter a YouTube video URL
3. Click "Run Raffle"
4. Wait for the animation to complete
5. View the winner and statistics

## Project Structure

```
raffleri/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── youtube_api.py      # YouTubeAPI class implementation
│   │   └── tiktok_api.py       # TikTokAPI placeholder
│   ├── services/
│   │   ├── __init__.py
│   │   └── raffle.py           # Platform-agnostic raffle logic
│   ├── models/
│   │   ├── __init__.py
│   │   └── raffle.py           # Pydantic models
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
Runs a raffle for YouTube video comments.

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
    "entries": 3
  },
  "total_entries": 150,
  "total_participants": 45,
  "platform": "youtube"
}
```

### POST /api/tiktok/entries
Placeholder endpoint (returns 501 Not Implemented).

## License

MIT
