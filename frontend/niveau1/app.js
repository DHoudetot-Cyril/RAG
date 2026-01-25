// Chat application for niveau1-usagers
const chatContainer = document.getElementById('chatContainer');
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');

const USER_LEVEL = 1;

// Add message to chat
function addMessage(content, type) {
    // Remove welcome message if present
    const welcome = document.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = content;
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return messageDiv;
}

// Create typing indicator
function createTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant typing';
    messageDiv.innerHTML = '<span class="cursor"></span>';
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return messageDiv;
}

// Handle form submission
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const query = userInput.value.trim();
    if (!query) return;

    // Disable input
    userInput.disabled = true;
    sendBtn.disabled = true;

    // Add user message
    addMessage(query, 'user');
    userInput.value = '';

    // Create typing indicator
    const typingDiv = createTypingIndicator();

    try {
        // Send request to API with SSE
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                level: USER_LEVEL,
                stream: true
            })
        });

        if (!response.ok) {
            throw new Error('Erreur de connexion');
        }

        // Handle SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';

        // Replace typing indicator with response
        typingDiv.classList.remove('typing');
        typingDiv.innerHTML = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.token) {
                            fullResponse += data.token;
                            typingDiv.textContent = fullResponse;
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    } catch (e) {
                        // Ignore parse errors
                    }
                }
            }
        }

    } catch (error) {
        typingDiv.textContent = "Désolé, une erreur s'est produite. Veuillez réessayer.";
        console.error('Error:', error);
    }

    // Re-enable input
    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.focus();
});
