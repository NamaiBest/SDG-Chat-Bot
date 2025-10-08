# 🌱 SDG Teacher & Multi-Persona AI Assistant

A powerful dual-mode intelligent chatbot powered by Google's Gemini AI. Switch between **Sustainability Teacher** mode for ethics and UN SDG education, or **Multi-Persona Assistant** mode featuring six specialized AI personalities (Chef, Teacher, Tech, Motivation, Finance, Knowledge) that automatically switch based on your needs. Features personalized video analysis, advanced conversation memory, and multimodal capabilities.

## ✨ Features

### 🔄 Dual Mode System
- **🌱 Sustainability Teacher Mode**: Educational focus on ethics, sustainability, and UN SDGs with personalized, caring responses
- **🎭 Multi-Persona Assistant Mode**: Six specialized AI personalities that automatically switch based on your needs

### 🎭 Multi-Persona AI Personalities

#### Your Personal AI Team:
- **👨‍🍳 Chef You**: Cooking, recipes, meal planning, nutrition, food safety, kitchen organization
- **👨‍🏫 Teacher You**: Learning, education, study tips, explaining concepts, homework help, skill development  
- **👨‍💻 Tech You**: Technology, gadgets, software, troubleshooting, digital organization, apps, devices
- **💪 Motivation You**: Encouragement, goal setting, productivity, wellness, mental health, personal growth
- **💰 Finance You**: Money management, budgeting, savings, investment basics, financial planning
- **🧠 Knowledge You**: General knowledge, facts, research, curiosity-driven questions, trivia

*Each persona automatically activates based on your question and responds with their specialized expertise!*

### 🧠 Advanced Memory & Analysis
- 💬 **Cross-mode conversation memory**: Seamlessly remembers discussions across both modes
- 🎯 **Context-aware responses**: AI adapts to your mood and needs (offers support if you look sad/stressed in videos)
- 📊 **Ultra-detailed media analysis**: Comprehensive breakdown of your environment, belongings, and activities
- ⏰ **Time-tracking**: Monitors changes in your space and habits over time
- 📊 **Enhanced context window**: Up to 20 recent exchanges for better conversation continuity

### 🖼️ Multimodal Capabilities with Optional Context
- 📷 **Webcam integration**: Capture photos directly in-browser for instant analysis
- 🎥 **Video recording with optional context**: Record videos and optionally add text descriptions for targeted analysis
- 📁 **File uploads**: Upload images and videos for detailed analysis
- 🎤 **Voice input**: Record voice messages with automatic transcription and environmental audio analysis
- � **Video context feature**: After recording, add optional text context like "Review my presentation skills" or "Check my cooking technique"
- 🏷️ **Smart tagging**: Visual confirmation when video is saved with optional description field

### 🎨 Professional Interface
- 🎯 **Modern UI**: Clean, responsive design with smooth animations
- 📱 **Mobile friendly**: Optimized for all devices with touch-friendly controls  
- 🖼️ **Media preview**: Corner preview system for captured media
- 📝 **Markdown support**: Rich text formatting in responses
- ↩️ **Navigation**: Easy return to main page from chat interface
- 🎭 **Modal system**: Elegant profile creation with background collection

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
  # On macOS/Linux
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

### Getting Started
1. **Choose your mode** using the toggle switch:
   - 🌱 **Sustainability Teacher**: For education about ethics, sustainability, and SDGs
   - 🤖 **Personal Assistant**: For environment analysis and personalized help

2. **Create or select a profile**:
   - **New users**: Create a profile with your background information for personalized responses
   - **Returning users**: Select your existing profile to continue with your conversation history

3. **Start chatting** - your conversations are automatically saved and restored

### 🌱 Sustainability Teacher Mode
Perfect for learning and education. Ask questions like:
- "What is SDG 2?"
- "How can I live more sustainably?"
- "What are the ethics of fast fashion?"
- "Tell me about circular economy"
- "Analyze the environmental impact in this image/video"

