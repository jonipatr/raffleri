// Run raffle button
document.getElementById('run-raffle-btn').addEventListener('click', async () => {
    const videoUrl = document.getElementById('video-url').value.trim();
    
    if (!videoUrl) {
        showError('Please enter a video URL');
        return;
    }
    
    // Hide previous results and errors
    document.getElementById('results-container').classList.add('hidden');
    document.getElementById('error-container').classList.add('hidden');
    
    // Show animation
    showAnimation();
    
    try {
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
        
        // Wait for animation to complete (2-3 seconds)
        await new Promise(resolve => setTimeout(resolve, 2500));
        
        // Hide animation and show results
        hideAnimation();
        showResults(data);
        
    } catch (error) {
        hideAnimation();
        if (error.name === 'AbortError') {
            showError('Request timed out. The stream may have too many messages. Please try with a smaller stream or wait a moment and try again.');
        } else {
            showError(error.message || 'An error occurred while processing the raffle');
        }
    }
});

function showAnimation() {
    const container = document.getElementById('animation-container');
    const text = document.getElementById('animation-text');
    
    container.classList.remove('hidden');
    
    // Update text to show we're fetching messages
    text.textContent = 'Fetching live chat messages...';
    
    // Countdown effect (but keep updating text to show progress)
    let countdown = 3;
    const countdownInterval = setInterval(() => {
        if (countdown > 0) {
            text.textContent = `Fetching messages... ${countdown}`;
            text.classList.add('countdown-animation');
            setTimeout(() => {
                text.classList.remove('countdown-animation');
            }, 500);
            countdown--;
        } else {
            clearInterval(countdownInterval);
            text.textContent = 'Processing messages and selecting winner...';
        }
    }, 2000);  // Longer interval since this might take a while
}

function hideAnimation() {
    document.getElementById('animation-container').classList.add('hidden');
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
