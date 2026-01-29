// Chat con Ollama AI
document.addEventListener('DOMContentLoaded', function() {
    const messagesDiv = document.getElementById('messages');
    const inputField = document.getElementById('input');
    
    if (!messagesDiv || !inputField) return;
    
    // Control de throttling en el cliente
    let lastRequestTime = 0;
    const MIN_INTERVAL_MS = 5000; // 5 segundos entre solicitudes (para cuenta nueva)
    let isWaitingForResponse = false;
    
    // Enviar mensaje al presionar Enter
    inputField.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && this.value.trim()) {
            const userMessage = this.value.trim();
            sendMessage(userMessage);
            this.value = '';
        }
    });
    
    function sendMessage(message) {
        // Verificar throttling
        const now = Date.now();
        const timeSinceLastRequest = now - lastRequestTime;
        
        if (isWaitingForResponse) {
            showError('Por favor espera a que se complete la solicitud anterior.');
            return;
        }
        
        if (timeSinceLastRequest < MIN_INTERVAL_MS) {
            const waitTime = ((MIN_INTERVAL_MS - timeSinceLastRequest) / 1000).toFixed(1);
            showError(`Por favor espera ${waitTime} segundos antes de enviar otro mensaje.`);
            inputField.disabled = false;
            return;
        }
        
        isWaitingForResponse = true;
        inputField.disabled = true;
        
        // Mostrar mensaje del usuario
        const userDiv = document.createElement('div');
        userDiv.className = 'message user-message';
        userDiv.innerHTML = `<p>${escapeHtml(message)}</p>`;
        messagesDiv.appendChild(userDiv);
        
        // Mostrar indicador de carga
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot-message loading';
        loadingDiv.innerHTML = '<p>Escribiendo...</p>';
        messagesDiv.appendChild(loadingDiv);
        
        // Scroll al último mensaje
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        // Enviar petición al servidor
        fetch('/api/chat?message=' + encodeURIComponent(message))
            .then(response => response.json())
            .then(data => {
                // Remover indicador de carga
                loadingDiv.remove();
                
                if (data.error) {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'message bot-message error';
                    errorDiv.innerHTML = `<p>Error: ${escapeHtml(data.error)}</p>`;
                    messagesDiv.appendChild(errorDiv);
                } else {
                    const botDiv = document.createElement('div');
                    botDiv.className = 'message bot-message';
                    botDiv.innerHTML = `<p>${escapeHtml(data.message)}</p>`;
                    messagesDiv.appendChild(botDiv);
                }
                
                // Actualizar tiempo de última solicitud
                lastRequestTime = Date.now();
                isWaitingForResponse = false;
                inputField.disabled = false;
                inputField.focus();
                
                // Scroll al último mensaje
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            })
            .catch(error => {
                loadingDiv.remove();
                const errorDiv = document.createElement('div');
                errorDiv.className = 'message bot-message error';
                errorDiv.innerHTML = `<p>Error de conexión: ${escapeHtml(error.message)}</p>`;
                messagesDiv.appendChild(errorDiv);
                
                lastRequestTime = Date.now();
                isWaitingForResponse = false;
                inputField.disabled = false;
                inputField.focus();
                
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            });
    }
    
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message bot-message error';
        errorDiv.innerHTML = `<p>${escapeHtml(message)}</p>`;
        messagesDiv.appendChild(errorDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    // Función para escapar HTML y prevenir inyecciones
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
