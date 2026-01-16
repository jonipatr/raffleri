// Radio button change handlers
const urlTypeVideo = document.getElementById('url-type-video');
const urlTypeChannel = document.getElementById('url-type-channel');
const urlInput = document.getElementById('video-url');
const urlLabel = document.getElementById('url-label');
const urlHelpText = document.getElementById('url-help-text');
const streamSelectContainer = document.getElementById('stream-selection-container');
const streamSelect = document.getElementById('stream-select');

urlTypeVideo.addEventListener('change', () => {
    if (urlTypeVideo.checked) {
        urlLabel.textContent = 'YouTube Live Stream URL';
        urlInput.placeholder = 'https://www.youtube.com/watch?v=...';
        urlHelpText.textContent = 'Enter a URL for an active YouTube live stream';
        streamSelectContainer.classList.add('hidden');
        urlInput.value = '';
    }
});

urlTypeChannel.addEventListener('change', () => {
    if (urlTypeChannel.checked) {
        urlLabel.textContent = 'YouTube Channel URL';
        urlInput.placeholder = 'https://www.youtube.com/@channelname';
        urlHelpText.textContent = 'Enter a channel URL to find active live streams';
        streamSelectContainer.classList.add('hidden');
        urlInput.value = '';
    }
});

// Run raffle button
document.getElementById('run-raffle-btn').addEventListener('click', async () => {
    const inputUrl = document.getElementById('video-url').value.trim();
    const isChannelUrl = urlTypeChannel.checked;
    
    if (!inputUrl) {
        showError('Please enter a URL');
        return;
    }
    
    // Hide previous results and errors
    document.getElementById('results-container').classList.add('hidden');
    document.getElementById('error-container').classList.add('hidden');
    streamSelectContainer.classList.add('hidden');
    
    try {
        let videoUrl = inputUrl;
        
        // If channel URL, first get active streams
        if (isChannelUrl) {
            showLoadingAnimation();
            const loadingText = document.getElementById('animation-text');
            loadingText.textContent = 'Checking for active live streams...';
            
            // Fetch active streams
            const streamsResponse = await fetch('/api/youtube/channel/streams', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    channel_url: inputUrl
                })
            });
            
            const streamsData = await streamsResponse.json();
            
            if (!streamsResponse.ok) {
                throw new Error(streamsData.detail || 'Failed to fetch active streams');
            }
            
            if (streamsData.streams.length === 0) {
                hideLoadingAnimation();
                throw new Error('No active live streams found for this channel');
            }
            
            // If multiple streams, show dropdown
            if (streamsData.streams.length > 1) {
                hideLoadingAnimation();
                
                // Populate dropdown
                streamSelect.innerHTML = '<option value="">Select a stream...</option>';
                streamsData.streams.forEach((stream, index) => {
                    const option = document.createElement('option');
                    option.value = stream.video_url;
                    option.textContent = stream.title || `Stream ${index + 1}`;
                    streamSelect.appendChild(option);
                });
                
                streamSelectContainer.classList.remove('hidden');
                
                // Wait for user to select a stream
                return new Promise((resolve) => {
                    streamSelect.addEventListener('change', async function onStreamSelect() {
                        const selectedUrl = streamSelect.value;
                        if (selectedUrl) {
                            streamSelect.removeEventListener('change', onStreamSelect);
                            videoUrl = selectedUrl;
                            streamSelectContainer.classList.add('hidden');
                            // Continue with raffle
                            await runRaffle(videoUrl);
                            resolve();
                        }
                    });
                });
            } else {
                // Single stream, auto-select
                videoUrl = streamsData.streams[0].video_url;
            }
        }
        
        // Run the raffle with the video URL
        await runRaffle(videoUrl);
        
    } catch (error) {
        hideLoadingAnimation();
        hideRaffleAnimation();
        if (error.name === 'AbortError') {
            showError('Request timed out. The stream may have too many messages. Please try with a smaller stream or wait a moment and try again.');
        } else {
            showError(error.message || 'An error occurred while processing the raffle');
        }
    }
});

async function runRaffle(videoUrl) {
    try {
        // Show loading animation while fetching
        showLoadingAnimation();
        
        // Add timeout to prevent hanging (60 seconds)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000);
        
        const response = await fetch('/api/youtube/entries', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                video_url: videoUrl,
                winners: 1
            }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'An error occurred');
        }
        
        // Hide loading, show raffle animation
        hideLoadingAnimation();
        showRaffleAnimation();
        
        // Wait for raffle animation (2-3 seconds)
        await new Promise(resolve => setTimeout(resolve, 2500));
        
        // Hide animation and show results
        hideRaffleAnimation();
        showResults(data);
        
    } catch (error) {
        hideLoadingAnimation();
        hideRaffleAnimation();
        if (error.name === 'AbortError') {
            showError('Request timed out. The stream may have too many messages. Please try with a smaller stream or wait a moment and try again.');
        } else {
            showError(error.message || 'An error occurred while processing the raffle');
        }
    }
}

function showLoadingAnimation() {
    const container = document.getElementById('animation-container');
    const text = document.getElementById('animation-text');
    const spinner = document.getElementById('spinner');
    
    container.classList.remove('hidden');
    spinner.classList.remove('hidden');
    spinner.classList.add('spinning');
    text.textContent = 'Fetching live chat messages...';
}

function hideLoadingAnimation() {
    const spinner = document.getElementById('spinner');
    // Don't hide spinner, just change animation - it will be used for raffle animation
    spinner.classList.remove('spinning');
}

function showRaffleAnimation() {
    const text = document.getElementById('animation-text');
    const spinner = document.getElementById('spinner');
    
    // Make sure spinner is visible and change to raffle animation
    spinner.classList.remove('hidden');
    spinner.classList.remove('spinning');
    spinner.classList.add('pulsing');
    text.textContent = 'Selecting winner...';
    
    // Add some excitement with text animation
    let countdown = 3;
    const countdownInterval = setInterval(() => {
        if (countdown > 0) {
            text.textContent = `Selecting winner... ${countdown}`;
            text.classList.add('countdown-animation');
            setTimeout(() => {
                text.classList.remove('countdown-animation');
            }, 500);
            countdown--;
        } else {
            clearInterval(countdownInterval);
            text.textContent = 'And the winner is...';
        }
    }, 600);
}

function hideRaffleAnimation() {
    document.getElementById('animation-container').classList.add('hidden');
    const spinner = document.getElementById('spinner');
    spinner.classList.remove('pulsing');
}

function showResults(data) {
    const container = document.getElementById('results-container');
    const winnerUsername = document.getElementById('winner-username');
    const winnerCommentText = document.getElementById('winner-comment-text');
    const winnerCommentDiv = document.getElementById('winner-comment');
    const totalEntries = document.getElementById('total-entries');
    const totalParticipants = document.getElementById('total-participants');
    
    winnerUsername.textContent = data.winner.username;
    totalEntries.textContent = data.total_comments;
    totalParticipants.textContent = data.total_participants;
    
    // Show comment text if available
    if (data.winner.comment_text) {
        winnerCommentText.textContent = data.winner.comment_text;
        winnerCommentDiv.classList.remove('hidden');
    } else {
        winnerCommentDiv.classList.add('hidden');
    }
    
    container.classList.remove('hidden');
    
    // Add reveal animation
    const winnerDisplay = document.getElementById('winner-display');
    winnerDisplay.classList.add('winner-reveal');
    setTimeout(() => {
        winnerDisplay.classList.remove('winner-reveal');
    }, 1500);
}

function showError(message) {
    const container = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    
    errorMessage.textContent = message;
    container.classList.remove('hidden');
}
