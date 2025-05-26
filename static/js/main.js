document.addEventListener('DOMContentLoaded', function() {
    // Tab functionality
    const tabs = document.querySelectorAll('.nav-tab');
    const sections = document.querySelectorAll('.section');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Remove active class from all tabs and sections
            tabs.forEach(t => t.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));
            
            // Add active class to clicked tab
            tab.classList.add('active');
            
            // Show corresponding section
            const sectionId = tab.getAttribute('data-section');
            document.getElementById(sectionId).classList.add('active');
        });
    });

    // Mobile menu functionality
    const mobileMenuButton = document.querySelector('.mobile-menu-button');
    const navTabs = document.querySelector('.nav-tabs');
    
    if (mobileMenuButton) {
        mobileMenuButton.addEventListener('click', () => {
            mobileMenuButton.classList.toggle('active');
            navTabs.classList.toggle('show');
        });
    }

    // Voice selection
    const voiceButtons = document.querySelectorAll('.voice-btn');
    let currentVoice = 'tiffany'; // Default voice
    
    voiceButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons
            voiceButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            button.classList.add('active');
            
            // Update current voice
            currentVoice = button.getAttribute('data-voice');
            
            // If websocket is connected, send voice change message
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'voice_change',
                    voice: currentVoice
                }));
            }
        });
    });

    // WebSocket and audio handling
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    const micVisualizer = document.getElementById('micVisualizer');
    const statusElement = document.getElementById('status');
    const transcriptElement = document.getElementById('transcript');
    
    let ws = null;
    let mediaRecorder = null;
    let audioContext = null;
    let audioQueue = [];
    let isRecording = false;
    let clientId = null;
    
    // Function to show status messages
    function showStatus(message, type = 'info') {
        const statusMsg = document.createElement('div');
        statusMsg.className = `status-message ${type}`;
        statusMsg.textContent = message;
        
        // Insert at the top of the transcript
        if (transcriptElement.firstChild) {
            transcriptElement.insertBefore(statusMsg, transcriptElement.firstChild);
        } else {
            transcriptElement.appendChild(statusMsg);
        }
        
        // Remove after 5 seconds
        setTimeout(() => {
            statusMsg.remove();
        }, 5000);
    }
    
    // Function to add message to transcript
    function addMessage(text, role, timestamp) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${role}-text`;
        
        const timestampElement = document.createElement('span');
        timestampElement.className = 'message-timestamp';
        timestampElement.textContent = timestamp;
        
        const contentElement = document.createElement('span');
        contentElement.className = 'message-content';
        contentElement.textContent = text;
        
        messageElement.appendChild(timestampElement);
        messageElement.appendChild(document.createTextNode(' '));
        messageElement.appendChild(contentElement);
        
        transcriptElement.appendChild(messageElement);
        transcriptElement.scrollTop = transcriptElement.scrollHeight;
    }
    
    // Function to initialize WebSocket connection
    function initializeWebSocket() {
        // Generate a unique client ID
        clientId = Date.now().toString();
        
        // Create WebSocket connection
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${clientId}`;
        
        ws = new WebSocket(wsUrl);
        
        ws.onopen = function() {
            console.log('WebSocket connection established');
            showStatus('Connected to server', 'success');
            startButton.disabled = false;
        };
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.type === 'text') {
                // Add text message to transcript
                addMessage(data.data, data.role.toLowerCase(), data.timestamp);
            } else if (data.type === 'audio') {
                // Handle audio data
                playAudio(data.data);
            } else if (data.type === 'status') {
                // Handle status updates
                showStatus(data.message, data.status === 'error' ? 'error' : 'info');
            } else if (data.type === 'latency') {
                // Display latency information
                console.log(`Latency: ${data.data} seconds`);
            } else if (data.type === 'error') {
                // Handle error messages
                showStatus(`Error: ${data.message}`, 'error');
            }
        };
        
        ws.onclose = function() {
            console.log('WebSocket connection closed');
            showStatus('Disconnected from server', 'error');
            startButton.disabled = false;
            stopButton.disabled = true;
            isRecording = false;
            if (micVisualizer) {
                micVisualizer.classList.remove('recording');
            }
            statusElement.textContent = 'Status: Not recording';
        };
        
        ws.onerror = function(error) {
            console.error('WebSocket error:', error);
            showStatus('Connection error', 'error');
        };
    }
    
    // Function to play audio
    function playAudio(base64Audio) {
        if (!base64Audio) return;
        
        try {
            // Convert base64 to array buffer
            const binaryString = window.atob(base64Audio);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            
            // Create audio context if not exists
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)({
                    sampleRate: 24000
                });
            }
            
            // Queue the audio data
            audioQueue.push(bytes.buffer);
            
            // If not already playing, start playing
            if (audioQueue.length === 1) {
                playNextAudio();
            }
        } catch (error) {
            console.error('Error playing audio:', error);
        }
    }
    
    // Function to play next audio in queue
    function playNextAudio() {
        if (audioQueue.length === 0) return;
        
        const audioBuffer = audioQueue[0];
        
        audioContext.decodeAudioData(audioBuffer, (buffer) => {
            const source = audioContext.createBufferSource();
            source.buffer = buffer;
            source.connect(audioContext.destination);
            
            source.onended = () => {
                // Remove played audio from queue
                audioQueue.shift();
                
                // Play next audio if available
                if (audioQueue.length > 0) {
                    playNextAudio();
                }
            };
            
            source.start(0);
        }, (error) => {
            console.error('Error decoding audio data:', error);
            audioQueue.shift();
            if (audioQueue.length > 0) {
                playNextAudio();
            }
        });
    }
    
    // Function to start recording
    async function startRecording() {
        try {
            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Create media recorder
            mediaRecorder = new MediaRecorder(stream);
            
            mediaRecorder.ondataavailable = function(event) {
                if (event.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                    // Convert blob to base64
                    const reader = new FileReader();
                    reader.onloadend = function() {
                        const base64data = reader.result.split(',')[1];
                        
                        // Send audio data to server
                        ws.send(JSON.stringify({
                            type: 'audio',
                            data: base64data
                        }));
                    };
                    reader.readAsDataURL(event.data);
                }
            };
            
            // Start recording
            mediaRecorder.start(100); // Collect data every 100ms
            
            isRecording = true;
            startButton.disabled = true;
            stopButton.disabled = false;
            if (micVisualizer) {
                micVisualizer.classList.add('recording');
            }
            statusElement.textContent = 'Status: Recording';
            
            showStatus('Recording started', 'success');
        } catch (error) {
            console.error('Error starting recording:', error);
            showStatus(`Microphone access error: ${error.message}`, 'error');
        }
    }
    
    // Function to stop recording
    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            
            // Stop all tracks
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            
            isRecording = false;
            startButton.disabled = false;
            stopButton.disabled = true;
            if (micVisualizer) {
                micVisualizer.classList.remove('recording');
            }
            statusElement.textContent = 'Status: Not recording';
            
            showStatus('Recording stopped', 'info');
        }
    }
    
    // Initialize WebSocket on page load
    initializeWebSocket();
    
    // Event listeners for buttons
    startButton.addEventListener('click', startRecording);
    stopButton.addEventListener('click', stopRecording);
    
    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        if (ws) {
            ws.close();
        }
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
    });
});