const chatWindow = document.getElementById('chat-window');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const welcomeScreen = document.getElementById('welcome-screen');
const chatInterface = document.getElementById('chat-interface');
const usernameInput = document.getElementById('username');
const startChatBtn = document.getElementById('start-chat');
const userDisplayName = document.getElementById('user-display-name');

let currentUsername = '';
let sessionId = localStorage.getItem('sdg_session_id') || generateSessionId();

function generateSessionId() {
    const id = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('sdg_session_id', id);
    return id;
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
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message, 
                username: currentUsername,
                session_id: sessionId
            })
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
