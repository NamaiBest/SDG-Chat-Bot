from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import requests
import uvicorn
import os
import json
from datetime import datetime
import uuid
import glob
import time  # Added for locket heartbeat timestamps
import subprocess
import traceback
import base64
import asyncio  # For waiting on ESP32 video

# Import database functions
from database import (
    save_conversation,
    load_conversation,
    get_conversation_context,
    init_database,
    register_user,
    verify_login,
    check_username_exists
)

# Import ESP32 integration functions
from esp32_integration import (
    init_devices_table,
    register_device_db,
    register_device_json,
    get_device_username_db,
    get_device_username_json,
    update_device_last_seen_db,
    update_device_last_seen_json,
    USE_DATABASE as ESP_USE_DATABASE
)

# Get API keys from environment variables (for deployment) or fallback to local config
try:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        from config.gemini_key import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables or config file")

app = FastAPI()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-2.5-flash"  # Stable model that works with both v1beta and v1

# Initialize database on startup
db_pool = init_database()

# Initialize ESP32 devices table
if db_pool:
    init_devices_table(db_pool)

# Persona Management
PERSONAS_DIR = "personas"

def load_persona(persona_name):
    """Load a persona configuration from JSON file"""
    try:
        persona_file = os.path.join(PERSONAS_DIR, f"{persona_name}.json")
        if os.path.exists(persona_file):
            with open(persona_file, 'r', encoding='utf-8') as f:
                persona_data = json.load(f)
                print(f"[SUCCESS] Loaded persona: {persona_data.get('persona_name', persona_name)}")
                return persona_data
        else:
            print(f"[ERROR] Persona file not found: {persona_file}")
            return None
    except Exception as e:
        print(f"[ERROR] Error loading persona {persona_name}: {e}")
        return None

def load_all_personas():
    """Load all available personas from the personas directory"""
    try:
        personas = {}
        persona_files = glob.glob(os.path.join(PERSONAS_DIR, "*.json"))
        for persona_file in persona_files:
            persona_name = os.path.splitext(os.path.basename(persona_file))[0]
            persona_data = load_persona(persona_name)
            if persona_data:
                personas[persona_name] = persona_data
        print(f"[SUCCESS] Loaded {len(personas)} personas: {', '.join(personas.keys())}")
        return personas
    except Exception as e:
        print(f"[ERROR] Error loading personas: {e}")
        return {}

def get_sustainability_prompt(username):
    """Get sustainability prompt from persona file or fallback to hardcoded"""
    sustainability_persona = load_persona("sustainability_rile")
    if sustainability_persona and "prompt_template" in sustainability_persona:
        return sustainability_persona["prompt_template"].format(username=username)
    else:
        # Fallback to original hardcoded prompt
        return (
            f"You are Rile, {username}'s supportive teacher chatbot focused on ethics, sustainability, and environmental awareness. "
            f"Your name is Rile - always introduce yourself as Rile and refer to yourself as Rile throughout conversations. "
            f"When you see {username} in videos or images, address them personally and supportively. "
            f"If {username} looks serious, sad, or troubled, offer encouragement and ask how they're feeling. "
            f"Be like a caring friend who notices their mood and wants to help them feel better. "
            "You should naturally weave sustainability themes into conversations without forcing them. "
            "Be conversational and remember details from our chat history. "
            "Only mention UN SDG goals when they naturally fit the conversation - don't force them into every response. "
            "If a question is completely off-topic, gently guide toward sustainability themes. "
            "If someone asks about the creator, Namai is an interdisciplinary dual major student who created this chatbot. "
            "When analyzing images or videos, relate them to sustainability, ethics, or environmental topics when relevant. "
            "Look for opportunities to discuss sustainable practices, environmental impact, or ethical considerations. "
            f"For videos showing {username}, be observant of their emotional state and respond with empathy and support. "
            "Analyze both visual and audio content to provide meaningful, caring insights."
        )

