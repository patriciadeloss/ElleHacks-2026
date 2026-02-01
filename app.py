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
import random
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Town Economy Game", version="1.0")

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
        print("✅ Gemini API initialized successfully")
    except Exception as e:
        print(f"❌ Gemini initialization error: {e}")
        genai_client = None
else:
    genai_client = None
    print("⚠️ Gemini API key not found. Running in mock mode.")

# Initialize ElevenLabs
eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
if eleven_api_key:
    eleven_client = ElevenLabs(api_key=eleven_api_key)
    print("✅ ElevenLabs API initialized successfully")
else:
    eleven_client = None
    print("⚠️ ElevenLabs API key not found. Running in mock mode.")

# Game state with your specific buildings - FIXED: Added library and fixed building names
game_state = {
    "budget": 1000,
    "happiness": 50,
    "day": 0,
    "scenario_day": 1,
    "town_state": {
        "townhall": {"status": "needs_repair", "window_broken": True},
        "pizza": {"status": "ready_for_party", "pizza_needed": True},  # Changed from pizza_area to pizza
        "townhouse": {"status": "new_families_moving_in", "families_count": 3},
        "library": {"status": "window_broken", "needs_fix": True},  # Added library
        "playground": {"status": "needs_upgrade", "equipment_broken": True}
    },
    "decisions": [],
    "previous_choices": {},
    "game_phase": "introduction"  # introduction, exploration, day1, day2, day3, final
}

# People database for exploration - matching your buildings
town_people = [
    {"name": "Town Clerk", "building": "townhall", "description": "Keeps town records"},
    {"name": "Assistant", "building": "townhall", "description": "Helps the Mayor"},
    {"name": "Pizza Chef", "building": "pizza", "description": "Makes delicious pizza"},
    {"name": "Hungry Student", "building": "pizza", "description": "Loves pizza parties"},
    {"name": "New Family", "building": "townhouse", "description": "Just moved in"},
    {"name": "Friendly Neighbor", "building": "townhouse", "description": "Welcomes everyone"},
    {"name": "Playful Child", "building": "playground", "description": "Loves to play"},
    {"name": "Park Helper", "building": "playground", "description": "Keeps playground safe"},
    {"name": "Librarian", "building": "library", "description": "Loves books"},
    {"name": "Bookworm", "building": "library", "description": "Reads all day"}
]

# Homepage
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

