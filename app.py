from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import requests
import uvicorn
import os
import json
import base64
from datetime import datetime
import uuid
from config.gemini_key import GEMINI_API_KEY

app = FastAPI()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-1.5-flash"  # Free tier compatible model

SYSTEM_PROMPT = (
    "You are an expert teacher chatbot focused on ethics, sustainability, and environmental awareness. "
    "You should naturally weave these themes into conversations without forcing them. "
    "Be conversational and remember details from our chat history. "
    "Only mention UN SDG goals when they naturally fit the conversation - don't force them into every response. "
    "If a question is completely off-topic, gently guide toward sustainability themes. "
    "If someone asks about the creator, Namai is an interdisciplinary dual major student who created this chatbot. "
    "When analyzing images, relate them to sustainability, ethics, or environmental topics when relevant. "
    "Look for opportunities to discuss sustainable practices, environmental impact, or ethical considerations in what you see."
)

# Serve static files (for custom CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create memory directory for storing conversations
MEMORY_DIR = "memory"
if not os.path.exists(MEMORY_DIR):
    os.makedirs(MEMORY_DIR)

def save_conversation(session_id, username, message, response, has_image=False):
    """Save conversation to memory"""
    try:
        file_path = os.path.join(MEMORY_DIR, f"{session_id}.json")
        conversation_data = {
            "username": username,
            "messages": []
        }
        
        # Load existing conversation if exists
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                conversation_data = json.load(f)
        
        # Add new message
        conversation_data["messages"].append({
            "timestamp": datetime.now().isoformat(),
            "user_message": message,
            "bot_response": response,
            "has_image": has_image
        })
        
        # Save updated conversation
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Conversation saved to: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Error saving conversation: {e}")
        return False

def load_conversation(session_id):
    """Load conversation from memory"""
    try:
        file_path = os.path.join(MEMORY_DIR, f"{session_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Loaded conversation from: {file_path} - {len(data.get('messages', []))} messages")
                return data
        else:
            print(f"ℹ️ No conversation file found: {file_path}")
        return None
    except Exception as e:
        print(f"❌ Error loading conversation: {e}")
        return None

def get_conversation_context(session_id):
    """Get recent conversation history for better responses"""
    conversation = load_conversation(session_id)
    if not conversation or not conversation.get("messages"):
        print(f"ℹ️ No conversation context for session: {session_id}")
        return ""
    
    # Get last 10 exchanges for better context retention (increased from 5)
    recent_messages = conversation["messages"][-10:]
    context = "Here's our conversation history so you can remember important details:\n\n"
    for msg in recent_messages:
        image_note = " (with image)" if msg.get("has_image") else ""
        context += f"User: {msg['user_message']}{image_note}\nYou responded: {msg['bot_response']}\n\n"
    
    context += "Remember any personal details, preferences, or facts mentioned by the user in this conversation.\n"
    
    print(f"✅ Using context from {len(recent_messages)} previous messages")
    return context

@app.get("/", response_class=HTMLResponse)
def get_chat_page():
    with open("templates/index.html", "r") as f:
        html = f.read()
    return HTMLResponse(content=html)

@app.get("/models")
async def list_models():
    """List available Gemini models"""
    try:
        response = requests.get(f"{GEMINI_BASE_URL}/models?key={GEMINI_API_KEY}")
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.text}
    except Exception as e:
        return {"error": str(e)}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("message", "")
    username = data.get("username", "User")
    session_id = data.get("session_id", str(uuid.uuid4()))
    image_data = data.get("image", None)
    
    print(f"🔄 Processing chat - Session: {session_id}, User: {username}, Has Image: {bool(image_data)}")
    
    # Get conversation context for better responses
    context = get_conversation_context(session_id)
    
    # Create prompt with context
    if context:
        prompt = f"{SYSTEM_PROMPT}\n\n{context}\n\nCurrent user ({username}): {user_input}\n\nRemember to reference any relevant details from our conversation history when appropriate."
    else:
        prompt = f"{SYSTEM_PROMPT}\n\nUser ({username}): {user_input}"
    
    # Prepare payload for Gemini API
    parts = [{"text": prompt}]
    
    # Add image if provided
    if image_data:
        try:
            # Extract base64 data (remove data:image/jpeg;base64, prefix)
            base64_data = image_data.split(',')[1]
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64_data
                }
            })
            print("✅ Image added to request")
        except Exception as e:
            print(f"❌ Error processing image: {e}")
    
    payload = {
        "contents": [
            {
                "parts": parts
            }
        ]
    }
    
    try:
        api_url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        response = requests.post(api_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                bot_reply = data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                bot_reply = "Sorry, I couldn't generate a response."
        else:
            error_detail = response.text
            bot_reply = f"Gemini API error: {error_detail}"
    except Exception as e:
        bot_reply = f"Exception: {str(e)}"
    
    # Save conversation to memory
    save_success = save_conversation(session_id, username, user_input, bot_reply, bool(image_data))
    if not save_success:
        print("⚠️ Failed to save conversation to memory")
    
    return JSONResponse({"reply": bot_reply, "session_id": session_id})

@app.get("/conversation/{session_id}")
async def get_conversation(session_id: str):
    """Get conversation history"""
    conversation = load_conversation(session_id)
    if conversation:
        return conversation
    return {"messages": []}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
