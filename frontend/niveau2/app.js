// Chat application for niveau2-direction
const chatContainer = document.getElementById('chatContainer');
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const sourcesPanel = document.getElementById('sourcesPanel');
const sourcesList = document.getElementById('sourcesList');
const toggleSourcesBtn = document.getElementById('toggleSources');
const copyBtn = document.getElementById('copyBtn');
const exportBtn = document.getElementById('exportBtn');

const USER_LEVEL = 2;
let lastResponse = '';
let currentSources = [];

// Toggle sources panel
toggleSourcesBtn.addEventListener('click', () => {
    sourcesPanel.classList.toggle('hidden');
    toggleSourcesBtn.classList.toggle('active');
});

// Copy last response
copyBtn.addEventListener('click', () => {
    if (lastResponse) {
        navigator.clipboard.writeText(lastResponse);
        copyBtn.style.color = '#4ade80';
        setTimeout(() => copyBtn.style.color = '', 1000);
    }
});

// Export conversation
exportBtn.addEventListener('click', () => {
    const messages = document.querySelectorAll('.message');
    let content = '# Conversation IG2I\n\n';

    messages.forEach(msg => {
        const type = msg.classList.contains('user') ? 'Vous' : 'Assistant';
        content += `**${type}:** ${msg.textContent}\n\n`;
    });

    if (currentSources.length > 0) {
        content += '## Sources\n\n';
        currentSources.forEach((src, i) => {
            content += `${i + 1}. ${src.source} (p.${src.page})\n`;
        });
    }

    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-ig2i-${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
});

// Add message to chat
function addMessage(content, type) {
    const welcome = document.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.innerHTML = content;
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

// Update sources panel
function updateSources(sources) {
    currentSources = sources;

    if (sources.length === 0) {
        sourcesList.innerHTML = '<p class="no-sources">Aucune source trouvée</p>';
        return;
    }

    sourcesList.innerHTML = sources.map((src, i) => `
        <div class="source-card" data-index="${i}">
            <div class="source-name">[${i + 1}] ${src.source}</div>
            <div class="source-meta">
                Page ${src.page}
                <span class="source-score">${(src.score * 100).toFixed(0)}%</span>
            </div>
        </div>
    `).join('');
}

// Format response with citations
function formatWithCitations(text) {
    // Convert [1], [2] etc to clickable citations
    return text.replace(/\[(\d+)\]/g, '<span class="citation" data-ref="$1">$1</span>');
}

// Handle form submission
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const query = userInput.value.trim();
    if (!query) return;

    userInput.disabled = true;
    sendBtn.disabled = true;

    addMessage(query, 'user');
    userInput.value = '';

    const typingDiv = createTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                level: USER_LEVEL,
                stream: true
            })
        });

        if (!response.ok) throw new Error('Erreur de connexion');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';

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
                            typingDiv.innerHTML = formatWithCitations(fullResponse);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                        if (data.sources) {
                            updateSources(data.sources);
                        }
                    } catch (e) { }
                }
            }
        }

        lastResponse = fullResponse;

    } catch (error) {
        typingDiv.textContent = "Désolé, une erreur s'est produite. Veuillez réessayer.";
        console.error('Error:', error);
    }

    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.focus();
});

// Citation click handler
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('citation')) {
        const ref = parseInt(e.target.dataset.ref) - 1;
        const sourceCard = document.querySelector(`.source-card[data-index="${ref}"]`);
        if (sourceCard) {
            sourceCard.scrollIntoView({ behavior: 'smooth' });
            sourceCard.style.background = 'var(--accent)';
            setTimeout(() => sourceCard.style.background = '', 1000);
        }
    }
});