# Gemini API endpoint - Enhanced with dynamic scenarios
@app.get("/api/gemini/scenario")
async def get_gemini_scenario(
    phase: str = None,
    building: str = None,
    person: str = None,
    previous_decision: str = None
):
    try:
        # If no specific phase provided, use current game phase
        if not phase:
            phase = game_state["game_phase"]
        
        # Generate dynamic numbers for scenarios
        pizza_slices_needed = random.randint(40, 60)
        pizza_price_a = round(random.uniform(1.5, 2.0), 2)  # Kid-friendly prices
        pizza_price_b = round(random.uniform(1.0, 1.5), 2)
        roof_cost_quality = random.randint(600, 800)
        roof_cost_cheap = random.randint(200, 350)
        playground_upgrade_cost = random.randint(300, 500)
        townhouse_welcome_cost = random.randint(150, 250)
        
        # Build creative prompts for Gemini with kid-friendly language
        if phase == "introduction":
            prompt = f"""Welcome Mayor! I'm your cat guide and I will help you lead a town with 1,000 people.
            You have ${game_state['budget']} to spend.
            People are {game_state['happiness']}% happy.
            Let's get on this mission!"""

        elif phase == "day1":
            prompt = f"""The townhall is hosting a pizza party! {pizza_slices_needed} kids want pizza.
            Pizza Place A: ${pizza_price_a} per slice. Best pizza, but pricier!
            Pizza Place B: ${pizza_price_b} per slice. Only 30 slices available.
            Cat gives a hint to think about money and happiness.
            Prompt Mayor to pick a choice.
            Keep it short!"""

        elif phase == "day2":
            # Randomly select which building has broken window
            broken_building = random.choice(["library", "townhouse", "school"])
            
            prompt = f"""Oh no! {broken_building} has a broken window!
            Cold air is coming in. Rain might get in.
            Two fixes: Good fix costs ${roof_cost_quality}. Will last years, but more expensive.
            Quick fix costs ${roof_cost_cheap}. Might break again, but cost cheaper.
            Prompt Mayor to pick a choice.
            Keep it short!"""

        elif phase == "day3":
            prompt = f"""Two important things need money.
            Playground upgrade costs ${playground_upgrade_cost}. Kids want new swings.
            Helping old grandma to find her lost dog cost ${townhouse_welcome_cost}. 
            Budget only for one.
            Prompt Mayor to pick a choice.
            Pick playground or grandma?
            Keep it short!"""

        elif phase == "final":
            prompt = f"""Week is done! Time to celebrate.
            Budget: ${game_state['budget']}. Happiness: {game_state['happiness']}%.
            First ending: you have a lot of money to build a museum, but you get kicked off as mayor because of low happiness.
            Second ending: you have no money and can't build a museum, but your town people are happy and you get to stay as mayor. Work harder next time!
            Third ending: you have both money and happiness! You can build a new museum, and stays as mayor. 
            Based on the budget and happiniess, give an ending to the mayor. 
            Keep it short!"""

        # Update the instruction
        prompt += "\n\nWrite for kids 7-12. Short sentences, with a total of 4-5 sentences. Mayor is player. Cat helps. Town has people. Keep it simple!"

        # Use Gemini if available, otherwise use mock responses
        if genai_client:
            try:
                response = genai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[{"text": prompt}]
                )
                ai_text = response.text
            except Exception as gemini_error:
                print(f"Gemini API error: {gemini_error}")
                # Try with 2.0-flash if 2.5 fails
                try:
                    response = genai_client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[{"text": prompt}]
                    )
                    ai_text = response.text
                except Exception as e2:
                    print(f"Second Gemini attempt failed: {e2}")
                    ai_text = generate_kid_friendly_mock_response(phase, pizza_slices_needed, pizza_price_a, pizza_price_b, 
                                                                roof_cost_quality, roof_cost_cheap, playground_upgrade_cost, 
                                                                townhouse_welcome_cost)
        else:
            ai_text = generate_kid_friendly_mock_response(phase, pizza_slices_needed, pizza_price_a, pizza_price_b, 
                                                        roof_cost_quality, roof_cost_cheap, playground_upgrade_cost, 
                                                        townhouse_welcome_cost)
            
        # Store scenario data for frontend
        scenario_data = {
            "response": ai_text,
            "phase": phase,
            "dynamic_data": {
                "pizza_slices_needed": pizza_slices_needed,
                "pizza_price_a": pizza_price_a,
                "pizza_price_b": pizza_price_b,
                "roof_cost_quality": roof_cost_quality,
                "roof_cost_cheap": roof_cost_cheap,
                "playground_upgrade_cost": playground_upgrade_cost,
                "townhouse_welcome_cost": townhouse_welcome_cost
            },
            "options": get_kid_friendly_options_for_phase(phase, pizza_slices_needed, pizza_price_a, pizza_price_b, 
                                                        roof_cost_quality, roof_cost_cheap, playground_upgrade_cost, 
                                                        townhouse_welcome_cost)
        }
        
        return scenario_data
        
    except Exception as e:
        print(f"❌ Scenario generation error: {e}")
        return {
            "response": "Hi Mayor! Ready for some fun decisions? Let's make our town awesome! Today we have important choices to make. Remember to think about what's best for everyone. Your decisions help people feel happy and safe. Let's start our adventure!",
            "phase": "error",
            "dynamic_data": {},
            "options": []
        }

