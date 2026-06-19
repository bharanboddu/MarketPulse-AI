/**
 * MarketPulse AI - Chatbot Client
 * Handles sidebar toggling and AI assistant messaging
 */

document.addEventListener("DOMContentLoaded", function () {
    const chatSidebar = document.getElementById("chat-sidebar");
    const toggleBtn = document.getElementById("chat-sidebar-toggle");
    const closeBtn = document.getElementById("chat-sidebar-close");
    const form = document.getElementById("chat-input-form");
    const input = document.getElementById("chat-input-field");
    const messagesContainer = document.getElementById("chat-messages-container");
    
    if (!chatSidebar) return;
    
    // Toggle Chat
    toggleBtn.addEventListener("click", function () {
        chatSidebar.classList.toggle("open");
        scrollToBottom();
        // Hide red ping dot if clicked
        const ping = toggleBtn.querySelector(".chat-ping-dot");
        if (ping) ping.style.display = "none";
    });
    
    closeBtn.addEventListener("click", function () {
        chatSidebar.classList.remove("open");
    });
    
    // Submit message
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        
        const messageText = input.value.trim();
        if (!messageText) return;
        
        // Append user bubble
        appendMessage(messageText, "user");
        input.value = "";
        
        // Append typing indicator
        const typingId = appendTypingIndicator();
        scrollToBottom();
        
        // Fetch response
        fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: messageText,
                symbol: ACTIVE_SYMBOL
            })
        })
        .then(res => res.json())
        .then(data => {
            // Remove typing indicator
            removeTypingIndicator(typingId);
            
            // Append assistant response
            appendMessage(data.response, "system");
            scrollToBottom();
        })
        .catch(err => {
            removeTypingIndicator(typingId);
            appendMessage("I encountered an issue communicating with the AI service. Please verify your internet or API key.", "system");
            scrollToBottom();
            console.error("Chat error:", err);
        });
    });
    
    function appendMessage(text, sender) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${sender}-message`;
        
        // Convert Markdown bold **text** to HTML strong tags
        const formattedText = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
            
        msgDiv.innerHTML = `
            <div class="message-bubble">
                ${formattedText}
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
    }
    
    function appendTypingIndicator() {
        const typingId = "typing-" + Date.now();
        const typingDiv = document.createElement("div");
        typingDiv.className = "message system-message typing-indicator-msg";
        typingDiv.id = typingId;
        typingDiv.innerHTML = `
            <div class="message-bubble" style="display:flex;gap:4px;padding:10px 14px;">
                <span class="dot" style="width:6px;height:6px;background:var(--text-secondary);border-radius:50%;animation:typing 1.4s infinite both;"></span>
                <span class="dot" style="width:6px;height:6px;background:var(--text-secondary);border-radius:50%;animation:typing 1.4s infinite both 0.2s;"></span>
                <span class="dot" style="width:6px;height:6px;background:var(--text-secondary);border-radius:50%;animation:typing 1.4s infinite both 0.4s;"></span>
            </div>
        `;
        
        // Inject animation style inline if not in CSS
        if (!document.getElementById("typing-animation-style")) {
            const style = document.createElement("style");
            style.id = "typing-animation-style";
            style.innerHTML = `
                @keyframes typing {
                    0%, 100% { opacity: 0.2; transform: translateY(0); }
                    50% { opacity: 1; transform: translateY(-4px); }
                }
            `;
            document.head.appendChild(style);
        }
        
        messagesContainer.appendChild(typingDiv);
        return typingId;
    }
    
    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }
    
    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
});
