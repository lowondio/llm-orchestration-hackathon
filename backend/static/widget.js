(function() {
  'use strict';

  // Get agent ID from script tag data attribute
  const currentScript = document.currentScript || document.querySelector('script[data-agent-id]');
  const AGENT_ID = currentScript ? currentScript.getAttribute('data-agent-id') : null;
  const API_BASE_URL = currentScript ? (currentScript.getAttribute('data-api-url') || 'http://localhost:8000') : 'http://localhost:8000';

  if (!AGENT_ID) {
    console.error('[AI Widget] Missing data-agent-id attribute on script tag');
    return;
  }

  // Session management
  const SESSION_KEY = `ai_widget_session_${AGENT_ID}`;
  let sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem(SESSION_KEY, sessionId);
  }

  // Message history
  const HISTORY_KEY = `ai_widget_history_${AGENT_ID}`;
  let messageHistory = [];
  try {
    const stored = localStorage.getItem(HISTORY_KEY);
    if (stored) {
      messageHistory = JSON.parse(stored);
    }
  } catch (e) {
    console.warn('[AI Widget] Failed to load message history', e);
  }

  // Inject CSS
  const style = document.createElement('style');
  style.textContent = `
    .ai-widget-container * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    .ai-widget-button {
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999999;
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .ai-widget-button:hover {
      transform: scale(1.05);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
    }

    .ai-widget-button svg {
      width: 28px;
      height: 28px;
      fill: white;
    }

    .ai-widget-window {
      position: fixed;
      bottom: 90px;
      right: 20px;
      width: 380px;
      height: 600px;
      max-height: calc(100vh - 120px);
      background: #1a1a2e;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      display: none;
      flex-direction: column;
      z-index: 999998;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      overflow: hidden;
    }

    .ai-widget-window.open {
      display: flex;
    }

    .ai-widget-header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 16px 20px;
      font-weight: 600;
      font-size: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .ai-widget-close {
      background: none;
      border: none;
      color: white;
      cursor: pointer;
      font-size: 24px;
      line-height: 1;
      padding: 0;
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0.8;
      transition: opacity 0.2s;
    }

    .ai-widget-close:hover {
      opacity: 1;
    }

    .ai-widget-messages {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      background: #16213e;
    }

    .ai-widget-message {
      margin-bottom: 16px;
      display: flex;
      flex-direction: column;
    }

    .ai-widget-message.user {
      align-items: flex-end;
    }

    .ai-widget-message.assistant {
      align-items: flex-start;
    }

    .ai-widget-message-bubble {
      max-width: 80%;
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.5;
      word-wrap: break-word;
    }

    .ai-widget-message.user .ai-widget-message-bubble {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }

    .ai-widget-message.assistant .ai-widget-message-bubble {
      background: #0f3460;
      color: #e8e8e8;
    }

    .ai-widget-typing {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 12px 16px;
      background: #0f3460;
      border-radius: 12px;
      max-width: 80px;
    }

    .ai-widget-typing-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #667eea;
      animation: ai-widget-typing-animation 1.4s infinite;
    }

    .ai-widget-typing-dot:nth-child(2) {
      animation-delay: 0.2s;
    }

    .ai-widget-typing-dot:nth-child(3) {
      animation-delay: 0.4s;
    }

    @keyframes ai-widget-typing-animation {
      0%, 60%, 100% {
        transform: translateY(0);
        opacity: 0.7;
      }
      30% {
        transform: translateY(-10px);
        opacity: 1;
      }
    }

    .ai-widget-input-container {
      padding: 16px 20px;
      background: #1a1a2e;
      border-top: 1px solid #0f3460;
      display: flex;
      gap: 12px;
    }

    .ai-widget-input {
      flex: 1;
      background: #0f3460;
      border: 1px solid #16213e;
      border-radius: 8px;
      padding: 12px 16px;
      color: white;
      font-size: 14px;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s;
    }

    .ai-widget-input:focus {
      border-color: #667eea;
    }

    .ai-widget-input::placeholder {
      color: #6b7280;
    }

    .ai-widget-send {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border: none;
      border-radius: 8px;
      padding: 12px 20px;
      color: white;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s;
    }

    .ai-widget-send:hover:not(:disabled) {
      opacity: 0.9;
    }

    .ai-widget-send:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    @media (max-width: 480px) {
      .ai-widget-window {
        width: calc(100vw - 40px);
        height: calc(100vh - 120px);
        right: 20px;
        bottom: 90px;
      }
    }
  `;
  document.head.appendChild(style);

  // Create widget HTML
  const container = document.createElement('div');
  container.className = 'ai-widget-container';
  container.innerHTML = `
    <button class="ai-widget-button" id="ai-widget-toggle" aria-label="Open chat">
      <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
      </svg>
    </button>
    <div class="ai-widget-window" id="ai-widget-window">
      <div class="ai-widget-header">
        <span>AI Assistant</span>
        <button class="ai-widget-close" id="ai-widget-close" aria-label="Close chat">&times;</button>
      </div>
      <div class="ai-widget-messages" id="ai-widget-messages"></div>
      <div class="ai-widget-input-container">
        <input
          type="text"
          class="ai-widget-input"
          id="ai-widget-input"
          placeholder="Type your message..."
          autocomplete="off"
        />
        <button class="ai-widget-send" id="ai-widget-send">Send</button>
      </div>
    </div>
  `;
  document.body.appendChild(container);

  // Get elements
  const toggleBtn = document.getElementById('ai-widget-toggle');
  const closeBtn = document.getElementById('ai-widget-close');
  const widgetWindow = document.getElementById('ai-widget-window');
  const messagesContainer = document.getElementById('ai-widget-messages');
  const input = document.getElementById('ai-widget-input');
  const sendBtn = document.getElementById('ai-widget-send');

  // State
  let isOpen = false;
  let isSending = false;

  // Functions
  function toggleWidget() {
    isOpen = !isOpen;
    widgetWindow.classList.toggle('open', isOpen);
    if (isOpen) {
      input.focus();
    }
  }

  function addMessage(text, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `ai-widget-message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'ai-widget-message-bubble';
    bubble.textContent = text;

    messageDiv.appendChild(bubble);
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Save to history
    messageHistory.push({ text, role, timestamp: Date.now() });
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(messageHistory.slice(-50))); // Keep last 50 messages
    } catch (e) {
      console.warn('[AI Widget] Failed to save message history', e);
    }
  }

  function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'ai-widget-message assistant';
    typingDiv.id = 'ai-widget-typing-indicator';

    const typingBubble = document.createElement('div');
    typingBubble.className = 'ai-widget-typing';
    typingBubble.innerHTML = `
      <div class="ai-widget-typing-dot"></div>
      <div class="ai-widget-typing-dot"></div>
      <div class="ai-widget-typing-dot"></div>
    `;

    typingDiv.appendChild(typingBubble);
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function hideTypingIndicator() {
    const typingIndicator = document.getElementById('ai-widget-typing-indicator');
    if (typingIndicator) {
      typingIndicator.remove();
    }
  }

  async function sendMessage() {
    const message = input.value.trim();
    if (!message || isSending) return;

    // Add user message
    addMessage(message, 'user');
    input.value = '';

    // Disable input
    isSending = true;
    sendBtn.disabled = true;
    input.disabled = true;

    // Show typing indicator
    showTypingIndicator();

    try {
      const response = await fetch(`${API_BASE_URL}/api/widget/chat/${AGENT_ID}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          session_id: sessionId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Hide typing indicator
      hideTypingIndicator();

      // Add assistant response
      if (data.response) {
        addMessage(data.response, 'assistant');
      } else {
        addMessage('Sorry, I could not generate a response.', 'assistant');
      }
    } catch (error) {
      console.error('[AI Widget] Error sending message:', error);
      hideTypingIndicator();
      addMessage('Sorry, there was an error connecting to the assistant. Please try again.', 'assistant');
    } finally {
      // Re-enable input
      isSending = false;
      sendBtn.disabled = false;
      input.disabled = false;
      input.focus();
    }
  }

  // Load message history
  function loadHistory() {
    messageHistory.forEach(msg => {
      const messageDiv = document.createElement('div');
      messageDiv.className = `ai-widget-message ${msg.role}`;

      const bubble = document.createElement('div');
      bubble.className = 'ai-widget-message-bubble';
      bubble.textContent = msg.text;

      messageDiv.appendChild(bubble);
      messagesContainer.appendChild(messageDiv);
    });
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Event listeners
  toggleBtn.addEventListener('click', toggleWidget);
  closeBtn.addEventListener('click', toggleWidget);
  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Load history on init
  loadHistory();

  console.log('[AI Widget] Initialized with agent ID:', AGENT_ID);
})();
