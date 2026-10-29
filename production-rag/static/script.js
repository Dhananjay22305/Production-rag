// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const queryInput = document.getElementById('queryInput');
const sendButton = document.getElementById('sendButton');
const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const documentList = document.getElementById('documentList');
const docCount = document.getElementById('docCount');

// State
let chatHistory = [];
let activeDocuments = [];

// Event Listeners
sendButton.addEventListener('click', handleSendMessage);
queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
    }
});

// Drag and drop setup
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.add('border-indigo-500', 'bg-indigo-950/20'), false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.remove('border-indigo-500', 'bg-indigo-950/20'), false);
});

dropZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
        fileInput.files = files;
        handleFileUpload(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (fileInput.files.length > 0) {
        handleFileUpload(fileInput.files[0]);
    }
});

// Initial health & doc check on load
async function checkBackendHealth() {
    try {
        const res = await fetch('/api/v1/health');
        if (res.ok) {
            const data = await res.json();
            if (data.active_documents) {
                activeDocuments = data.active_documents;
                renderDocumentList();
            }
        }
    } catch (err) {
        console.error('Health check failed:', err);
    }
}
checkBackendHealth();

// Chat Handler
async function handleSendMessage() {
    const query = queryInput.value.trim();
    if (!query) return;

    // Append user message
    appendMessage(query, 'user');
    queryInput.value = '';
    
    // Push to history
    chatHistory.push({ role: 'user', content: query });

    // Create AI response placeholder
    const aiMsgDiv = appendMessage('', 'ai', true);
    const msgBody = aiMsgDiv.querySelector('.message-body');
    const sourcesContainer = aiMsgDiv.querySelector('.sources-container');

    try {
        const response = await fetch('/api/v1/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: query,
                top_k: 3,
                history: chatHistory
            })
        });

        if (!response.ok) throw new Error(`Backend returned ${response.status} ${response.statusText} for /api/v1/chat`);

        msgBody.textContent = '';
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            fullResponse += chunk;
            msgBody.textContent = fullResponse;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        // Push assistant response to history
        chatHistory.push({ role: 'assistant', content: fullResponse });

        // Fetch retrieval preview chunks
        fetchRetrievedChunksForQuery(query, sourcesContainer);

    } catch (error) {
        console.error('Chat request failed:', error);
        msgBody.textContent = `Error: ${error.message}`;
    }
}

// Fetch and render context chunks used for answering
async function fetchRetrievedChunksForQuery(query, container) {
    try {
        const res = await fetch(`/api/v1/retrieval-preview?question=${encodeURIComponent(query)}&top_k=3`);
        if (!res.ok) return;
        const data = await res.json();
        
        if (data.retrieved_chunks && data.retrieved_chunks.length > 0) {
            container.innerHTML = '<div class="text-xs font-semibold text-slate-400 mb-1 mt-3">Retrieved Context Sources:</div>';
            data.retrieved_chunks.forEach((chunk, index) => {
                const badge = document.createElement('div');
                badge.className = 'text-[11px] bg-slate-800/80 border border-slate-700/60 rounded p-2 mb-1 text-slate-300 font-mono';
                badge.innerHTML = `<span class="text-indigo-400 font-bold">[${index+1}] ${chunk.doc_name}</span> (score: ${chunk.score || 'N/A'}): <span class="text-slate-400">${escapeHtml(chunk.text.substring(0, 120))}...</span>`;
                container.appendChild(badge);
            });
        }
    } catch (err) {
        console.error('Failed to fetch retrieval preview:', err);
    }
}

// File Upload Handler
async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);

    const uploadStatus = document.getElementById('uploadStatus') || createUploadStatusBanner();
    uploadStatus.className = "mt-4 p-3 rounded-lg bg-slate-900 border border-indigo-500/30 text-sm text-indigo-300 flex items-center justify-between";
    uploadStatus.innerHTML = `<span>Uploading & indexing <b>${file.name}</b>...</span><i class="fa-solid fa-spinner animate-spin"></i>`;

    try {
        const response = await fetch('/api/v1/ingest?strategy=sentence_aware', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            let detail = `${response.status} ${response.statusText}`;
            try { detail = (await response.json()).detail || detail; } catch (_) {}
            throw new Error(detail);
        }

        const result = await response.json();
        
        uploadStatus.className = "mt-4 p-3 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-sm text-emerald-300 flex items-center justify-between";
        uploadStatus.innerHTML = `<span>Successfully indexed <b>${result.filename}</b> (${result.chunks_count} chunks)!</span><i class="fa-solid fa-check"></i>`;

        if (result.active_documents) {
            activeDocuments = result.active_documents;
            renderDocumentList();
        }
    } catch (err) {
        console.error('Ingest failed:', err);
        uploadStatus.className = "mt-4 p-3 rounded-lg bg-red-950/30 border border-red-500/30 text-sm text-red-300 flex items-center justify-between";
        uploadStatus.innerHTML = `<span>Error ingesting file: ${err.message}</span><i class="fa-solid fa-triangle-exclamation"></i>`;
    }
}

// UI Helpers
function appendMessage(text, sender, isStreamingPlaceholder = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `flex ${sender === 'user' ? 'justify-end' : 'justify-start'} mb-4`;

    const innerDiv = document.createElement('div');
    innerDiv.className = `max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
        sender === 'user' 
            ? 'bg-indigo-600 text-white rounded-br-none' 
            : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none shadow-lg'
    }`;

    const bodyDiv = document.createElement('div');
    bodyDiv.className = 'message-body whitespace-pre-wrap leading-relaxed';
    bodyDiv.textContent = text;
    innerDiv.appendChild(bodyDiv);

    if (sender === 'ai') {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'sources-container mt-2';
        innerDiv.appendChild(sourcesDiv);
    }

    messageDiv.appendChild(innerDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageDiv;
}

function createUploadStatusBanner() {
    const banner = document.createElement('div');
    banner.id = 'uploadStatus';
    dropZone.parentNode.appendChild(banner);
    return banner;
}

function renderDocumentList() {
    if (!documentList) return;
    documentList.innerHTML = '';
    docCount.textContent = activeDocuments.length;

    if (activeDocuments.length === 0) {
        documentList.innerHTML = '<div class="text-xs text-slate-500 italic">No documents indexed yet.</div>';
        return;
    }

    activeDocuments.forEach(docName => {
        const item = document.createElement('div');
        item.className = 'flex items-center justify-between bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 mb-1.5';
        item.innerHTML = `<span class="truncate max-w-[200px]"><i class="fa-solid fa-file-pdf text-red-400 mr-2"></i>${docName}</span><span class="text-emerald-400 font-mono">Active</span>`;
        documentList.appendChild(item);
    });
}

function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}