def generate_kid_friendly_mock_response(phase, pizza_slices_needed, pizza_price_a, pizza_price_b, 
                                      roof_cost_quality, roof_cost_cheap, playground_upgrade_cost, 
                                      townhouse_welcome_cost):
    """Generate VERY short mock responses"""
    
    responses_by_phase = {
        "introduction": [
            "Welcome Mayor! Your cat will guide you. You have $1000. People are 50% happy. Visit five places. Make good choices!",
            "Hi Mayor! Cat is here to help. Lead our town. Spend money wisely. Make people happy. Let's go!"
        ],
        
        "exploration": [
            f"Mayor visits {random.choice(['townhouse', 'townhall', 'pizza', 'library', 'playground'])}. Cat comes too. People say hi. Something needs fixing.",
            f"Exploring with cat. At the {random.choice(['townhouse', 'townhall', 'pizza', 'library', 'playground'])}. See people. Hear sounds. Cat points."
        ],
        
        "day1": [
            f"Pizza party! {pizza_slices_needed} hungry kids. Place A: ${pizza_price_a}. Place B: ${pizza_price_b}. Choose! Cat waits.",
            f"Pizza time! Need {pizza_slices_needed} slices. One place costs more. One has fewer slices. Decide! Cat watches."
        ],
        
        "day2": [
            f"Broken window! Good fix: ${roof_cost_quality}. Quick fix: ${roof_cost_cheap}. Choose! Cat meows advice.",
            f"Window broke! Fix it well or fix it cheap? Cat says think ahead. Pick one!"
        ],
        
        "day3": [
            f"Playground needs ${playground_upgrade_cost}. Families need ${townhouse_welcome_cost}. Pick one! Cat waits.",
            f"Two needs. One budget. Playground or families? Cat watches you choose."
        ],
        
        "final": [
            f"Week done! Party: $300. Or save. Budget: ${game_state['budget']}. Happiness: {game_state['happiness']}%. Choose! Cat purrs.",
            f"Time to decide! Party costs $300. Or save money. What's best? Cat trusts you."
        ]
    }
    
    responses = responses_by_phase.get(phase, ["Welcome Mayor! Let's explore town. Cat will help you. Make good choices!"])
    return random.choice(responses)

def get_kid_friendly_options_for_phase(phase, pizza_slices_needed, pizza_price_a, pizza_price_b, 
                                     roof_cost_quality, roof_cost_cheap, playground_upgrade_cost, 
                                     townhouse_welcome_cost):
    """Generate kid-friendly decision options"""
    if phase == "day1":
        cost_all_a = pizza_slices_needed * pizza_price_a
        cost_mix = (30 * pizza_price_b) + ((pizza_slices_needed - 30) * pizza_price_a)
        
        return [
            {"id": "pizza_all_a", "label": f"All from Pizza Place A (${cost_all_a:.2f})", 
             "cost": cost_all_a, "happiness": 20},
            {"id": "pizza_mix", "label": f"Mix from both places (${cost_mix:.2f})", 
             "cost": cost_mix, "happiness": 15},
            {"id": "pizza_less", "label": f"Buy less pizza (save ${150})", 
             "cost": 150, "happiness": -10}
        ]
    elif phase == "day2":
        return [
            {"id": "window_quality", "label": f"Good fix (${roof_cost_quality})",  # Changed from roof_quality to window_quality
             "cost": roof_cost_quality, "happiness": 15},
            {"id": "window_cheap", "label": f"Quick fix (${roof_cost_cheap})",  # Changed from roof_cheap to window_cheap
             "cost": roof_cost_cheap, "happiness": 5}
        ]
    elif phase == "day3":
        return [
            {"id": "upgrade_playground", "label": f"Upgrade playground (${playground_upgrade_cost})", 
             "cost": playground_upgrade_cost, "happiness": 25},
            {"id": "welcome_families", "label": f"Welcome new families (${townhouse_welcome_cost})", 
             "cost": townhouse_welcome_cost, "happiness": 20}
        ]
    elif phase == "final":
        party_cost = 300
        return [
            {"id": "big_party", "label": f"Throw big party! (${party_cost})", 
             "cost": party_cost, "happiness": 30},
            {"id": "save_money", "label": "Save money for future", 
             "cost": 0, "happiness": -15}
        ]
    return []

