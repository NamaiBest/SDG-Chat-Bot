const chatWindow = document.getElementById('chat-window');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const welcomeScreen = document.getElementById('welcome-screen');
const chatInterface = document.getElementById('chat-interface');
const usernameInput = document.getElementById('username');
const startChatBtn = document.getElementById('start-chat');
const userDisplayName = document.getElementById('user-display-name');

// Camera elements
const toggleCameraBtn = document.getElementById('toggle-camera');
const captureImageBtn = document.getElementById('capture-image');
const clearImageBtn = document.getElementById('clear-image');
const cameraVideo = document.getElementById('camera-video');
const cameraCanvas = document.getElementById('camera-canvas');
const cameraContainer = document.getElementById('camera-container');
const capturedImageContainer = document.getElementById('captured-image-container');
const capturedImage = document.getElementById('captured-image');

let currentUsername = '';
let sessionId = localStorage.getItem('sdg_session_id') || generateSessionId();
let cameraStream = null;
let isCameraOn = false;
let capturedImageData = null;

function generateSessionId() {
    const id = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('sdg_session_id', id);
    return id;
}

// Camera Functions
async function toggleCamera() {
    if (!isCameraOn) {
        try {
            console.log('Requesting camera access...');
            cameraStream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 640 }, 
                    height: { ideal: 480 },
                    facingMode: 'user'
                } 
            });
            console.log('Camera access granted');
            
            cameraVideo.srcObject = cameraStream;
            cameraContainer.style.display = 'block';
            toggleCameraBtn.textContent = '📷 Turn Off Camera';
            isCameraOn = true;
            
            // Hide captured image when turning on camera
            capturedImageContainer.style.display = 'none';
            clearImageBtn.style.display = 'none';
            capturedImageData = null;
            
        } catch (error) {
            console.error('Camera error:', error);
            alert('Camera access denied or not available. Please check your browser permissions and try again.');
        }
    } else {
        console.log('Turning off camera...');
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
            cameraStream = null;
        }
        cameraContainer.style.display = 'none';
        toggleCameraBtn.textContent = '📷 Turn On Camera';
        isCameraOn = false;
    }
}

function captureImage() {
    console.log('Capturing image...');
    const canvas = cameraCanvas;
    const context = canvas.getContext('2d');
    
    // Set canvas size to match video
    canvas.width = cameraVideo.videoWidth;
    canvas.height = cameraVideo.videoHeight;
    
    // Draw the video frame to canvas
    context.drawImage(cameraVideo, 0, 0, canvas.width, canvas.height);
    
    // Convert to base64 JPEG
    capturedImageData = canvas.toDataURL('image/jpeg', 0.8);
    capturedImage.src = capturedImageData;
    
    // Show captured image and hide camera
    capturedImageContainer.style.display = 'block';
    clearImageBtn.style.display = 'inline-block';
    
    // Turn off camera after capture
    toggleCamera();
    
    console.log('Image captured successfully');
}

function clearImage() {
    console.log('Clearing captured image...');
    capturedImageData = null;
    capturedImageContainer.style.display = 'none';
    clearImageBtn.style.display = 'none';
}

function convertMarkdownToHtml(text) {
    // Convert **bold** to <strong>bold</strong>
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Convert *italic* to <em>italic</em>
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Convert line breaks to <br>
    text = text.replace(/\n/g, '<br>');
    return text;
}

function appendMessage(role, text, animate = true) {
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container';
    
    const msgDiv = document.createElement('div');
    msgDiv.className = role === 'user' ? 'user-msg' : 'bot-msg';
    
    if (role === 'bot') {
        msgDiv.innerHTML = convertMarkdownToHtml(text);
    } else {
        msgDiv.textContent = text;
    }
    
    messageContainer.appendChild(msgDiv);
    chatWindow.appendChild(messageContainer);
    
    if (animate) {
        msgDiv.style.opacity = '0';
        msgDiv.style.transform = 'translateY(20px)';
        setTimeout(() => {
            msgDiv.style.transition = 'all 0.3s ease';
            msgDiv.style.opacity = '1';
            msgDiv.style.transform = 'translateY(0)';
        }, 50);
    }
    
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function startChat() {
    const username = usernameInput.value.trim();
    if (!username) {
        usernameInput.focus();
        return;
    }
    
    currentUsername = username;
    userDisplayName.textContent = username;
    localStorage.setItem('sdg_username', username);
    
    welcomeScreen.style.display = 'none';
    chatInterface.style.display = 'block';
    
    // Load previous conversation if exists
    loadConversationHistory();
    
    // Welcome message
    setTimeout(() => {
        appendMessage('bot', `Hello ${username}! 🌱 I'm your SDG Teacher. I'm here to help you learn about ethics, sustainability, and the UN Sustainable Development Goals. What would you like to explore today?`);
    }, 500);
    
    userInput.focus();
}

async function loadConversationHistory() {
    try {
        const response = await fetch(`/conversation/${sessionId}`);
        const data = await response.json();
        
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                appendMessage('user', msg.user_message, false);
                appendMessage('bot', msg.bot_response, false);
            });
        }
    } catch (error) {
        console.log('No previous conversation found');
    }
}

// Event Listeners
startChatBtn.addEventListener('click', startChat);
toggleCameraBtn.addEventListener('click', toggleCamera);
captureImageBtn.addEventListener('click', captureImage);
clearImageBtn.addEventListener('click', clearImage);

usernameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        startChat();
    }
});

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (!message) return;
    
    appendMessage('user', message);
    userInput.value = '';
    
    // Show typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message-container typing-indicator';
    typingDiv.innerHTML = '<div class="bot-msg">🤔 Thinking...</div>';
    chatWindow.appendChild(typingDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    
    try {
        const requestData = { 
            message, 
            username: currentUsername,
            session_id: sessionId
        };
        
        // Add image data if available
        if (capturedImageData) {
            requestData.image = capturedImageData;
        }
        
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        const data = await res.json();
        
        // Remove typing indicator
        chatWindow.removeChild(typingDiv);
        
        appendMessage('bot', data.reply);
        
        // Update session ID if new one was created
        if (data.session_id) {
            sessionId = data.session_id;
            localStorage.setItem('sdg_session_id', sessionId);
        }
    } catch (error) {
        chatWindow.removeChild(typingDiv);
        appendMessage('bot', 'Sorry, I encountered an error. Please try again.');
    }
});

// Initialize
window.addEventListener('load', () => {
    const savedUsername = localStorage.getItem('sdg_username');
    if (savedUsername) {
        usernameInput.value = savedUsername;
    }
    usernameInput.focus();
});