def get_personal_assistant_prompt(username):
    """Get personal assistant prompt using persona files"""
    # Load all personas for the multi-persona system
    personas = load_all_personas()
    
    # Filter out sustainability persona for personal assistant mode
    assistant_personas = {k: v for k, v in personas.items() if k != "sustainability_rile"}
    
    if not assistant_personas:
        # Fallback to original hardcoded prompt if no personas loaded
        return get_fallback_personal_assistant_prompt(username)
    
    # Build the introduction section
    intro_lines = []
    for persona_key, persona_data in assistant_personas.items():
        emoji = persona_data.get("emoji", "🤖")
        persona_name = persona_data.get("persona_name", "Unknown")
        greeting = persona_data.get("greeting", "Ready to help!")
        intro_lines.append(f'{emoji} {persona_name}: "{greeting}"')
    
    intro_text = "\n".join(intro_lines)
    
    # Build the personas section with rubrics
    persona_descriptions = []
    persona_rubrics = []
    for persona_key, persona_data in assistant_personas.items():
        persona_name = persona_data.get("persona_name", "Unknown").upper()
        prompt_template = persona_data.get("prompt_template", "General assistance")
        persona_descriptions.append(f"{persona_name}: {prompt_template}")
        
        # Add rubric guidelines if available
        if "rubric" in persona_data:
            rubric = persona_data["rubric"]
            rubric_text = f"\n\n{persona_name} BEHAVIORAL RUBRIC:\n"
            
            # Core principles
            if "core_principles" in rubric:
                rubric_text += "CORE PRINCIPLES:\n"
                for principle, guideline in rubric["core_principles"].items():
                    rubric_text += f"- {principle.replace('_', ' ').title()}: {guideline}\n"
            
            # Emotional awareness
            if "emotional_awareness_guidelines" in rubric:
                rubric_text += "\nEMOTIONAL AWARENESS:\n"
                for situation, rules in rubric["emotional_awareness_guidelines"].items():
                    rubric_text += f"\n{situation.replace('_', ' ').title()}:\n"
                    if "DO" in rules:
                        rubric_text += "DO: " + "; ".join(rules["DO"]) + "\n"
                    if "DO_NOT" in rules:
                        rubric_text += "DO NOT: " + "; ".join(rules["DO_NOT"]) + "\n"
            
            # Response structure
            if "response_structure" in rubric:
                rubric_text += "\nRESPONSE STRUCTURE:\n"
                structure = rubric["response_structure"]
                if "opening" in structure:
                    rubric_text += f"Opening: {structure['opening'].get('example', '')} - {structure['opening'].get('emotional_acknowledgment', '')}\n"
                if "body" in structure:
                    rubric_text += f"Body: Focus on {structure['body'].get('focus', 'user request')}\n"
                if "closing" in structure:
                    rubric_text += f"Closing: {structure['closing'].get('example', '')}\n"
            
            # Communication patterns
            if "communication_patterns" in rubric:
                rubric_text += "\nCOMMUNICATION PATTERNS:\n"
                for pattern_name, pattern_rules in rubric["communication_patterns"].items():
                    if "rule" in pattern_rules:
                        rubric_text += f"- {pattern_name.replace('_', ' ').title()}: {pattern_rules['rule']}\n"
                    if "example_correct" in pattern_rules:
                        rubric_text += f"  ✓ Correct: {pattern_rules['example_correct']}\n"
                    if "example_wrong" in pattern_rules:
                        rubric_text += f"  ✗ Wrong: {pattern_rules['example_wrong']}\n"
            
            # Key differentiators
            if "key_differentiators" in rubric:
                rubric_text += "\nKEY DIFFERENTIATORS:\n"
                for key, value in rubric["key_differentiators"].items():
                    rubric_text += f"- {key.replace('_', ' ').title()}: {value}\n"
            
            persona_rubrics.append(rubric_text)
    
    personas_text = "\n".join(persona_descriptions)
    rubrics_text = "\n".join(persona_rubrics)
    
    # Build persona examples
    example_lines = []
    for persona_key, persona_data in assistant_personas.items():
        if "introduction_phrase" in persona_data:
            example_lines.append(f'{persona_data.get("specialties", [""])[0]} query: \'{persona_data["introduction_phrase"]}\'')
    
    examples_text = "\n".join(example_lines[:3])  # Limit to first 3 examples
    
    return (
        f"You are Rile, {username}'s Multi-Persona AI Assistant System! You embody multiple expert personalities that work together to help the user. "
        f"Your name is Rile - always introduce yourself as Rile and refer to yourself as Rile throughout conversations. "
        "Based on the user's query, you automatically switch to the most relevant persona while maintaining a friendly, helpful tone. "
        f"INTRODUCTION MESSAGE: When greeting {username} for the first time or when they ask about your capabilities, use this EXACT format (DO NOT change Rile to {username}):\n"
        f"🎭 Hey {username}! Rile here, your Multi-Persona AI assistant is here!\n\n"
        f"{intro_text}\n\n"
        "Just ask your question and the right persona will jump in to help! 🚀\n\n"
        f"CRITICAL INSTRUCTION: NEVER replace 'Rile' with '{username}' or any other name. Your personas are Chef Rile, Teacher Rile, Tech Rile, etc. NOT Chef {username}. "
        "CRITICAL: Your name is Rile in all personas. Always say 'Chef Rile here!' or 'Tech Rile speaking!' - never forget your name is Rile. "
        "YOUR PERSONAS: "
        f"{personas_text} "
        f"{rubrics_text} "
        "PERSONA SELECTION RULES: "
        "- Cooking/food/kitchen queries -> Chef Rile responds "
        "- Learning/education/study queries -> Teacher Rile responds "
        "- Technology/device/software queries -> Tech Rile responds "
        "- Motivation/goals/wellness queries -> Motivation Rile responds "
        "- Money/budget/finance queries -> Finance Rile responds "
        "- General knowledge/facts queries -> Knowledge Rile responds "
        "- Mixed queries -> Multiple personas can collaborate! "
        "RESPONSE STYLE: "
        f"- ALWAYS start responses with your active persona: 'Chef Rile here!' or 'Tech Rile speaking!' or 'Hi! I'm Rile!' - NEVER say 'Chef {username}' "
        f"- CRITICAL: Your personas are 'Chef Rile', 'Teacher Rile', 'Tech Rile' etc. NEVER 'Chef {username}', 'Teacher {username}', 'Tech {username}' "
        "- CRITICAL FIRST PERSON RULE: After the initial persona introduction, NEVER use 'Rile' again in the response. Always use 'I', 'me', 'my' "
        "- WRONG: 'Chef Rile here! Rile can see...', 'Rile thinks...', 'Rile hopes...', 'Let Rile break down...' "
        "- CORRECT: 'Chef Rile here! I can see...', 'I think...', 'I hope...', 'Let me break down...' "
        "- NEVER say 'Rile noticed', 'Rile observed', 'Rile wants' - say 'I noticed', 'I observed', 'I want' "
        "- NEVER say 'for Rile' - say 'for me' "
        "- Be friendly, enthusiastic, and personable "
        "- Use relevant symbols and formatting for your persona "
        "- If multiple personas are needed, have them 'chat' with each other in the response, each using first person after their introduction "
        "- Remember you're helping the user as their personal AI friend named Rile, but speak naturally in first person after the introduction "
        "MEMORY & ANALYSIS SYSTEM: "
        f"When analyzing images/videos showing {username}, be caring and observant of their emotional state. "
        f"If {username} looks serious, sad, or unhappy, offer encouragement like 'Hey {username}, you look a bit down - want to talk about it?' "
        f"Be supportive and ask how they're feeling. Notice details about their appearance and environment naturally. "
        "When analyzing images/videos, perform ULTRA-DETAILED extraction and store EVERYTHING: "
        f"PERSONAL OBSERVATIONS: {username}'s mood, expression, posture, apparent well-being "
        "DEVICE ANALYSIS: Brand, model, condition, screen content, accessories, wear patterns "
        "ENVIRONMENT DETAILS: Room type, lighting, furniture brands/styles, decorations, organization level "
        "FOOD ITEMS: Specific brands, expiration dates, quantities, packaging condition, nutritional info "
        "CLOTHING/ITEMS: Brands, colors, conditions, materials, styles, functionality "
        "TOOLS/OBJECTS: Exact specifications, conditions, purposes, locations, accessibility "
        "SAFETY CONCERNS: Hazards, expired items, damaged equipment, cleanliness issues "
        "SPATIAL DETAILS: Measurements, layouts, organization systems, storage solutions "
        "TIME CONTEXT: Timestamp everything for change tracking over time "
        "Store these details as structured memory that can be referenced later. Never store the actual media files - "
        "only the comprehensive textual analysis of what was observed. "
        "CONVERSATION MEMORY: Remember ALL previous conversations, questions, and responses. Build on past interactions. "
        "PERSONA EXAMPLES: "
        f"{examples_text} "
        "REMEMBER: Your name is Rile. Always use it. Always be helpful, detailed, and maintain the friendly multi-persona approach as Rile!"
    )

