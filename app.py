from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import google.genai as genai
from elevenlabs import ElevenLabs, Voice, VoiceSettings
import os
import json
from dotenv import load_dotenv
import asyncio
from tempfile import NamedTemporaryFile
import base64
#from presage import Presage

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Town Economy Game", version="1.0")

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure APIs
genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# Initialize ElevenLabs client using API key from .env
eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
if eleven_api_key:
    eleven_client = ElevenLabs(api_key=eleven_api_key)
    print("✅ ElevenLabs API initialized successfully")
else:
    eleven_client = None
    print("⚠️ ElevenLabs API key not found. Running in mock mode.")

# Initialize Presage (predictive typing)
#presage = Presage()

# Game state
game_state = {
    "budget": 1000,
    "happiness": 50,
    "day": 0,
    "town_state": {
        "school": "needs_pizza",
        "city_hall": "needs_repair",
        "park": "damaged",
        "dog": "lost"
    }
}

# Homepage
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

# Gemini API endpoint
# Mock Gemini API endpoint (for testing)
@app.get("/api/gemini")
async def get_gemini_response(prompt: str = "Create a welcome message for a town mayor"):
    try:
        # Dictionary of responses based on prompt keywords
        prompt_lower = prompt.lower()
        
        if "pizza" in prompt_lower:
            response = "🍕 PIZZA PARTY DECISION: School needs pizza for 67 kids. Shop A: $2 per slice. Shop B: $1.50 per slice. Which will you choose, Mayor?"
        elif "roof" in prompt_lower or "repair" in prompt_lower:
            response = "🏛️ ROOF REPAIR DECISION: City Hall's roof is leaking! Option A: $1000 for permanent fix. Option B: $400 for temporary patch (might fail later). What's your choice?"
        elif "playground" in prompt_lower or "dog" in prompt_lower:
            response = "🌳 PLAYGROUND vs DOG DECISION: After the storm, choose: Fix playground OR find lost dog? Opportunity cost: you can't do both!"
        elif "welcome" in prompt_lower:
            response = "🎉 Welcome Mayor! Our town has 1,000 citizens and a budget of $1000. Your decisions will shape our future! Drag the cat to explore buildings."
        elif "museum" in prompt_lower:
            response = "🏛️ MUSEUM DECISION: Build a museum to celebrate our history! Costs $800 but increases happiness by 40 points. Will you invest?"
        else:
            response = f"🤖 AI RESPONSE TO: '{prompt[:50]}...' - As Mayor, consider both budget and happiness in your decision."
        
        return {"response": response}
    except Exception as e:
        return {"response": "Welcome to the town! Let's make wise decisions together."}

# ElevenLabs endpoint
# Mock ElevenLabs endpoint
# ElevenLabs endpoint
@app.post("/api/speak")
async def text_to_speech(request: dict):
    try:
        # Get text from request body
        text_content = request.get('text', '')
        if not text_content:
            return {"error": "No text provided"}
        
        # Check if we have ElevenLabs API key
        if not eleven_client:
            # Fall back to mock mode if no API key
            return {
                "audio_url": "/static/audio/mock.mp3", 
                "text": text_content,
                "status": "mock_mode",
                "message": "ElevenLabs API key not configured. Using mock voice."
            }
        
        # Generate audio using ElevenLabs API
        print(f"🔊 Generating speech for: '{text_content[:50]}...'")
        
        # CORRECTED: Use the correct parameters for the convert method
        try:
            # First, try the correct method signature
            audio = eleven_client.text_to_speech.convert(
                text=text_content,
                voice_id="pNInz6obpgDQGcFmaJgB",  # Adam voice - pass as voice_id parameter
                model_id="eleven_multilingual_v2",
                voice_settings={
                    "stability": 0.71,
                    "similarity_boost": 0.5,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            )
        except Exception as inner_e:
            # If that fails, try alternative parameter format
            print(f"⚠️ First approach failed: {inner_e}")
            print("🔄 Trying alternative approach...")
            
            # Alternative approach using generate method
            audio = eleven_client.generate(
                text=text_content,
                voice="Adam",  # Use voice name instead of ID
                model="eleven_monolingual_v1"
            )
        
        # Save audio to a temporary file
        with NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            for chunk in audio:
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        # Read the file content
        with open(temp_file_path, "rb") as f:
            audio_content = f.read()
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        # Convert to base64 for easy frontend consumption
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        return {
            "audio_url": f"data:audio/mp3;base64,{audio_base64}",
            "text": text_content,
            "status": "success",
            "message": "Voice generated successfully"
        }
        
    except Exception as e:
        print(f"❌ Error generating speech: {e}")
        # Fall back to mock mode on error
        return {
            "audio_url": "/static/audio/mock.mp3", 
            "text": text_content if 'text_content' in locals() else str(request),
            "status": "error",
            "message": f"Failed to generate voice: {str(e)}"
        }
    
# Presage predictive typing
@app.get("/api/predict")
async def get_predictions(text: str):
    try:
        # predictions = presage.predict(text)
        # return {"predictions": predictions}
        return {"predictions": []}  # Placeholder
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Game endpoints
@app.get("/api/game/state")
async def get_game_state():
    return game_state

@app.post("/api/game/decision")
async def make_decision(decision: dict):
    # Update game state based on decision
    if decision.get("type") == "buy_pizza":
        game_state["budget"] -= decision.get("cost", 0)
        game_state["happiness"] += decision.get("happiness", 0)
        game_state["day"] += 1
    
    return {"message": "Decision made", "state": game_state}

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="localhost", port=8000, reload=True)