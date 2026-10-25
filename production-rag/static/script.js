// Tab Switching Logic
const navBtns = document.querySelectorAll('.nav-btn');
const tabContents = document.querySelectorAll('.tab-content');

navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        navBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(t => t.classList.remove('active'));
        
        btn.classList.add('active');
        const targetTab = document.getElementById(btn.dataset.tab);
        targetTab.classList.add('active');
    });
});

// Chat State & History Tracking
let chatHistory = [];
let sessionList = [{ id: Date.now(), title: "Current Session", history: [] }];
let activeSessionIndex = 0;
let activeUploadedFiles = [];

const sendBtn = document.getElementById('send-btn');
const userQueryInput = document.getElementById('user-query');
const chatBox = document.getElementById('chat-box');
const newChatBtn = document.getElementById('new-chat-btn');
const historyListContainer = document.getElementById('history-list');

// Initialize Sidebar on Load
updateHistorySidebar();

// New Chat Handler
newChatBtn.addEventListener('click', () => {
    // Save current active session state
    sessionList[activeSessionIndex].history = [...chatHistory];

    // Create a new session and set it active
    const newSession = {
        id: Date.now(),
        title: `Session ${sessionList.length + 1}`,
        history: []
    };
    sessionList.push(newSession);
    activeSessionIndex = sessionList.length - 1;
    chatHistory = [];

    renderActiveChatSession();
    updateHistorySidebar();
});

function updateHistorySidebar() {
    historyListContainer.innerHTML = '';
    sessionList.forEach((session, idx) => {
        const item = document.createElement('div');
        item.classList.add('history-item');
        if (idx === activeSessionIndex) item.classList.add('active');
        item.textContent = session.title;

        // Click listener to load previous/selected chat
        item.addEventListener('click', () => {
            if (activeSessionIndex === idx) return;

            // Sync active state before switching
            sessionList[activeSessionIndex].history = [...chatHistory];
            
            // Switch session pointer
            activeSessionIndex = idx;
            chatHistory = [...sessionList[activeSessionIndex].history];

            renderActiveChatSession();
            updateHistorySidebar();
        });

        historyListContainer.appendChild(item);
    });
}

function renderActiveChatSession() {
    chatBox.innerHTML = '';

    if (chatHistory.length === 0) {
        chatBox.innerHTML = `
            <div class="message ai-message">
                <div class="msg-icon"><i class="fa-solid fa-robot"></i></div>
                <div class="msg-body">Started a new session. Ask me anything about your ingested documents!</div>
            </div>
        `;
        return;
    }

    // Re-render conversation history for loaded session
    chatHistory.forEach(msg => {
        const msgDiv = appendMessage(msg.content, msg.role === 'user' ? 'user' : 'ai');
        
        // If user message, fetch citations attached to that question
        if (msg.role === 'user') {
            fetchRetrievedChunksForQuery(msg.content, msgDiv);
        }
    });
}

async function handleSendMessage() {
    const query = userQueryInput.value.trim();
    if (!query) return;

    // Auto-update session title based on first query
    if (chatHistory.length === 0) {
        sessionList[activeSessionIndex].title = query.length > 25 ? query.substring(0, 25) + '...' : query;
        updateHistorySidebar();
    }

    appendMessage(query, 'user');
    chatHistory.push({ role: 'user', content: query });
    sessionList[activeSessionIndex].history = [...chatHistory];
    userQueryInput.value = '';

    const aiMsgDiv = appendMessage('Thinking...', 'ai');
    const msgBody = aiMsgDiv.querySelector('.msg-body');

    try {
        const response = await fetch('/api/v1/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                question: query, 
                top_k: 3, 
                history: chatHistory.slice(0, -1) 
            })
        });

        if (!response.ok) throw new Error('Failed to fetch response from backend');

        msgBody.textContent = '';
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullAssistantResponse = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            fullAssistantResponse += chunk;
            msgBody.textContent += chunk;
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        chatHistory.push({ role: 'assistant', content: fullAssistantResponse });
        sessionList[activeSessionIndex].history = [...chatHistory];

        // Fetch retrieval preview to attach interactive citation badges
        fetchRetrievedChunksForQuery(query, aiMsgDiv);

    } catch (error) {
        msgBody.textContent = 'Error: Could not connect to local RAG backend or generate response.';
    }
}

