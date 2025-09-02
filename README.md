# 🌱 SDG Teacher Chatbot

An educational chatbot powered by Google's Gemini AI, focused on ethics, sustainability, and the UN Sustainable Development Goals (SDGs). This chatbot provides personalized learning experiences with conversation memory and a professional web interface.

## ✨ Features

- **🎯 Educational Focus**: All responses revolve around ethics, sustainability, and SDG goals
- **💬 Conversation Memory**: Automatically saves and loads chat history for each user session. All conversations are stored in a dedicated `memory/` folder, which acts as a simple database. This allows the chatbot to remember details, preferences, and facts from previous interactions, even if the site is refreshed or revisited later.
- **👤 Personalized Experience**: Asks for user's name and provides personalized responses
- **🎨 Professional UI**: Modern, responsive design with smooth animations
- **📱 Mobile Friendly**: Works seamlessly on desktop and mobile devices
- **🔄 Context Awareness**: Gemini AI uses previous conversation context for better responses

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- A free Google Gemini API key

### Installation & Setup

1. **Clone or download this project** to your local machine

2. **Navigate to the project directory**:
   ```bash
   cd "Chat bot"
   ```

3. **Create and activate a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate     # On Windows
   ```

4. **Install required packages**:
   ```bash
   pip install fastapi uvicorn requests
   ```

5. **Run the chatbot**:
   ```bash
   uvicorn app:app --reload
   ```
   
   Or if you're using the virtual environment:
   ```bash
   .venv/bin/python -m uvicorn app:app --reload
   ```

6. **Open your browser** and go to:
   ```
   http://localhost:8000
   ```

## 🎮 How to Use

1. **Enter your name** when prompted on the welcome screen
2. **Start chatting** about ethics, sustainability, or any SDG-related topics
3. **Your conversations are automatically saved** and will be restored when you return
4. **Ask questions** like:
   - "What is SDG 2?"
   - "How can I live more sustainably?"
   - "What are the ethics of fast fashion?"
   - "Tell me about circular economy"

## 📁 Project Structure

```
Chat bot/
├── app.py                 # Main FastAPI application
├── templates/
│   └── index.html        # HTML template for the web interface
├── static/
│   ├── style.css         # CSS styling
│   └── script.js         # JavaScript for frontend functionality
├── memory/               # Conversation storage (auto-created, acts as a database)
│   └── session_*.json    # Individual conversation files (one per user/session)
└── README.md            # This file
```

## 🔧 Configuration

The chatbot uses Google's Gemini-1.5-Flash model, which is free tier compatible. The API key is already configured in the code.

## 🌟 Features in Detail

### Conversation Memory
- Each user session gets a unique ID
- All chat messages and bot responses are saved as JSON files in the `memory/` folder, which acts as a lightweight database
- When you return or refresh, your previous conversation is automatically loaded
- Gemini receives the last several exchanges from your chat history for more context-aware and personalized responses
- The chatbot can remember details (like your favorite color, preferences, or facts) from earlier in the conversation and use them in future answers

### UI/UX Features
- Welcome screen with name input
- Left-aligned user messages (green bubbles)
- Right-aligned bot responses (white bubbles)
- Typing indicator while processing
- Smooth animations and transitions
- Markdown formatting support (**bold**, *italic*)

### Educational Focus
- All responses are filtered through an educational lens
- Focus on ethics, sustainability, and SDG goals
- Off-topic questions are gently redirected to relevant themes
- Teacher-like explanations that inspire and educate


**Chat not working?**
- Check your internet connection (required for Gemini API)
- Look at the browser console for error messages (F12 → Console)

**Want to reset conversations?**
- Delete the `memory/` folder to clear all saved conversations. The folder will be recreated automatically when you start a new chat.

## 🎯 About

Created by Namai, an interdisciplinary dual major student passionate about sustainability and ethical technology. This chatbot serves as an educational tool to promote awareness about the UN Sustainable Development Goals and encourage ethical thinking.

## 📄 License

This project is open source and available for educational purposes.