### 🤖 Personal Assistant Mode  
Ideal for practical help and environment analysis. Try:
- **Environment scanning**: "What do you see in my room?" (with photos/videos)
- **Meal planning**: "What can I cook with these ingredients?" (show your fridge/pantry)
- **Organization help**: "How should I organize this space?"
- **Resource optimization**: "What can I do with these items?"
- **Safety assessment**: "Is there anything unsafe here?"

### 🎤 Voice & Media Features
- **Voice messages**: Record speech for automatic transcription and environmental audio analysis
- **Camera capture**: Take photos directly in the app for instant analysis  
- **Video recording**: Record your environment for comprehensive assessment
- **File uploads**: Upload existing images and videos

## 📁 Project Structure

```
Chat bot/
├── app.py                 # Main FastAPI application with dual-mode support
├── config/
│   └── gemini_key.py     # Holds GEMINI_API_KEY (keep private)
├── templates/
│   └── index.html        # HTML template with modal system and dual-mode interface
├── static/
│   ├── style.css         # CSS styling with mode-specific themes and modal effects
│   └── script.js         # JavaScript for frontend functionality, profile management, media handling
├── memory/               # Conversation storage (auto-created, acts as a database)
│   ├── sustainability/   # Sustainability Teacher mode conversations
│   │   └── session_*.json
│   └── personal_assistant/ # Personal Assistant mode conversations  
│       └── session_*.json
└── README.md            # This file
```

## 🔧 Configuration

The chatbot uses Google's Gemini-1.5-Flash model, which is free tier compatible. The API key is already configured in the code.

## 🌟 Features in Detail

### 🧠 Advanced Memory System
- **Cross-mode continuity**: Conversations are remembered across both Sustainability Teacher and Personal Assistant modes
- **Profile-based memory**: Each profile maintains its own conversation history and environment observations
- **Enhanced context window**: AI receives up to 20 recent exchanges for better conversation flow
- **Time-aware memory**: Environment observations are timestamped for tracking changes over time
- **Background-aware responses**: AI tailors advice based on your profile background (student, professional, etc.)

### 👤 Profile Management
- **Background collection**: Profiles store your living situation and background for personalized responses
- **Multiple profiles**: Create different profiles for different contexts or users
- **Modal interface**: Clean, professional profile creation with detailed background collection
- **Persistent sessions**: Each profile maintains its own conversation continuity

### 🎯 Mode-Specific Features

#### 🌱 Sustainability Teacher Mode
- Educational responses focused on ethics, sustainability, and UN SDGs
- Gentle redirection of off-topic questions to relevant themes  
- Teacher-like explanations that inspire and educate
- Analysis of media through sustainability lens

#### 🤖 Personal Assistant Mode
- **Detailed environment analysis**: Comprehensive inventory of visible objects, conditions, safety assessment
- **Meal planning**: Recipe suggestions based on visible ingredients
- **Organization advice**: Space optimization and resource management
- **Adaptive responses**: Advice tailored to your background (student budget-friendly, professional efficiency-focused, etc.)
- **Environmental memory**: Detailed tracking of your belongings and space changes over time

### 🎨 User Interface
- **Dual-mode toggle**: Smooth switching between modes with visual feedback
- **Modern design**: Glass-morphism effects, smooth animations, professional appearance
- **Responsive layout**: Optimized for mobile and desktop with touch-friendly controls
- **Media integration**: Corner preview system, camera overlay, real-time recording feedback
- **Navigation**: Easy return to main page, clear visual hierarchy


**Chat not working?**
- Check your internet connection (required for Gemini API)
- Look at the browser console for error messages (F12 → Console)

**Want to reset conversations?**
- Delete the `memory/` folder to clear all saved conversations. The folder will be recreated automatically when you start a new chat.

## 🎯 About

Created by Namai, an interdisciplinary dual major student passionate about sustainability and ethical technology. This chatbot serves as an educational tool to promote awareness about the UN Sustainable Development Goals and encourage ethical thinking.

## 📄 License

This project is open source and available for educational purposes.
