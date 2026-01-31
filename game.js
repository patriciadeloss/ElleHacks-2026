// Game state
let gameState = {
    budget: 1000,
    happiness: 50,
    day: 0
};

// Drag and drop cat
const cat = document.getElementById('cat');
const buildings = document.querySelectorAll('.building');

// Make cat draggable
cat.addEventListener('dragstart', (e) => {
    e.dataTransfer.setData('text/plain', 'cat');
});

// Make buildings droppable
buildings.forEach(building => {
    building.addEventListener('dragover', (e) => {
        e.preventDefault();
        building.style.background = '#bee3f8';
    });
    
    building.addEventListener('dragleave', () => {
        building.style.background = '';
    });
    
    building.addEventListener('drop', async (e) => {
        e.preventDefault();
        building.style.background = '';
        
        const buildingType = building.getAttribute('data-building');
        const prompt = `The mayor visits the ${buildingType}. Create a short, fun description about what they find there.`;
        
        // Get AI response
        const response = await fetch(`/api/gemini?prompt=${encodeURIComponent(prompt)}`);
        const data = await response.json();
        
        document.getElementById('ai-message').textContent = data.response;
    });
});

// Generate AI scenario
async function generateScenario() {
    const scenarios = [
        "Create a fun scenario about buying pizza for school kids",
        "Create a decision about fixing a roof with consequences",
        "Create an opportunity cost scenario between fixing a playground or finding a lost dog"
    ];
    
    const randomScenario = scenarios[Math.floor(Math.random() * scenarios.length)];
    
    const response = await fetch(`/api/gemini?prompt=${encodeURIComponent(randomScenario)}`);
    const data = await response.json();
    
    document.getElementById('scenario').textContent = data.response;
}

// Text to speech
async function speakText() {
    const text = document.getElementById('ai-message').textContent;
    
    try {
        const response = await fetch('/api/speak', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: text})
        });
        const data = await response.json();
        
        if (data.audio_url) {
            // Play the audio file
            const audio = new Audio(data.audio_url);
            audio.play();
            console.log("Playing voice:", data.text);
        } else {
            // Fallback to browser speech
            speakWithBrowser(text);
        }
    } catch (error) {
        console.error("Voice error:", error);
        speakWithBrowser(text);
    }
}

// Predictive typing
async function getPredictions() {
    const input = document.getElementById('user-input').value;
    
    if (input.length > 0) {
        const response = await fetch(`/api/predict?text=${encodeURIComponent(input)}`);
        const data = await response.json();
        
        const predictionsDiv = document.getElementById('predictions');
        predictionsDiv.innerHTML = '';
        
        data.predictions.forEach(prediction => {
            const button = document.createElement('button');
            button.textContent = prediction;
            button.onclick = () => {
                document.getElementById('user-input').value = prediction;
                predictionsDiv.innerHTML = '';
            };
            predictionsDiv.appendChild(button);
        });
    }
}

// Make game decision
async function makeDecision(type, cost, happiness) {
    const response = await fetch('/api/game/decision', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            type: type,
            cost: cost,
            happiness: happiness
        })
    });
    
    const data = await response.json();
    
    // Update UI
    gameState = data.state;
    document.getElementById('budget').textContent = `$${gameState.budget}`;
    document.getElementById('happiness').textContent = gameState.happiness;
    document.getElementById('day').textContent = gameState.day;
    
    // Get next scenario
    await generateScenario();
}

// Send message (for typing)
async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value;
    
    if (message.trim()) {
        const response = await fetch(`/api/gemini?prompt=${encodeURIComponent(message)}`);
        const data = await response.json();
        
        document.getElementById('ai-message').textContent = data.response;
        input.value = '';
        document.getElementById('predictions').innerHTML = '';
    }
}

// Initialize
async function initGame() {
    const response = await fetch('/api/game/state');
    const data = await response.json();
    gameState = data;
    
    // Update initial display
    document.getElementById('budget').textContent = `$${gameState.budget}`;
    document.getElementById('happiness').textContent = gameState.happiness;
    document.getElementById('day').textContent = gameState.day;
}

// Start the game
window.onload = initGame;