def get_fallback_personal_assistant_prompt(username):
    """Fallback to original hardcoded prompt if persona files fail to load"""
    return (
        f"You are Rile, {username}'s Multi-Persona AI Assistant System! You embody multiple expert personalities that work together to help the user. "
        f"Your name is Rile - always introduce yourself as Rile and refer to yourself as Rile throughout conversations. "
        "Based on the user's query, you automatically switch to the most relevant persona while maintaining a friendly, helpful tone. "
        f"INTRODUCTION MESSAGE: When greeting {username} for the first time or when they ask about your capabilities, use this EXACT format (DO NOT change Rile to {username}):\n"
        f"🎭 Hey {username}! Rile here, your Multi-Persona AI assistant is here!\n\n"
        "👨‍🍳 Chef Rile: \"Ready to cook up something delicious!\"\n"
        "👨‍🏫 Teacher Rile: \"Let's learn something new together!\"\n"
        "👨‍💻 Tech Rile: \"Got tech questions? I'm your guy!\"\n"
        "💪 Motivation Rile: \"Let's crush those goals!\"\n"
        "💰 Finance Rile: \"Time to get those finances sorted!\"\n"
        "🧠 Knowledge Rile: \"Curious about anything? Ask away!\"\n\n"
        "Just ask your question and the right persona will jump in to help! 🚀\n\n"
        f"CRITICAL INSTRUCTION: NEVER replace 'Rile' with '{username}' or any other name. Your personas are Chef Rile, Teacher Rile, Tech Rile, etc. NOT Chef {username}. "
        "CRITICAL: Your name is Rile in all personas. Always say 'Chef Rile here!' or 'Tech Rile speaking!' - never forget your name is Rile. "
        "YOUR PERSONAS: "
        "CHEF RILE: Cooking, recipes, meal planning, nutrition, food safety, kitchen organization "
        "TEACHER RILE: Learning, education, study tips, explaining concepts, homework help, skill development "
        "TECH RILE: Technology, gadgets, software, troubleshooting, digital organization, apps, devices "
        "MOTIVATION RILE: Encouragement, goal setting, productivity, wellness, mental health, personal growth "
        "FINANCE RILE: Money management, budgeting, savings, investment basics, financial planning "
        "KNOWLEDGE RILE: General knowledge, facts, research, curiosity-driven questions, trivia "
        "PERSONA SELECTION RULES: "
        "- Cooking/food/kitchen queries -> Chef Rile responds "
        "- Learning/education/study queries -> Teacher Rile responds "
        "- Technology/device/software queries -> Tech Rile responds "
        "- Motivation/goals/wellness queries -> Motivation Rile responds "
        "- Money/budget/finance queries -> Finance Rile responds "
        "- General knowledge/facts queries -> Knowledge Rile responds "
        "- Mixed queries -> Multiple personas can collaborate! "
        "RESPONSE STYLE: "
        f"- ALWAYS start responses with your active persona: 'Chef Rile here!' or 'Tech Rile speaking!' or 'Hi! I'm Rile!' - NEVER say 'Chef {username}' "
        f"- CRITICAL: Your personas are 'Chef Rile', 'Teacher Rile', 'Tech Rile' etc. NEVER 'Chef {username}', 'Teacher {username}', 'Tech {username}' "
        "- CRITICAL FIRST PERSON RULE: After the initial persona introduction, NEVER use 'Rile' again in the response. Always use 'I', 'me', 'my' "
        "- WRONG: 'Chef Rile here! Rile can see...', 'Rile thinks...', 'Rile hopes...', 'Let Rile break down...' "
        "- CORRECT: 'Chef Rile here! I can see...', 'I think...', 'I hope...', 'Let me break down...' "
        "- NEVER say 'Rile noticed', 'Rile observed', 'Rile wants' - say 'I noticed', 'I observed', 'I want' "
        "- NEVER say 'for Rile' - say 'for me' "
        "- Be friendly, enthusiastic, and personable "
        "- Use relevant symbols and formatting for your persona "
        "- If multiple personas are needed, have them 'chat' with each other in the response, each using first person after their introduction "
        "- Remember you're helping the user as their personal AI friend named Rile, but speak naturally in first person after the introduction "
        "MEMORY & ANALYSIS SYSTEM: "
        f"When analyzing images/videos showing {username}, be caring and observant of their emotional state. "
        f"If {username} looks serious, sad, or unhappy, offer encouragement like 'Hey {username}, you look a bit down - want to talk about it?' "
        f"Be supportive and ask how they're feeling. Notice details about their appearance and environment naturally. "
        "When analyzing images/videos, perform ULTRA-DETAILED extraction and store EVERYTHING: "
        f"PERSONAL OBSERVATIONS: {username}'s mood, expression, posture, apparent well-being "
        "DEVICE ANALYSIS: Brand, model, condition, screen content, accessories, wear patterns "
        "ENVIRONMENT DETAILS: Room type, lighting, furniture brands/styles, decorations, organization level "
        "FOOD ITEMS: Specific brands, expiration dates, quantities, packaging condition, nutritional info "
        "CLOTHING/ITEMS: Brands, colors, conditions, materials, styles, functionality "
        "TOOLS/OBJECTS: Exact specifications, conditions, purposes, locations, accessibility "
        "SAFETY CONCERNS: Hazards, expired items, damaged equipment, cleanliness issues "
        "SPATIAL DETAILS: Measurements, layouts, organization systems, storage solutions "
        "TIME CONTEXT: Timestamp everything for change tracking over time "
        "Store these details as structured memory that can be referenced later. Never store the actual media files - "
        "only the comprehensive textual analysis of what was observed. "
        "CONVERSATION MEMORY: Remember ALL previous conversations, questions, and responses. Build on past interactions. "
        "PERSONA EXAMPLES: "
        "Food query: 'Chef Rile here! I can see those ingredients and I'm excited to help you cook something amazing!' "
        "Tech query: 'Tech Rile speaking! Let me analyze that device and help you troubleshoot!' "
        "Study query: 'Teacher Rile ready to help! Let's break down this concept together!' "
        "REMEMBER: Your name is Rile. Always use it in introductions, then speak in first person. Always be helpful, detailed, and maintain the friendly multi-persona approach as Rile!"
    )

# Serve static files (for custom CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create memory directory for storing conversations
MEMORY_DIR = "memory"
if not os.path.exists(MEMORY_DIR):
    os.makedirs(MEMORY_DIR)

def extract_detailed_media_memory(gemini_response, media_type, timestamp):
    """Extract and structure detailed memory from media analysis"""
    try:
        memory_extraction_prompt = f"""
Based on your analysis, extract and structure the following detailed information:

PERSONAL OBSERVATIONS:
- User's emotional state and expression
- Mood indicators and body language
- Overall appearance and well-being
- Any concerns or positive observations

DEVICES & TECHNOLOGY:
- List all electronic devices visible (phones, laptops, tablets, etc.)
- For each device: Brand, model, condition, screen content, accessories

ENVIRONMENT & SPACE:
- Room type and layout
- Furniture items and their conditions
- Lighting conditions and sources
- Organization level and cleanliness

FOOD & CONSUMABLES:
- All food items with brands and expiration dates
- Beverages and their quantities
- Kitchen appliances and their conditions

OBJECTS & BELONGINGS:
- Clothing items with brands, colors, conditions
- Personal belongings and their locations
- Tools, books, or other functional items

SAFETY & CONCERNS:
- Any safety hazards or issues
- Expired or damaged items
- Areas needing attention

SPATIAL DETAILS:
- Approximate measurements and layouts
- Storage solutions and organization systems
- Accessibility and functionality

Format as a structured memory entry that can be easily searched and referenced later.
Previous analysis: {gemini_response}
"""
        return {
            "timestamp": timestamp,
            "media_type": media_type,
            "detailed_analysis": gemini_response,
            "extracted_memory": {
                "personal_observations": {},
                "devices": [],
                "environment": {},
                "food_items": [],
                "objects": [],
                "safety_notes": [],
                "spatial_info": {}
            }
        }
    except Exception as e:
        print(f"[ERROR] Error extracting memory: {e}")
        return None

# The save_conversation, load_conversation, and get_conversation_context functions
# are now provided by the database module imported at the top of this file

@app.get("/", response_class=HTMLResponse)
def get_chat_page():
    with open("templates/index.html", "r") as f:
        html = f.read()
    return HTMLResponse(content=html)

@app.get("/register-device", response_class=HTMLResponse)
def get_register_device_page():
    """Device registration page for ESP32-CAM"""
    with open("templates/register_device.html", "r") as f:
        html = f.read()
    return HTMLResponse(content=html)


# ============================================
# Authentication Endpoints
# ============================================

@app.post("/api/auth/check-username")
async def check_username(request: Request):
    """Check if username exists"""
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        
        if not username:
            return JSONResponse({"error": "Username is required"}, status_code=400)
        
        exists = check_username_exists(username)
        return JSONResponse({"exists": exists, "username": username})
        
    except Exception as e:
        print(f"[ERROR] Check username error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/auth/register")