async function fetchRetrievedChunksForQuery(query, aiMsgDiv) {
    try {
        const res = await fetch(`/api/v1/retrieval-preview?question=${encodeURIComponent(query)}&top_k=3`);
        if (!res.ok) return;
        const data = await res.json();
        
        if (data.retrieved_chunks && data.retrieved_chunks.length > 0) {
            const citationsDiv = document.createElement('div');
            citationsDiv.classList.add('citations-container');

            data.retrieved_chunks.forEach((chunk) => {
                const pill = document.createElement('button');
                pill.classList.add('citation-pill');
                pill.innerHTML = `<i class="fa-solid fa-file-pdf"></i> ${chunk.doc_name} (Pg ${chunk.page_number})`;
                
                pill.addEventListener('click', () => {
                    openDrawerWithChunk(chunk);
                });
                citationsDiv.appendChild(pill);
            });

            aiMsgDiv.appendChild(citationsDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    } catch (err) {
        console.error("Failed to fetch retrieval preview", err);
    }
}

function openDrawerWithChunk(chunk) {
    const drawer = document.getElementById('citation-drawer');
    const drawerContent = document.getElementById('drawer-content');
    
    drawerContent.innerHTML = `
        <div class="chunk-card">
            <div class="chunk-meta">Source: ${chunk.doc_name} | Page: ${chunk.page_number} | Chunk ID: ${chunk.chunk_id}</div>
            <p>${chunk.text}</p>
        </div>
    `;
    drawer.classList.remove('hidden');
}

document.getElementById('close-drawer').addEventListener('click', () => {
    document.getElementById('citation-drawer').classList.add('hidden');
});

function appendMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'ai-message');
    
    const iconDiv = document.createElement('div');
    iconDiv.classList.add('msg-icon');
    iconDiv.innerHTML = sender === 'user' ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';
    
    const bodyDiv = document.createElement('div');
    bodyDiv.classList.add('msg-body');
    bodyDiv.textContent = text;
    
    messageDiv.appendChild(iconDiv);
    messageDiv.appendChild(bodyDiv);
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    
    return messageDiv;
}

sendBtn.addEventListener('click', handleSendMessage);
userQueryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
    }
});

// File Ingestion Handler
const fileInput = document.getElementById('file-input');
const uploadStatus = document.getElementById('upload-status');
const statusText = document.getElementById('status-text');
const uploadedFilesList = document.getElementById('uploaded-files-list');

fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    uploadStatus.classList.remove('hidden');
    const icon = uploadStatus.querySelector('i');
    icon.className = "fa-solid fa-spinner fa-spin";
    icon.style.color = "";
    statusText.textContent = `Uploading & parsing ${file.name}...`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/v1/ingest?strategy=sentence_aware', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Ingestion failed');

        const result = await response.json();
        
        icon.className = "fa-solid fa-check";
        icon.style.color = "#22c55e";
        statusText.textContent = `Successfully indexed ${result.filename}! Total Active Documents: ${result.total_documents_count}`;

        // Update active files array from backend registry
        activeUploadedFiles = result.active_documents;
        
        // Clear and re-render all active document chips side-by-side
        uploadedFilesList.innerHTML = '';
        activeUploadedFiles.forEach(docName => {
            const chip = document.createElement('div');
            chip.classList.add('doc-chip');
            chip.innerHTML = `<i class="fa-solid fa-file-pdf"></i> ${docName}`;
            uploadedFilesList.appendChild(chip);
        });

    } catch (err) {
        icon.className = "fa-solid fa-triangle-exclamation";
        icon.style.color = "#ef4444";
        statusText.textContent = `Error ingesting file. Ensure backend is running.`;
    }
});