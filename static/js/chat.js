/**
 * chat.js - Frontend chat functionality for DeepSeek AI Chat Application.
 *
 * Handles user interactions, API communication, markdown rendering, and UI updates.
 */

// --- Global State ---
let abortController = null; // To allow cancellation of in-progress requests
let currentConversationId = null; // Tracks active conversation ID
let isProcessing = false; // Prevents duplicate submissions
let messageHistory = []; // Stores message objects for current conversation

// --- DOM Element References ---
const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const newChatButton = document.getElementById('new-chat-button');
const conversationList = document.getElementById('conversation-list');
const conversationTitle = document.getElementById('conversation-title');
const statusIndicator = document.getElementById('status-indicator');

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    // Load conversations from server
    loadConversations();
    // Focus input on page load
    messageInput.focus();
    // Add event listeners
    messageInput.addEventListener('keydown', handleEnterKey);
    sendButton.addEventListener('click', sendMessage);
    newChatButton.addEventListener('click', startNewConversation);
});

// --- Helper: Escape special characters for XSS prevention ---
function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

// --- Helper: Safely render markdown using marked.js (if available) ---
function renderMarkdown(text) {
    if (typeof marked !== 'undefined') {
        // Configure marked to avoid dangerous HTML
        const renderer = new marked.Renderer();
        renderer.link = function(href, title, text) {
            // Ensure links open in new tab and have rel="noopener"
            const titleAttr = title ? ` title="${escapeHtml(title)}"` : '';
            return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer"${titleAttr}>${escapeHtml(text)}</a>`;
        };
        marked.setOptions({
            renderer: renderer,
            sanitize: true, // Deprecated but works for basic safety
            breaks: true,
            gfm: true
        });
        return marked.parse(text);
    }
    // Fallback: simple HTML with basic formatting (newlines → <br>)
    return `<p>${escapeHtml(text).replace(/\n/g, '<br>')}</p>`;
}