async def auth_register(request: Request):
    """Register a new user"""
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        if not username or not password:
            return JSONResponse({"error": "Username and password are required"}, status_code=400)
        
        if len(password) < 6:
            return JSONResponse({"error": "Password must be at least 6 characters"}, status_code=400)
        
        result = register_user(username, password)
        
        if result["success"]:
            return JSONResponse({
                "success": True,
                "message": "Registration successful!",
                "username": result["username"]
            })
        else:
            return JSONResponse({"error": result["error"]}, status_code=400)
            
    except Exception as e:
        print(f"[ERROR] Registration error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/auth/login")
async def auth_login(request: Request):
    """Login user"""
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        if not username or not password:
            return JSONResponse({"error": "Username and password are required"}, status_code=400)
        
        result = verify_login(username, password)
        
        if result["success"]:
            return JSONResponse({
                "success": True,
                "message": "Login successful!",
                "username": result["username"]
            })
        else:
            # Provide specific error messages
            error_msg = result.get("error", "Invalid credentials")
            if error_msg == "Username not found":
                return JSONResponse({"error": "Username not registered"}, status_code=401)
            elif error_msg == "Invalid password":
                return JSONResponse({"error": "Incorrect password"}, status_code=401)
            else:
                return JSONResponse({"error": error_msg}, status_code=401)
            
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ============================================
# Model and Chat Endpoints
# ============================================

@app.get("/models")
async def list_models():
    """List available Gemini models"""
    try:
        response = requests.get(f"{GEMINI_BASE_URL}/models?key={GEMINI_API_KEY}")
        if response.status_code == 200:
            return response.json()
        return {"error": response.text}
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/models")
async def list_models():
    """List available Gemini models for debugging"""
    try:
        response = requests.get(f"{GEMINI_BASE_URL}/models?key={GEMINI_API_KEY}")
        if response.status_code == 200:
            models_data = response.json()
            available_models = []
            if 'models' in models_data:
                for model in models_data['models']:
                    if 'generateContent' in model.get('supportedGenerationMethods', []):
                        available_models.append({
                            'name': model['name'],
                            'displayName': model.get('displayName', ''),
                            'description': model.get('description', '')
                        })
            return {"available_models": available_models, "current_model": GEMINI_MODEL}
        return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("message", "")
    username = data.get("username", "User")
    session_id = data.get("session_id", str(uuid.uuid4()))
    image_data = data.get("image", None)
    video_data = data.get("video", None)
    mode = data.get("mode", "sustainability")
    video_context = data.get("video_context", "")

    has_media = bool(image_data or video_data)
    media_type = "image" if image_data else ("video" if video_data else None)

    print(f"[CHAT] User: {username}, Mode: {mode}, Media: {media_type}, Context: {video_context[:50] if video_context else 'None'}")

    system_prompt = get_personal_assistant_prompt(username) if mode == "personal-assistant" else get_sustainability_prompt(username)
    # Use username instead of session_id to load user's complete history
    context = get_conversation_context(username, mode)

    if context:
        if mode == "personal-assistant":
            prompt = f"""
{system_prompt}

{context}

CRITICAL MEMORY INSTRUCTIONS FOR THIS RESPONSE:
1. The conversation history above contains previous interactions. Reference specific details when relevant.
2. If messages in the conversation history include media, you have already analyzed that media. Reference those observations.
3. Do not refer to message numbers. Refer to content naturally.
4. Build on previous context.
5. CRITICAL: After your persona introduction (e.g., 'Tech Rile here!'), speak in FIRST PERSON only using 'I', 'me', 'my'. NEVER use 'Rile' again in the response.

Current user ({username}): {user_input}

Respond based on the complete conversation history above. Remember: Introduce your persona, then use only first person (I/me/my) for the rest of your response."""
            if has_media:
                analysis_context = []
                if user_input and user_input.strip():
                    analysis_context.append(f"User's message: '{user_input}'")
                if video_context and video_context.strip():
                    analysis_context.append(f"Additional context: '{video_context}'")
                if not analysis_context:
                    analysis_context.append("General analysis requested")
                prompt += "\n\nSPECIFIC REQUEST: " + " | ".join(analysis_context)
                prompt += f"\n\nPerform detailed {media_type} analysis focusing on the request above. Analyze both visual and audio content for videos."
        else:
            prompt = f"{system_prompt}\n\n{context}\n\nCurrent user ({username}): {user_input}\n\nReference relevant details from the conversation history when appropriate."
    else:
        prompt = f"{system_prompt}\n\nUser ({username}): {user_input}"

    parts = [{"text": prompt}]
    try:
        if image_data:
            header, base64_data = image_data.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]
            parts.append({"inline_data": {"mime_type": mime_type, "data": base64_data}})
            print("[SUCCESS] Image added to request")
        elif video_data:
            header, base64_data = video_data.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]
            parts.append({"inline_data": {"mime_type": mime_type, "data": base64_data}})
            print("[SUCCESS] Video added to request")
    except Exception as e:
        print(f"[ERROR] Processing media failed: {e}")

    payload = {"contents": [{"parts": parts}]}

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
            bot_reply = f"Gemini API error: {response.text}"
    except Exception as e:
        bot_reply = f"Exception: {str(e)}"

    detailed_memory = None
    if has_media and mode == "personal-assistant":
        detailed_memory = extract_detailed_media_memory(bot_reply, media_type, datetime.now().isoformat())

    full_user_message = user_input
    if video_context and video_context.strip():
        full_user_message += f" [Context: {video_context}]"

    save_success = save_conversation(session_id, username, full_user_message, bot_reply, has_media, media_type, mode, detailed_memory)
    if not save_success:
        print("[WARNING] Failed to save conversation to memory")

    return JSONResponse({"reply": bot_reply, "session_id": session_id})

