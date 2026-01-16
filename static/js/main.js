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
});

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
