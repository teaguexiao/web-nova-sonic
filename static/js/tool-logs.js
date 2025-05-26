// Tool logs functionality
document.addEventListener('DOMContentLoaded', function() {
    const refreshLogsBtn = document.getElementById('refreshLogsBtn');
    const clearLogsBtn = document.getElementById('clearLogsBtn');
    const toolLogsList = document.getElementById('toolLogsList');
    
    // Function to fetch and display tool logs
    async function fetchToolLogs() {
        try {
            const response = await fetch('/tool-logs');
            if (!response.ok) {
                throw new Error('Failed to fetch tool logs');
            }
            
            const logs = await response.json();
            displayToolLogs(logs);
        } catch (error) {
            console.error('Error fetching tool logs:', error);
        }
    }
    
    // Function to display tool logs
    function displayToolLogs(logs) {
        // Clear existing logs
        toolLogsList.innerHTML = '';
        
        if (logs.length === 0) {
            toolLogsList.innerHTML = '<div class="empty-logs-message">No tool invocations logged yet.</div>';
            return;
        }
        
        // Display logs in reverse chronological order (newest first)
        logs.slice().reverse().forEach(log => {
            const logItem = document.createElement('div');
            logItem.className = 'tool-log-item';
            
            // Create log header
            const logHeader = document.createElement('div');
            logHeader.className = 'tool-log-header';
            
            const logNameSpan = document.createElement('div');
            logNameSpan.className = 'tool-log-name';
            logNameSpan.innerHTML = `${log.tool} <span class="tool-log-status ${log.status === 'success' ? 'tool-log-status-success' : 'tool-log-status-error'}">${log.status}</span>`;
            
            const logTimestamp = document.createElement('div');
            logTimestamp.className = 'tool-log-timestamp';
            logTimestamp.textContent = log.timestamp;
            
            logHeader.appendChild(logNameSpan);
            logHeader.appendChild(logTimestamp);
            
            // Create log content
            const logContent = document.createElement('div');
            logContent.className = 'tool-log-content';
            
            // Input section
            const inputSection = document.createElement('div');
            inputSection.className = 'tool-log-section';
            
            const inputTitle = document.createElement('div');
            inputTitle.className = 'tool-log-section-title';
            inputTitle.textContent = 'Input:';
            
            const inputData = document.createElement('div');
            inputData.className = 'tool-log-data';
            inputData.textContent = JSON.stringify(log.input, null, 2);
            
            inputSection.appendChild(inputTitle);
            inputSection.appendChild(inputData);
            
            // Output section
            const outputSection = document.createElement('div');
            outputSection.className = 'tool-log-section';
            
            const outputTitle = document.createElement('div');
            outputTitle.className = 'tool-log-section-title';
            outputTitle.textContent = 'Output:';
            
            const outputData = document.createElement('div');
            outputData.className = 'tool-log-data';
            outputData.textContent = JSON.stringify(log.output, null, 2);
            
            outputSection.appendChild(outputTitle);
            outputSection.appendChild(outputData);
            
            logContent.appendChild(inputSection);
            logContent.appendChild(outputSection);
            
            // Add all elements to the log item
            logItem.appendChild(logHeader);
            logItem.appendChild(logContent);
            
            // Add the log item to the list
            toolLogsList.appendChild(logItem);
        });
    }
    
    // Refresh logs when button is clicked
    if (refreshLogsBtn) {
        refreshLogsBtn.addEventListener('click', fetchToolLogs);
    }
    
    // Clear logs when button is clicked
    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', function() {
            toolLogsList.innerHTML = '<div class="empty-logs-message">No tool invocations logged yet.</div>';
        });
    }
    
    // Initial fetch of tool logs
    if (toolLogsList) {
        fetchToolLogs();
        
        // Set up periodic refresh (every 5 seconds)
        setInterval(fetchToolLogs, 5000);
    }
});