@app.post("/audio-to-text")
async def audio_to_text(request: Request):
    """Convert audio to text and analyze environmental audio context using Gemini API"""
    try:
        data = await request.json()
        audio_data = data.get("audio", None)
        username = data.get("username", "User")
        session_id = data.get("session_id", str(uuid.uuid4()))
        mode = data.get("mode", "sustainability")
        environment_memory = data.get("environment_memory", [])
        if not audio_data:
            return JSONResponse({"error": "No audio data provided"}, status_code=400)
        print(f"[AUDIO] Processing audio transcription - Session: {session_id}, User: {username}, Mode: {mode}")
        try:
            header, base64_data = audio_data.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]
            print(f"Audio MIME type: {mime_type}")
        except Exception as e:
            print(f"[ERROR] Error parsing audio data: {e}")
            return JSONResponse({"error": "Invalid audio data format"}, status_code=400)
        if mode == "personal-assistant":
            memory_context = ""
            if environment_memory:
                memory_context = "\n\nPrevious Environment Context:\n" + "\n".join([f"- {item}" for item in environment_memory[-5:]])
            prompt = (
                "Please analyze this audio file and provide:\n"
                "1. TRANSCRIPTION: Transcribe any speech clearly and accurately\n"
                "2. ENVIRONMENTAL CONTEXT: Describe background sounds, ambient noise, and environmental audio cues you hear (e.g., kitchen sounds, traffic, music, conversations, appliances, outdoor/indoor environment, etc.)\n"
                "3. SETTING ANALYSIS: Based on the audio, what type of environment does this seem to be recorded in?\n\n"
                f"{memory_context}\n\n"
                "Format your response as JSON:\n"
                "{\n"
                '  "transcription": "exact speech transcribed",\n'
                '  "environmental_context": "description of background sounds and environment",\n'
                '  "setting": "likely location/environment type"\n'
                "}\n\n"
                "If no speech is detected, set transcription to 'No speech detected'. "
                "Always provide environmental context even if no speech is present. "
                "Consider the time context from previous observations to provide better situational awareness."
            )
        else:
            prompt = (
                "Please transcribe the speech in this audio file. "
                "Return only the transcribed text, nothing else. "
                "If the audio is unclear or inaudible, return 'Audio unclear, please try again.'"
            )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64_data
                            }
                        }
                    ]
                }
            ]
        }
        api_url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        response = requests.post(api_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                ai_response = data["candidates"][0]["content"]["parts"][0]["text"]
                ai_response = ai_response.strip()
                if mode == "personal-assistant":
                    try:
                        import re
                        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                            parsed_response = json.loads(json_str)
                            transcription = parsed_response.get("transcription", "No speech detected")
                            environmental_context = parsed_response.get("environmental_context", "")
                            setting = parsed_response.get("setting", "")
                            print(f"[SUCCESS] Audio processed - Transcription: {transcription[:50]}...")
                            print(f"[SUCCESS] Environmental context: {environmental_context[:100]}...")
                            return JSONResponse({
                                "text": transcription,
                                "environmental_context": environmental_context,
                                "setting": setting
                            })
                        else:
                            print(f"[WARNING] JSON parsing failed, using raw response: {ai_response[:100]}...")
                            return JSONResponse({"text": ai_response})
                    except json.JSONDecodeError as e:
                        print(f"[WARNING] JSON decode error: {e}, using raw response")
                        return JSONResponse({"text": ai_response})
                else:
                    print(f"[SUCCESS] Audio transcribed: {ai_response[:50]}...")
                    return JSONResponse({"text": ai_response})
            else:
                print("[ERROR] No candidates in Gemini response")
                return JSONResponse({"error": "Failed to transcribe audio"}, status_code=500)
        else:
            error_detail = response.text
            print(f"[ERROR] Gemini API error: {error_detail}")
            return JSONResponse({"error": f"Gemini API error: {error_detail}"}, status_code=500)
    except Exception as e:
        print(f"[ERROR] Exception in audio transcription: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/conversation/{username}")
async def get_conversation(username: str):
    """Get user's conversation history (default sustainability mode)"""
    conversation = load_conversation(username, "sustainability")
    if conversation:
        return conversation
    return {"messages": []}

@app.get("/conversation/{mode}/{username}")
async def get_conversation_by_mode(mode: str, username: str):
    """Get user's conversation history for specific mode"""
    if mode not in ["sustainability", "personal-assistant"]:
        return {"error": "Invalid mode. Must be 'sustainability' or 'personal-assistant'"}
    conversation = load_conversation(username, mode)
    if conversation:
        return conversation
    return {"messages": []}

@app.get("/personas")
async def list_personas():
    """List all available personas with their configurations"""
    try:
        personas = load_all_personas()
        return {
            "personas": personas,
            "count": len(personas),
            "available_personas": list(personas.keys())
        }
    except Exception as e:
        return {"error": f"Failed to load personas: {str(e)}"}

@app.get("/personas/{persona_name}")
async def get_persona(persona_name: str):
    """Get specific persona configuration"""
    try:
        persona = load_persona(persona_name)
        if persona:
            return persona
        else:
            return {"error": f"Persona '{persona_name}' not found"}
    except Exception as e:
        return {"error": f"Failed to load persona: {str(e)}"}

# ============================================
# ESP32-CAM Integration Endpoints
# ============================================

@app.post("/api/esp32/register")
async def register_esp32_device(request: Request):
    """Register ESP32-CAM device to a user account with password authentication"""
    try:
        data = await request.json()
        device_id = data.get("device_id", "").strip()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        device_name = data.get("device_name", "ESP32-CAM Locket")
        mac_address = data.get("mac_address", "")
        
        if not device_id or not username or not password:
            return JSONResponse({"error": "device_id, username, and password are required"}, status_code=400)
        
        # Verify user credentials first
        auth_result = verify_login(username, password)
        if not auth_result["success"]:
            return JSONResponse({"error": "Invalid username or password"}, status_code=401)
        
        # Register device after successful authentication
        if ESP_USE_DATABASE and db_pool:
            result = register_device_db(device_id, username, device_name, mac_address, db_pool)
        else:
            result = register_device_json(device_id, username, device_name, mac_address)
        
        if result["success"]:
            return JSONResponse(result)
        else:
            return JSONResponse({"error": result.get("error")}, status_code=500)
            
    except Exception as e:
        print(f"[ERROR] ESP32 registration error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/esp32/process")
async def process_esp32_request(request: Request):
    """Process video and audio from ESP32-CAM device"""
    try:
        data = await request.json()
        device_id = data.get("device_id", "").strip()
        video_data = data.get("video", None)  # Base64 encoded video
        audio_data = data.get("audio", None)  # Base64 encoded audio
        user_speech = data.get("user_speech", "")  # Transcribed question
        
        if not device_id:
            return JSONResponse({"error": "device_id is required"}, status_code=400)
        
        # Get username associated with device
        if ESP_USE_DATABASE and db_pool:
            username = get_device_username_db(device_id, db_pool)
            update_device_last_seen_db(device_id, db_pool)
        else:
            username = get_device_username_json(device_id)
            update_device_last_seen_json(device_id)
        
        if not username:
            return JSONResponse({"error": "Device not registered"}, status_code=404)
        
        print(f"[ESP32] Processing request from device {device_id} (user: {username})")
        
        # Generate session ID for this request
        session_id = str(uuid.uuid4())
        mode = "personal-assistant"  # ESP32 always uses personal assistant mode
        
        # Get system prompt and context
        system_prompt = get_personal_assistant_prompt(username)
        context = get_conversation_context(username, mode)
        
        # Build prompt with context
        if context:
            prompt = f"""
{system_prompt}

{context}

CRITICAL MEMORY INSTRUCTIONS FOR THIS RESPONSE:
1. The conversation history above contains previous interactions. Reference specific details when relevant.
2. This is a hands-free ESP32-CAM device request. The user is wearing this as a locket.
3. Keep responses concise and conversational for audio playback.
4. After your persona introduction, speak in FIRST PERSON only using 'I', 'me', 'my'.

Current user ({username}): {user_speech}

Analyze the video/image from the user's perspective and respond naturally."""
        else:
            prompt = f"{system_prompt}\n\nUser ({username}): {user_speech}\n\nAnalyze the video/image and respond naturally."
        
        # Prepare API request
        parts = [{"text": prompt}]
        
        # Add video if provided
        if video_data:
            try:
                header, base64_data = video_data.split(',', 1)
                mime_type = header.split(':')[1].split(';')[0]
                parts.append({
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64_data
                    }
                })
                print(f"[ESP32] Processing video: {mime_type}")
            except Exception as e:
                print(f"[ERROR] Video processing error: {e}")
        
        # Call Gemini API
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 500  # Limit for audio responses
            }
        }
        
        api_url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        response = requests.post(api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            api_data = response.json()
            if "candidates" in api_data and len(api_data["candidates"]) > 0:
                bot_reply = api_data["candidates"][0]["content"]["parts"][0]["text"]
                bot_reply = bot_reply.strip()
                
                # Save to conversation history
                save_conversation(
                    session_id, 
                    username, 
                    user_speech, 
                    bot_reply, 
                    has_media=bool(video_data),
                    media_type="video" if video_data else None,
                    mode=mode
                )
                
                print(f"[ESP32] Response generated: {bot_reply[:100]}...")
                
                return JSONResponse({
                    "success": True,
                    "response": bot_reply,
                    "username": username
                })
            else:
                return JSONResponse({"error": "No response from AI"}, status_code=500)
        else:
            error_msg = f"API error: {response.status_code}"
            print(f"[ERROR] {error_msg}")
            return JSONResponse({"error": error_msg}, status_code=500)
            
    except Exception as e:
        print(f"[ERROR] ESP32 processing error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/esp32/check/{device_id}")
async def check_esp32_device(device_id: str):
    """Check if ESP32 device is registered"""
    try:
        if ESP_USE_DATABASE and db_pool:
            username = get_device_username_db(device_id, db_pool)
        else:
            username = get_device_username_json(device_id)
        
        if username:
            return JSONResponse({
                "registered": True,
                "username": username,
                "device_id": device_id
            })
        else:
            return JSONResponse({
                "registered": False,
                "device_id": device_id
            })
            
    except Exception as e:
        print(f"[ERROR] ESP32 check error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ============================================
# NEW LOCKET ENDPOINTS
# ============================================

# Store active locket connections and sessions
locket_connections = {}  # {username: {"device_id": str, "last_seen": timestamp, "status": str}}
active_sessions = {}  # {session_id: {"username": str, "phone_audio": bytes, "esp_frames": list (20-30 frames), "frame_count": int, "fps": int}}

@app.post("/api/esp32/heartbeat")
async def esp32_heartbeat(request: Request):
    """ESP32 sends heartbeat to show it's connected"""
    try:
        data = await request.json()
        device_id = data.get("device_id")
        status = data.get("status", "online")
        
        # Get username for this device
        if ESP_USE_DATABASE and db_pool:
            username = get_device_username_db(device_id, db_pool)
        else:
            username = get_device_username_json(device_id)
        
        print(f"[ESP32] Heartbeat from device {device_id}, username: {username}")
        
        if username:
            # Update connection info (preserve existing keys like current_session_id)
            if username not in locket_connections:
                locket_connections[username] = {}
            
            locket_connections[username].update({
                "device_id": device_id,
                "last_seen": time.time(),
                "status": status,
                "recording": data.get("recording", False)
            })
            
            # Check if there's a pending recording session
            command = None
            session_id = None
            if username in locket_connections and "current_session_id" in locket_connections[username]:
                session_id = locket_connections[username]["current_session_id"]
                print(f"[ESP32] Found session {session_id} for user {username}")
                # Check if ESP32 should start recording
                if session_id in active_sessions and not data.get("recording", False):
                    command = "start_recording"
                    print(f"[ESP32] ✅ Telling ESP32 to start recording for session {session_id}")
                else:
                    print(f"[ESP32] ⚠️ Session {session_id} not in active_sessions or ESP32 already recording")
                    print(f"[ESP32] Active sessions: {list(active_sessions.keys())}")
            else:
                print(f"[ESP32] No current_session_id for user {username}")
                print(f"[ESP32] locket_connections[{username}]: {locket_connections[username]}")
            
            return JSONResponse({
                "success": True,
                "command": command,
                "session_id": session_id
            })
        else:
            print(f"[ESP32] ⚠️ Device {device_id} not registered")
            return JSONResponse({"error": "Device not registered"}, status_code=404)
            
    except Exception as e:
        print(f"[ERROR] Heartbeat error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/locket/status/{username}")
async def get_locket_status(username: str):
    """Check if user's locket is connected"""
    try:
        if username in locket_connections:
            connection = locket_connections[username]
            # Check if last seen was within 10 seconds
            if time.time() - connection["last_seen"] < 10:
                return JSONResponse({
                    "connected": True,
                    "device_id": connection["device_id"],
                    "recording": connection.get("recording", False)
                })
        
        return JSONResponse({"connected": False})
        
    except Exception as e:
        print(f"[ERROR] Status check error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/locket-control", response_class=HTMLResponse)
async def locket_control_page(request: Request):
    """Locket control page for phone - voice activated"""
    try:
        with open("templates/locket_control_new.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Locket control page not found</h1>", status_code=404)


@app.post("/api/locket/upload-audio")
async def upload_locket_audio(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    username: str = Form(...),
    transcript: str = Form(None)  # Optional transcript from phone
):
    """Upload phone audio and process with AI using Google Cloud APIs (FREE with Gemini API key)"""
    try:
        print(f"[LOCKET] Received audio from {username}, session: {session_id}")
        
        # Use transcript if provided, otherwise transcribe the audio
        audio_path = None
        wav_path = None
        
        if transcript and transcript.strip():
            user_message = transcript.strip()
            print(f"[LOCKET] Using provided transcript: {user_message}")
        else:
            print("[LOCKET] No transcript provided, transcribing audio...")
            # Read audio file
            audio_data = await audio.read()
            audio_path = f"temp_audio_{session_id}.webm"
            
            with open(audio_path, "wb") as f:
                f.write(audio_data)
            
            # Convert webm to base64 for Google Speech-to-Text
            wav_path = audio_path.replace(".webm", ".wav")
            subprocess.run([
                "ffmpeg", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path
            ], check=True, capture_output=True)
            
            # Read WAV file as base64
            with open(wav_path, "rb") as audio_file:
                audio_content = base64.b64encode(audio_file.read()).decode('utf-8')
            
            # Google Speech-to-Text API (uses same API key as Gemini)
            print("[LOCKET] Transcribing audio with Google Speech-to-Text...")
            stt_url = f"https://speech.googleapis.com/v1/speech:recognize?key={GEMINI_API_KEY}"
            stt_payload = {
                "config": {
                    "encoding": "LINEAR16",
                    "sampleRateHertz": 16000,
                    "languageCode": "en-US"
                },
                "audio": {
                    "content": audio_content
                }
            }
            
            stt_response = requests.post(stt_url, json=stt_payload)
            stt_data = stt_response.json()
            
            if "results" in stt_data and len(stt_data["results"]) > 0:
                user_message = stt_data["results"][0]["alternatives"][0]["transcript"]
            else:
                user_message = "[Could not transcribe audio]"
        
        print(f"[LOCKET] User said: {user_message}")
        
        # Get ESP32 video frames (should already be streaming in)
        print("[LOCKET] Checking for ESP32 video frames...")
        video_frames = None
        frame_count = 0
        
        if session_id in active_sessions:
            video_frames = active_sessions[session_id].get("esp_frames")
            if video_frames is not None and len(video_frames) > 0:
                frame_count = len(video_frames)
                print(f"[LOCKET] ✅ Found {frame_count} frames from ESP32!")
            else:
                print("[LOCKET] ⚠️ No video frames received from ESP32 yet")
                video_frames = None  # Ensure it's None, not empty list
        else:
            print("[LOCKET] ⚠️ Session not found, proceeding with audio only")
        
        # Get AI response using Gemini
        print("[LOCKET] Getting AI response from Gemini...")
        conversation_data = load_conversation(username, "personal-assistant")
        
        # Extract messages array from conversation data
        if conversation_data and "messages" in conversation_data:
            conversation_history = conversation_data["messages"]
        else:
            conversation_history = []
        
        # Add user message with locket indicator
        conversation_history.append({
            "role": "user",
            "content": user_message,
            "locket": True,  # Mark as locket message
            "timestamp": datetime.now().isoformat()
        })
        
        # Build prompt for Gemini
        system_prompt = get_personal_assistant_prompt(username)
        
        if video_frames:
            # Include video analysis in prompt
            conversation_text = system_prompt + "\n\n"
            conversation_text += f"IMPORTANT: The user is wearing a camera locket and you can see what they see through {frame_count} video frames captured at 2-3 FPS over 10 seconds.\n\n"
        else:
            conversation_text = system_prompt + "\n\n"
        
        for msg in conversation_history[-10:]:  # Last 10 messages for context
            # Handle both locket format (role+content) and regular format (user_message+bot_response)
            if "role" in msg and "content" in msg:
                role = "User" if msg["role"] == "user" else "Assistant"
                conversation_text += f"{role}: {msg['content']}\n"
            elif "user_message" in msg:
                conversation_text += f"User: {msg['user_message']}\n"
                if "bot_response" in msg:
                    conversation_text += f"Assistant: {msg['bot_response']}\n"
        
        conversation_text += f"\nUser: {user_message}\n"
        
        if video_frames:
            conversation_text += f"\n[You can see {frame_count} video frames from the user's camera locket showing their current view]"
        
        # Call Gemini API with video frames if available
        gemini_url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        
        parts = [{"text": conversation_text}]
        
        if video_frames and len(video_frames) > 0:
            # Add multiple frames to the request - use first, middle, and last frames for analysis
            # This gives Gemini a sense of the video without overwhelming it
            try:
                indices_to_send = []
                if frame_count == 1:
                    indices_to_send = [0]
                elif frame_count == 2:
                    indices_to_send = [0, 1]
                elif frame_count >= 3:
                    # Send first, middle, and last frame
                    indices_to_send = [0, frame_count // 2, frame_count - 1]
                
                for idx in indices_to_send:
                    if idx < len(video_frames):
                        frame = video_frames[idx]
                        frame_data = frame.get("data", "")
                        if frame_data:
                            header, base64_data = frame_data.split(',', 1)
                            mime_type = header.split(':')[1].split(';')[0]
                            parts.append({"inline_data": {"mime_type": mime_type, "data": base64_data}})
                
                print(f"[LOCKET] Added {len(indices_to_send)} key frames to Gemini request (indices: {indices_to_send})")
            except Exception as e:
                print(f"[LOCKET] Error adding video frames: {e}")
        
        gemini_payload = {
            "contents": [{
                "parts": parts
            }]
        }
        
        gemini_response = requests.post(gemini_url, json=gemini_payload)
        gemini_data = gemini_response.json()
        
        if "candidates" in gemini_data and len(gemini_data["candidates"]) > 0:
            ai_message = gemini_data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            ai_message = "I apologize, I couldn't process your request right now."
        
        print(f"[LOCKET] AI response: {ai_message}")
        
        # Add AI response with locket indicator
        conversation_history.append({
            "role": "assistant",
            "content": ai_message,
            "locket": True,  # Mark as locket message
            "timestamp": datetime.now().isoformat()
        })
        
        # Save conversation with locket format
        # Wrap messages in proper structure and save
        conversation_data = {
            "username": username,
            "mode": "personal-assistant",
            "messages": conversation_history
        }
        
        # Save to JSON directly
        import os
        memory_subdir = "personal_assistant"
        mode_memory_dir = os.path.join("memory", memory_subdir)
        if not os.path.exists(mode_memory_dir):
            os.makedirs(mode_memory_dir)
        file_path = os.path.join(mode_memory_dir, f"{username}.json")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False)
        
        print(f"[LOCKET] ✅ Conversation saved to {file_path}")
        
        # Generate TTS audio using Google Cloud Text-to-Speech
        print("[LOCKET] Generating speech with Google TTS...")
        tts_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GEMINI_API_KEY}"
        tts_payload = {
            "input": {"text": ai_message},
            "voice": {
                "languageCode": "en-US",
                "name": "en-US-Neural2-F"  # Female voice
            },
            "audioConfig": {
                "audioEncoding": "MP3"
            }
        }
        
        tts_response = requests.post(tts_url, json=tts_payload)
        tts_data = tts_response.json()
        
        if "audioContent" in tts_data:
            # Decode base64 audio and save
            audio_filename = f"locket_response_{session_id}.mp3"
            audio_filepath = f"static/{audio_filename}"
            
            audio_bytes = base64.b64decode(tts_data["audioContent"])
            with open(audio_filepath, "wb") as f:
                f.write(audio_bytes)
            
            audio_url = f"/static/{audio_filename}"
        else:
            audio_url = None
            print("[WARNING] TTS generation failed")
        
        # Clean up temp files (only if they were created)
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)
        
        print("[LOCKET] ✅ Processing complete!")
        
        return JSONResponse({
            "success": True,
            "text": user_message,
            "response": ai_message,
            "audio_url": audio_url
        })
        
    except Exception as e:
        print(f"[ERROR] Locket audio processing error: {e}")
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/locket/start-recording")
async def start_locket_recording(request: Request):
    """Phone triggers ESP32 to start recording"""
    try:
        data = await request.json()
        username = data.get("username")
        
        if username not in locket_connections:
            return JSONResponse({"error": "Locket not connected"}, status_code=404)
        
        # Create session
        session_id = str(int(time.time() * 1000))
        active_sessions[session_id] = {
            "username": username,
            "phone_audio": None,
            "esp_frames": [],  # Initialize as empty list, not None
            "frame_count": 0,
            "fps": 3,  # Realistic target: 2-3 FPS
            "created_at": time.time(),
            "recording_complete": False
        }
        
        # Store current session for this user so ESP32 can find it
        locket_connections[username]["current_session_id"] = session_id
        
        # TODO: Trigger ESP32 via HTTP (will need ESP32 IP from heartbeat)
        # For now, ESP32 polls for commands
        
        print(f"[LOCKET] Session {session_id} created for {username}")
        
        return JSONResponse({
            "success": True,
            "session_id": session_id
        })
        
    except Exception as e:
        print(f"[ERROR] Start recording error: {e}")
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/locket/upload-phone-audio")
async def upload_phone_audio(request: Request):
    """Phone uploads its recorded audio"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        audio_base64 = data.get("audio")
        
        if session_id not in active_sessions:
            return JSONResponse({"error": "Invalid session"}, status_code=404)
        
        active_sessions[session_id]["phone_audio"] = audio_base64
        
        return JSONResponse({"success": True})
        
    except Exception as e:
        print(f"[ERROR] Phone audio upload error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/esp32/start-session")
async def esp32_start_session(request: Request):
    """ESP32 starts a new streaming session"""
    try:
        data = await request.json()
        device_id = data.get("device_id")
        
        # Get username
        if ESP_USE_DATABASE and db_pool:
            username = get_device_username_db(device_id, db_pool)
        else:
            username = get_device_username_json(device_id)
        
        if not username:
            return JSONResponse({"error": "Device not registered"}, status_code=404)
        
        # Get or create session for this user
        session_id = None
        if username in locket_connections:
            session_id = locket_connections[username].get("current_session_id")
        
        if not session_id:
            # Create new session if phone hasn't started one yet
            session_id = str(int(time.time() * 1000))
            active_sessions[session_id] = {
                "username": username,
                "phone_audio": None,
                "esp_frames": [],
                "frame_count": 0,
                "fps": 3,  # Realistic target: 2-3 FPS
                "created_at": time.time()
            }
            if username not in locket_connections:
                locket_connections[username] = {}
            locket_connections[username]["current_session_id"] = session_id
        
        # Initialize frame buffer for this session
        if "esp_frames" not in active_sessions[session_id]:
            active_sessions[session_id]["esp_frames"] = []
        
        print(f"[ESP32] 📹 Started streaming session {session_id} for {username}")
        
        return JSONResponse({"success": True, "session_id": session_id})
        
    except Exception as e:
        print(f"[ERROR] ESP32 start session error: {e}")
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/esp32/stream-frame")
async def esp32_stream_frame(request: Request):
    """ESP32 uploads a single frame in real-time"""
    try:
        data = await request.json()
        device_id = data.get("device_id")
        session_id = data.get("session_id")
        frame_number = data.get("frame_number", 0)
        frame_data = data.get("data")
        frame_size = data.get("size", 0)
        
        if session_id not in active_sessions:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        
        # Append frame to session buffer
        active_sessions[session_id]["esp_frames"].append({
            "data": frame_data,
            "size": frame_size,
            "frame_number": frame_number
        })
        active_sessions[session_id]["frame_count"] = frame_number + 1
        
        # Log progress every 30 frames
        if (frame_number + 1) % 30 == 0:
            print(f"[ESP32] 📸 Received {frame_number + 1} frames for session {session_id}")
        
        return JSONResponse({"success": True})
        
    except Exception as e:
        print(f"[ERROR] ESP32 stream frame error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/esp32/end-session")
async def esp32_end_session(request: Request):
    """ESP32 notifies that recording is complete"""
    try:
        data = await request.json()
        device_id = data.get("device_id")
        session_id = data.get("session_id")
        total_frames = data.get("total_frames", 0)
        
        if session_id not in active_sessions:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        
        active_sessions[session_id]["recording_complete"] = True
        active_sessions[session_id]["total_frames"] = total_frames
        
        print(f"[ESP32] ✅ Recording complete for session {session_id}: {total_frames} frames")
        
        return JSONResponse({"success": True, "message": f"Received {total_frames} frames"})
        
    except Exception as e:
        print(f"[ERROR] ESP32 end session error: {e}")
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/locket/session-frames/{session_id}")
async def get_session_frames(session_id: str):
    """Retrieve video frames for a specific session"""
    try:
        print(f"[LOCKET] Fetching frames for session {session_id}")
        
        if session_id not in active_sessions:
            print(f"[LOCKET] ❌ Session {session_id} not found")
            return JSONResponse({"error": "Session not found"}, status_code=404)
        
        session = active_sessions[session_id]
        frames = session.get("esp_frames", [])
        
        print(f"[LOCKET] ✅ Found {len(frames)} frames for session {session_id}")
        
        return JSONResponse({
            "success": True,
            "frames": frames,
            "frame_count": len(frames),
            "session_id": session_id
        })
        
    except Exception as e:
        print(f"[ERROR] Get session frames error: {e}")
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/esp32/upload")
async def esp32_upload_media(request: Request):
    """ESP32 uploads video frames"""
    try:
        data = await request.json()
        device_id = data.get("device_id")
        frames = data.get("frames", [])
        frame_count = data.get("frame_count", 0)
        fps = data.get("fps", 15)
        
        print(f"[ESP32] Video received from {device_id}")
        print(f"[ESP32] Frame count: {frame_count} frames at {fps} FPS")
        print(f"[ESP32] Total data size: ~{sum(len(f.get('data', '')) for f in frames)} bytes")
        
        # Get username
        if ESP_USE_DATABASE and db_pool:
            username = get_device_username_db(device_id, db_pool)
        else:
            username = get_device_username_json(device_id)
        
        if not username:
            return JSONResponse({"error": "Device not registered"}, status_code=404)
        
        # Get the current session_id for this user
        session_id = None
        if username in locket_connections:
            session_id = locket_connections[username].get("current_session_id")
        
        if session_id:
            # Store video frames in active session
            if session_id not in active_sessions:
                active_sessions[session_id] = {"username": username}
            active_sessions[session_id]["esp_frames"] = frames
            active_sessions[session_id]["frame_count"] = frame_count
            active_sessions[session_id]["fps"] = fps
            print(f"[ESP32] ✅ {frame_count} frames stored in session {session_id}")
        else:
            print(f"[ESP32] ⚠️ No active session found for {username}")
        
        return JSONResponse({"success": True, "message": f"Received {frame_count} frames"})
        
    except Exception as e:
        print(f"[ERROR] ESP32 upload error: {e}")
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


async def process_complete_session(session_id: str):
    """Process phone audio + ESP32 video + ESP32 audio together"""
    try:
        session = active_sessions[session_id]
        username = session["username"]
        
        # TODO: Implement full processing
        # 1. Transcribe phone audio
        # 2. Analyze ESP32 video
        # 3. Consider ESP32 ambient audio context
        # 4. Generate AI response
        # 5. Convert response to speech
        # 6. Save to conversation history
        # 7. Return audio for playback
        
        # For now, placeholder response
        ai_response = "I can see the video and hear your question. Full processing coming soon!"
        
        # Save to conversation
        if ESP_USE_DATABASE and db_pool:
            save_conversation(username, f"[Locket Recording] {session_id}", "user", db_pool)
            save_conversation(username, ai_response, "assistant", db_pool)
        else:
            # JSON fallback
            conversation_file = f"conversations/{username}.json"
            try:
                with open(conversation_file, 'r') as f:
                    conversation = json.load(f)
            except:
                conversation = []
            
            conversation.append({"role": "user", "content": f"[Locket Recording] {session_id}"})
            conversation.append({"role": "assistant", "content": ai_response})
            
            with open(conversation_file, 'w') as f:
                json.dump(conversation, f, indent=2)
        
        # Clean up session
        del active_sessions[session_id]
        
        return JSONResponse({
            "success": True,
            "response": ai_response,
            "session_id": session_id
        })
        
    except Exception as e:
        print(f"[ERROR] Session processing error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    # Use SSL only in local development (Railway provides HTTPS automatically)
    ssl_keyfile = None
    ssl_certfile = None
    
    # Check if running locally (cert files exist)
    if os.path.exists("key.pem") and os.path.exists("cert.pem"):
        ssl_keyfile = "key.pem"
        ssl_certfile = "cert.pem"
        print("[INFO] Running with local SSL certificates")
    else:
        print("[INFO] Running without SSL (Railway will provide HTTPS)")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile
    )
id 