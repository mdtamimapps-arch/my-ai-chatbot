document.addEventListener('DOMContentLoaded', function() {
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');

    function addMessage(text, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        messageDiv.textContent = text;
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function showTyping() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message typing-indicator';
        typingDiv.id = 'typing-indicator';
        typingDiv.textContent = '⏳ চিন্তা করছি...';
        chatBox.appendChild(typingDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function hideTyping() {
        const typing = document.getElementById('typing-indicator');
        if (typing) typing.remove();
    }

    async function sendQuestion() {
        const question = userInput.value.trim();
        if (!question) return;

        addMessage(question, true);
        userInput.value = '';
        sendBtn.disabled = true;
        showTyping();

        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: question }),
            });

            const data = await response.json();

            if (response.ok) {
                hideTyping();
                addMessage(data.answer, false);
            } else {
                hideTyping();
                addMessage('❌ ' + (data.error || 'কিছু একটা সমস্যা হয়েছে!'), false);
            }
        } catch (error) {
            hideTyping();
            addMessage('❌ সার্ভারের সাথে যোগাযোগ করতে পারছি না!', false);
        } finally {
            sendBtn.disabled = false;
            userInput.focus();
        }
    }

    sendBtn.addEventListener('click', sendQuestion);
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') sendQuestion();
    });

    userInput.focus();
});