# ElevenLabs endpoint
@app.post("/api/speak")
async def text_to_speech(request: dict):
    try:
        text_content = request.get('text', '')
        if not text_content:
            return {"error": "No text provided"}
        
        if not eleven_client:
            return {
                "audio_url": "/static/audio/mock.mp3", 
                "text": text_content,
                "status": "mock_mode"
            }
        
        print(f"🔊 Generating speech: '{text_content[:50]}...'")
        
        try:
            audio = eleven_client.text_to_speech.convert(
                text=text_content,
                voice_id="pNInz6obpgDQGcFmaJgB",
                model_id="eleven_multilingual_v2",
                voice_settings={
                    "stability": 0.71,
                    "similarity_boost": 0.5,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            )
        except Exception as inner_e:
            print(f"⚠️ Trying alternative: {inner_e}")
            audio = eleven_client.generate(
                text=text_content,
                voice="Rachel",  # Kid-friendly voice
                model="eleven_monolingual_v1"
            )
        
        with NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            for chunk in audio:
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        with open(temp_file_path, "rb") as f:
            audio_content = f.read()
        
        os.unlink(temp_file_path)
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        return {
            "audio_url": f"data:audio/mp3;base64,{audio_base64}",
            "text": text_content,
            "status": "success"
        }
        
    except Exception as e:
        print(f"❌ Speech error: {e}")
        return {
            "audio_url": "/static/audio/mock.mp3", 
            "text": text_content if 'text_content' in locals() else str(request),
            "status": "error"
        }

# Game endpoints
@app.get("/api/game/state")
async def get_game_state():
    return game_state

@app.get("/api/game/people")
async def get_town_people():
    return {"people": town_people}

@app.post("/api/game/decision")
async def make_decision(decision: dict):
    decision_id = decision.get("id")
    phase = decision.get("phase", game_state["game_phase"])
    
    # Get cost and happiness from options (simplified for kids)
    cost = 0
    happiness_change = 0
    
    if decision_id == "pizza_all_a":
        cost = 120
        happiness_change = 20
    elif decision_id == "pizza_mix":
        cost = 100
        happiness_change = 15
    elif decision_id == "pizza_less":
        cost = 80
        happiness_change = -10
    elif decision_id == "window_quality":  # Changed from roof_quality
        cost = 700
        happiness_change = 15
    elif decision_id == "window_cheap":  # Changed from roof_cheap
        cost = 300
        happiness_change = 5
    elif decision_id == "upgrade_playground":
        cost = 400
        happiness_change = 25
    elif decision_id == "welcome_families":
        cost = 200
        happiness_change = 20
    elif decision_id == "big_party":
        cost = 300
        happiness_change = 30
    elif decision_id == "save_money":
        cost = 0
        happiness_change = -15
    
    # Apply decision
    game_state["budget"] -= cost
    game_state["happiness"] += happiness_change
    if happiness_change > 0:  # Don't let it go negative
        game_state["day"] += 1
    
    # Record decision
    game_state["decisions"].append({
        "day": game_state["day"],
        "decision": decision_id,
        "cost": cost,
        "happiness_change": happiness_change,
        "timestamp": datetime.now().isoformat()
    })
    
    # Update game phase
    if phase == "day1":
        game_state["game_phase"] = "day2"
    elif phase == "day2":
        game_state["game_phase"] = "day3"
    elif phase == "day3":
        game_state["game_phase"] = "final"
    elif phase == "final":
        # Check ending - kid friendly outcomes
        if game_state["budget"] > 400 and game_state["happiness"] > 70:
            game_state["ending"] = "Super Star Mayor!"
        elif game_state["happiness"] > 75:
            game_state["ending"] = "Most Loved Mayor!"
        elif game_state["budget"] > 600:
            game_state["ending"] = "Money Smart Mayor!"
        else:
            game_state["ending"] = "Good Try Mayor!"
        game_state["game_phase"] = "completed"
    
    return {"message": "Great choice!", "state": game_state}

@app.post("/api/game/explore")
async def explore_building(exploration: dict):
    building = exploration.get("building")
    person = exploration.get("person")
    
    # Update game phase to exploration if not already in a day scenario
    if game_state["game_phase"] not in ["day1", "day2", "day3", "final", "completed"]:
        game_state["game_phase"] = "exploration"
    
    return {
        "message": f"Visiting {building} is fun!" + (f" Met {person}!" if person else ""),
        "building": building,
        "person": person
    }

# Reset game endpoint
@app.post("/api/game/reset")
async def reset_game():
    global game_state
    game_state = {
        "budget": 1000,
        "happiness": 50,
        "day": 0,
        "scenario_day": 1,
        "town_state": {
            "townhall": {"status": "needs_repair", "window_broken": True},
            "pizza": {"status": "ready_for_party", "pizza_needed": True},  # Changed from pizza_area
            "townhouse": {"status": "new_families_moving_in", "families_count": 3},
            "library": {"status": "window_broken", "needs_fix": True},  # Added library
            "playground": {"status": "needs_upgrade", "equipment_broken": True}
        },
        "decisions": [],
        "previous_choices": {},
        "game_phase": "introduction"
    }
    return {"message": "New game started! Have fun!", "state": game_state}

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="localhost", port=8000, reload=True)