// --- Helper: Scroll chat to bottom ---
function scrollToBottom() {
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// --- Helper: Show error message in chat ---
function showErrorMessage(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message error-message';
    errorDiv.innerHTML = `<span class="error-icon">⚠️</span> ${escapeHtml(message)}`;
    chatContainer.appendChild(errorDiv);
    scrollToBottom();
}

// --- Helper: Update connection status ---
function updateStatus(isOnline) {
    if (statusIndicator) {
        statusIndicator.textContent = isOnline ? 'Online' : 'Offline';
        statusIndicator.className = isOnline ? 'status-online' : 'status-offline';
    }
}

// --- Load conversations from server ---
function loadConversations() {
    fetch('/api/conversations')
        .then(response => {
            if (!response.ok) throw new Error('Failed to load conversations');
            return response.json();
        })
        .then(data => {
            if (data.success && data.conversations) {
                renderConversationList(data.conversations);
                // If there's a current conversation, keep it selected
                if (currentConversationId) {
                    // Highlight in list
                    const selected = conversationList.querySelector(`[data-id="${currentConversationId}"]`);
                    if (selected) selected.classList.add('active');
                }
            } else {
                showErrorMessage('Could not load conversations.');
            }
        })
        .catch(error => {
            console.error('Error loading conversations:', error);
            updateStatus(false);
        });
}

// --- Render conversation list in sidebar ---
function renderConversationList(conversations) {
    if (!conversationList) return;
    conversationList.innerHTML = '';
    conversations.forEach(conv => {
        const li = document.createElement('li');
        li.dataset.id = conv.id;
        li.className = 'conversation-item';
        if (conv.id === currentConversationId) li.classList.add('active');
        li.innerHTML = `<span class="conv-title">${escapeHtml(conv.title || 'New Chat')}</span>
                        <button class="delete-conv" data-id="${conv.id}" title="Delete conversation">&times;</button>`;
        li.addEventListener('click', () => {
            openConversation(conv.id);
        });
        // Delete button event
        li.querySelector('.delete-conv').addEventListener('click', (e) => {
            e.stopPropagation();
            deleteConversation(conv.id);
        });
        conversationList.appendChild(li);
    });
}

// --- Delete a conversation ---
function deleteConversation(convId) {
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    fetch(`/api/conversations/${convId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to delete');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            if (currentConversationId === convId) {
                startNewConversation(); // Reset UI if deleted current
            } else {
                loadConversations(); // Refresh list
            }
        } else {
            showErrorMessage('Failed to delete conversation.');
        }
    })
    .catch(error => {
        console.error('Error deleting conversation:', error);
        showErrorMessage('Network error while deleting.');
    });
}

// --- Open an existing conversation ---
function openConversation(convId) {
    if (isProcessing) return; // Don't switch while sending
    currentConversationId = convId;
    // Update active state in sidebar
    document.querySelectorAll('.conversation-item').forEach(el => el.classList.remove('active'));
    const activeItem = conversationList.querySelector(`[data-id="${convId}"]`);
    if (activeItem) activeItem.classList.add('active');
    // Load messages for this conversation
    fetch(`/api/conversations/${convId}/messages`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load messages');
            return response.json();
        })
        .then(data => {
            if (data.success && data.messages) {
                messageHistory = data.messages;
                renderMessages(data.messages);
            } else {
                showErrorMessage('Could not load messages.');
            }
        })
        .catch(error => {
            console.error('Error loading messages:', error);
            showErrorMessage('Network error while loading conversation.');
        });
}

// --- Start a new conversation ---
function startNewConversation() {
    if (isProcessing) return;
    // Clear current conversation state
    currentConversationId = null;
    messageHistory = [];
    // Clear chat display
    renderMessages([]);
    // Reset title
    if (conversationTitle) conversationTitle.textContent = 'New Chat';
    // Remove active state from all conversation items
    document.querySelectorAll('.conversation-item').forEach(el => el.classList.remove('active'));
    // Focus input
    messageInput.focus();
    // Optionally create a new conversation on server (lazy creation when first message sent)
}

// --- Add a message to the chat display ---
function renderMessages(messages) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    chatMessages.innerHTML = '';
    messages.forEach(msg => {
        appendMessageToDisplay(msg.role, msg.content, msg.timestamp);
    });
    scrollToBottom();
}

// --- Append a single message to the display ---
function appendMessageToDisplay(role, content, timestamp) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    
    // Avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.textContent = role === 'user' ? '👤' : '🤖';
    
    // Message body
    const bodyDiv = document.createElement('div');
    bodyDiv.className = 'message-body';
    bodyDiv.innerHTML = renderMarkdown(content);
    
    // Timestamp
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-timestamp';
    if (timestamp) {
        const date = new Date(timestamp);
        timeDiv.textContent = date.toLocaleTimeString();
    }
    
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(bodyDiv);
    messageDiv.appendChild(timeDiv);
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// --- Send message to server (with streaming support) ---
function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isProcessing) return;
    isProcessing = true;
    sendButton.disabled = true;
    messageInput.disabled = true;
    
    // Add user message to display immediately
    appendMessageToDisplay('user', text);
    messageInput.value = '';
    
    // Prepare the assistant message placeholder
    const assistantMessageDiv = createAssistantMessagePlaceholder();
    const assistantBody = assistantMessageDiv.querySelector('.message-body');
    
    // Build request payload
    const payload = {
        message: text,
        conversation_id: currentConversationId || null
    };
    
    // Create abort controller for cancellation
    abortController = new AbortController();
    
    // Send request to server
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: abortController.signal
    })
    .then(async response => {
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }
        // Check if response is streamed (Content-Type text/event-stream or similar)
        const contentType = response.headers.get('Content-Type') || '';
        if (contentType.includes('text/event-stream') || contentType.includes('application/x-ndjson')) {
            // Streaming response
            return handleStreamingResponse(response, assistantBody);
        } else {
            // Non-streaming: read full response
            const data = await response.json();
            if (data.success && data.message) {
                assistantBody.innerHTML = renderMarkdown(data.message.content);
                // Update conversation ID if new
                if (data.conversation_id) {
                    currentConversationId = data.conversation_id;
                    loadConversations(); // Refresh sidebar
                }
                // Add to history
                messageHistory.push({ role: 'assistant', content: data.message.content, timestamp: new Date().toISOString() });
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        }
    })
    .catch(error => {
        if (error.name === 'AbortError') {
            // User cancelled
            return;
        }
        console.error('Send error:', error);
        showErrorMessage(`Error: ${error.message}`);
        // Remove placeholder if still there
        if (assistantMessageDiv.parentNode) {
            assistantMessageDiv.remove();
        }
    })
    .finally(() => {
        isProcessing = false;
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
        scrollToBottom();
        abortController = null;
    });
}

// --- Create a placeholder for assistant's streaming message ---
function createAssistantMessagePlaceholder() {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message';
    
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.textContent = '🤖';
    
    const bodyDiv = document.createElement('div');
    bodyDiv.className = 'message-body';
    bodyDiv.textContent = '▊'; // Blinking cursor placeholder
    bodyDiv.id = 'streaming-message-body';
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-timestamp';
    
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(bodyDiv);
    messageDiv.appendChild(timeDiv);
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
    return messageDiv;
}

// --- Handle streaming response (Server-Sent Events or NDJSON) ---
async function handleStreamingResponse(response, bodyElement) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';
    
    // Add cancel button or handle abort via global
    // (User can press Escape to cancel)
    document.addEventListener('keydown', cancelOnEscape);
    
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            // Process lines
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') {
                        // End of stream
                        break;
                    }
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.content) {
                            fullContent += parsed.content;
                            bodyElement.innerHTML = renderMarkdown(fullContent);
                            scrollToBottom();
                        }
                    } catch (e) {
                        // Ignore invalid JSON
                    }
                }
            }
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            // Handle cancellation
            bodyElement.innerHTML = renderMarkdown(fullContent) + '<br><em>Generation cancelled.</em>';
        } else {
            console.error('Stream error:', error);
            throw error;
        }
    } finally {
        document.removeEventListener('keydown', cancelOnEscape);
        // Clean up buffer
        if (buffer) {
            // Try to parse remaining
            if (buffer.startsWith('data: ')) {
                const data = buffer.slice(6).trim();
                if (data && data !== '[DONE]') {
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.content) {
                            fullContent += parsed.content;
                            bodyElement.innerHTML = renderMarkdown(fullContent);
                        }
                    } catch (e) {}
                }
            }
        }
        // Remove the streaming ID
        bodyElement.removeAttribute('id');
        // Update history
        messageHistory.push({ role: 'assistant', content: fullContent, timestamp: new Date().toISOString() });
        // Update conversation list after complete message
        loadConversations();
    }
}

// --- Handle Escape key to cancel streaming ---
function cancelOnEscape(e) {
    if (e.key === 'Escape' && abortController) {
        abortController.abort();
        abortController = null;
        isProcessing = false;
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
}

// --- Handle Enter key (Shift+Enter for newline) ---
function handleEnterKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

// --- (Optional) Expose functions for testing ---
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        escapeHtml,
        renderMarkdown,
        sendMessage,
        startNewConversation,
        loadConversations
    };
}