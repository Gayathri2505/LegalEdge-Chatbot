document.addEventListener('DOMContentLoaded', () => {
    let currentChatId = null;

    const centerForm = document.getElementById('center-form');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message');
    const messageBottomInput = document.getElementById('message-bottom');
    const chatWindow = document.getElementById('chatMessages');
    const chatHistory = document.getElementById('chat-history');
    const welcomeContent = document.getElementById('welcomeContent');
    const bottomInputArea = document.getElementById('bottomInputArea');
    const chatArea = document.querySelector('.chat-area');

    // Toggle sidebar collapse
    document.getElementById('toggleSidebar').addEventListener('click', function () {
        document.getElementById('sidebar').classList.toggle('collapsed');
    });

    // New chat button click
    document.getElementById('new-chat-btn').addEventListener('click', function (e) {
        e.preventDefault();
        startNewChat();
    });

    // Handle suggestion card clicks
    document.querySelectorAll('.suggestion-card').forEach(card => {
        card.addEventListener('click', () => {
            const cardTitle = card.querySelector('.card-title');
            const cardDescription = card.querySelector('.card-description');

            let message = '';
            if (cardTitle && cardDescription) {
                message = cardDescription.textContent.trim();
            } else {
                message = card.textContent.trim();
            }

            if (message) {
                messageInput.value = message;
                //centerForm.dispatchEvent(new Event('submit'));
            }
        });
    });

    // Handle center form submission (initial input)
    centerForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        switchToChatMode();
        sendMessage(message);
        messageInput.value = '';
    });

    // Handle chat form submission (bottom input)
    chatForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const message = messageBottomInput.value.trim();
        if (!message) return;

        sendMessage(message);
        messageBottomInput.value = '';
    });

    function switchToChatMode() {
        // Hide welcome content
        welcomeContent.style.display = 'none';

        // Show chat messages container
        chatMessages.style.display = 'flex';

        // Show bottom input area
        bottomInputArea.style.display = 'block';

        // Adjust chat area layout
        chatArea.classList.add('chat-mode');
        chatArea.style.justifyContent = 'flex-start';
        chatArea.style.textAlign = 'left';
    }

    function switchToWelcomeMode() {
        // Show welcome content
        welcomeContent.style.display = 'flex';

        // Hide chat messages container
        chatMessages.style.display = 'none';

        // Hide bottom input area
        bottomInputArea.style.display = 'none';

        // Reset chat area layout
        chatArea.classList.remove('chat-mode');
        chatArea.style.justifyContent = 'center';
        chatArea.style.textAlign = 'center';
    }

    function sendMessage(message) {
        // Display user message
        const userMsg = document.createElement('div');
        userMsg.classList.add('chat-message', 'user');
        userMsg.textContent = message;
        chatMessages.appendChild(userMsg);
        scrollToBottom();

        // Bot message placeholder
        const botMsg = document.createElement('div');
        botMsg.classList.add('chat-message', 'bot', 'generating');
        botMsg.innerHTML = "<i>⏳ Generating...</i>";
        chatMessages.appendChild(botMsg);
        scrollToBottom();

        // Send message to backend
        const requestData = new URLSearchParams();
        requestData.append('message', message);
        if (currentChatId) {
            requestData.append('chat_id', currentChatId);
        }

        fetch("chat/chatbot-response/", {
            method: "POST",
            headers: {
                "X-CSRFToken": getCSRFToken(),
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: requestData
        })
            .then(response => response.json())
            .then(data => {
                if (!currentChatId && data.chat_id) {
                    currentChatId = data.chat_id;
                }

                const fullResponse = data.response || 'Oops! No reply.';
                botMsg.classList.remove('generating');

                // Use marked if available, otherwise plain text
                renderMarkdownToElement(botMsg, fullResponse);

                scrollToBottom();
                // Update chat title for first message
                const totalUserMessages = chatMessages.querySelectorAll('.chat-message.user').length;
                if (totalUserMessages === 1) {
                    updateChatTitle(currentChatId, message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                botMsg.classList.remove('generating');
                botMsg.innerHTML = '⚠️ Bot is unavailable right now.';
            });
    }

    function renderMarkdownToElement(element, markdown) {
        // Configure marked to use highlight.js
        if (typeof marked !== 'undefined' && typeof hljs !== 'undefined') {
            marked.setOptions({
                highlight: function (code, lang) {
                    if (lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(code, { language: lang }).value;
                    } else {
                        return hljs.highlightAuto(code).value;
                    }
                },
                langPrefix: 'hljs language-', // highlight.js style class prefix
                breaks: true                  // optionally support line breaks
            });
        }
        // Actually render markdown into HTML!
        if (typeof marked !== 'undefined') {
            element.innerHTML = marked.parse(markdown);
        } else {
            // Fallback if marked is unavailable
            element.textContent = markdown;
        }

    }



    function updateChatTitle(chatId, message) {
        fetch("chat/update-chat-title/", {
            method: "POST",
            headers: {
                "X-CSRFToken": getCSRFToken(),
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                chat_id: chatId,
                message: message
            })
        })
            .then(res => res.json())
            .then(data => {
                if (data.title) {
                    loadChatHistory();
                }
            })
            .catch(err => console.error("Title update failed:", err));
    }

    function scrollToBottom() {
        chatMessages.scrollTo({
        top: chatMessages.scrollHeight,
        behavior: "smooth"
    });
    }

    function startNewChat() {
        fetch("chat/new-chat/", {
            method: "POST",
            headers: {
                "X-CSRFToken": getCSRFToken(),
                "Content-Type": "application/json"
            },
            body: JSON.stringify({})
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === "ready_for_new_chat") {
                    // Reset frontend state
                    currentChatId = null;
                    switchToWelcomeMode();

                    // Clear inputs and messages
                    messageInput.value = '';
                    messageBottomInput.value = '';
                    chatMessages.innerHTML = '';

                    // Refresh sidebar
                    loadChatHistory();
                } else {
                    alert("Unexpected response from server.");
                }
            })
            .catch(error => {
                console.error("Error starting new chat:", error);
                alert("Something went wrong. Please try again.");
            });
    }

    function loadChatHistory() {
        fetch("chat/get-user-chats/")
            .then(response => response.json())
            .then(data => {
                const grouped = groupChatsByTime(data.chats);
                chatHistory.innerHTML = ''; // clear existing

                // Render sections with chats
                renderChatSection("Recent", grouped.recent);
                renderChatSection("Last Week", grouped.lastWeek);
                renderChatSection("Last Month", grouped.lastMonth);
                renderChatSection("Older", grouped.older);
            })
            .catch(error => {
                console.error("Error loading chat history:", error);
            });
    }

    function renderChatSection(title, chats) {
        if (chats.length === 0) return;

        const sectionTitle = document.createElement('div');
        sectionTitle.className = 'recent-title';
        sectionTitle.textContent = title;
        chatHistory.appendChild(sectionTitle);

        chats.forEach(chat => {
            const li = document.createElement('li');
            li.classList.add('chat-item');
            if (chat.chat_id === currentChatId) li.classList.add('active');

            li.innerHTML = `
                <div class="chat-link-wrapper">
                    <a href="#" data-chat-id="${chat.chat_id}">
                    <i class="fa-solid fa-comment" style="margin-right: 8px; font-size: 13px;"></i>
                    <span>${chat.title
                    ? chat.title.split(' ').slice(0, 3).join(' ') + (chat.title.split(' ').length > 3 ? '…' : '')
                    : 'Untitled Chat'
                }</span>
                    </a>
                    
                </div>
                `;

            li.querySelector('a').addEventListener('click', (e) => {
                e.preventDefault();
                selectChat(chat.chat_id);
            });

            chatHistory.appendChild(li);
        });
    }


    function selectChat(chatId) {
        currentChatId = chatId;
        chatWindow.innerHTML = '';
        switchToChatMode();
        document.querySelectorAll('#chat-history .chat-item').forEach(li => {
            const link = li.querySelector('a');
            li.classList.toggle('active', link && link.dataset.chatId === chatId);
        });

        fetch(`chat/get-messages/${chatId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.messages) {
                    data.messages.forEach(msg => {
                        const msgDiv = document.createElement('div');
                        msgDiv.classList.add('chat-message');
                        msgDiv.classList.add(msg.role === 'user' ? 'user' : 'bot');
                        msgDiv.innerHTML = marked.parse(msg.message);
                        chatWindow.appendChild(msgDiv);
                    });
                    scrollToBottom();
                }
            })
            .catch(error => {
                console.error("Error fetching chat messages:", error);
            });
    }

    function getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [key, value] = cookie.trim().split('=');
            if (key === 'csrftoken') return value;
        }
    }

    function groupChatsByTime(chats) {
        const today = new Date();
        const oneDayAgo = new Date(today);
        const oneWeekAgo = new Date(today);
        const oneMonthAgo = new Date(today);

        oneDayAgo.setDate(today.getDate() - 1);
        oneWeekAgo.setDate(today.getDate() - 7);
        oneMonthAgo.setDate(today.getDate() - 30);

        print

        return {
            recent: chats.filter(c => new Date(c.modified_at) >= oneDayAgo),
            lastWeek: chats.filter(c => new Date(c.modified_at) < oneDayAgo && new Date(c.modified_at) >= oneWeekAgo),
            lastMonth: chats.filter(c => new Date(c.modified_at) < oneWeekAgo && new Date(c.modified_at) >= oneMonthAgo),
            older: chats.filter(c => new Date(c.modified_at) < oneMonthAgo)
        };
    }

    // Load initial chat history
    loadChatHistory();
});

