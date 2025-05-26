// Tool details data
const toolDetailsData = {
    getDateAndTimeTool: {
        description: "Get information about the current date and time. This tool provides accurate date and time information including timezone details.",
        sampleInput: `{}`,
        sampleOutput: `{
  "date": "2025-05-26",
  "time": "06:50:58",
  "day": "Monday",
  "timezone": "UTC",
  "unix_timestamp": 1748427458
}`
    },
    trackOrderTool: {
        description: "Retrieves real-time order tracking information and detailed status updates for customer orders by order ID. Provides estimated delivery dates.",
        sampleInput: `{
  "orderId": "ORD-12345-ABCDE",
  "requestNotifications": true
}`,
        sampleOutput: `{
  "orderId": "ORD-12345-ABCDE",
  "status": "in_transit",
  "statusDescription": "Your package is on the way",
  "estimatedDelivery": "2025-05-28",
  "currentLocation": "Distribution Center, New York",
  "trackingHistory": [
    {
      "timestamp": "2025-05-25T14:30:00Z",
      "status": "shipped",
      "location": "Warehouse, Chicago"
    },
    {
      "timestamp": "2025-05-26T03:15:00Z",
      "status": "in_transit",
      "location": "Distribution Center, New York"
    }
  ],
  "notificationsEnabled": true
}`
    },
    getWeatherTool: {
        description: "Get current weather information for a specified location. Provides temperature, conditions, and forecast data.",
        sampleInput: `{
  "location": "San Francisco",
  "unit": "celsius"
}`,
        sampleOutput: `{
  "location": "San Francisco, CA",
  "temperature": 18,
  "unit": "celsius",
  "condition": "Partly Cloudy",
  "humidity": 72,
  "wind": {
    "speed": 12,
    "direction": "W"
  },
  "forecast": [
    {
      "day": "Tuesday",
      "condition": "Sunny",
      "high": 21,
      "low": 14
    },
    {
      "day": "Wednesday",
      "condition": "Cloudy",
      "high": 19,
      "low": 13
    }
  ]
}`
    },
    getMoodSuggestionTool: {
        description: "Get personalized suggestions to improve mood or emotional state based on your current feelings.",
        sampleInput: `{
  "currentMood": "stressed",
  "intensity": "moderate"
}`,
        sampleOutput: `{
  "mood": "stressed",
  "intensity": "moderate",
  "suggestions": [
    "Take a 15-minute walk outside",
    "Practice deep breathing exercises",
    "Listen to calming music"
  ],
  "generalAdvice": "Taking small breaks can significantly reduce overall stress levels."
}`
    },
    searchTool: {
        description: "Search the internet for real-time information and answers to questions. Uses the Exa API to find accurate and up-to-date information.",
        sampleInput: `{
  "query": "What is the latest valuation of SpaceX?"
}`,
        sampleOutput: `{
  "answer": "$350 billion.",
  "citations": [
    {
      "title": "SpaceX valued at $350bn as company agrees to buy shares from employees",
      "url": "https://www.theguardian.com/science/2024/dec/11/spacex-valued-at-350bn-as-company-agrees-to-buy-shares-from-employees",
      "publishedDate": "2023-11-16T01:36:32.547Z"
    }
  ],
  "status": "success"
}`
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const toolItems = document.querySelectorAll('.tool-item');
    const toolDetailsModal = document.getElementById('toolDetailsModal');
    const closeToolDetailsModal = document.getElementById('closeToolDetailsModal');
    const modalToolTitle = document.getElementById('modalToolTitle');
    const toolDescription = document.getElementById('toolDescription');
    const toolSampleInput = document.getElementById('toolSampleInput');
    const toolSampleOutput = document.getElementById('toolSampleOutput');
    
    // Tool names mapping for display
    const toolDisplayNames = {
        getDateAndTimeTool: 'Date and Time Tool',
        trackOrderTool: 'Order Tracking Tool',
        getWeatherTool: 'Weather Tool',
        getMoodSuggestionTool: 'Mood Suggestion Tool',
        searchTool: 'Internet Search Tool'
    };
    
    // Function to show tool details modal
    function showToolDetailsModal(toolName) {
        const toolData = toolDetailsData[toolName];
        
        if (toolData) {
            // Update the modal title
            modalToolTitle.textContent = toolDisplayNames[toolName] || 'Tool Details';
            
            // Update the details content
            toolDescription.textContent = toolData.description;
            toolSampleInput.textContent = toolData.sampleInput;
            toolSampleOutput.textContent = toolData.sampleOutput;
            
            // Show the modal
            toolDetailsModal.classList.add('active');
            
            // Mark the selected tool as active
            toolItems.forEach(item => {
                if (item.dataset.tool === toolName) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
        }
    }
    
    // Add click event listeners to tool items
    toolItems.forEach(item => {
        item.addEventListener('click', () => {
            const toolName = item.dataset.tool;
            showToolDetailsModal(toolName);
        });
    });
    
    // Close modal when clicking the close button
    closeToolDetailsModal.addEventListener('click', () => {
        toolDetailsModal.classList.remove('active');
        toolItems.forEach(item => item.classList.remove('active'));
    });
    
    // Close modal when clicking outside the modal content
    toolDetailsModal.addEventListener('click', (event) => {
        if (event.target === toolDetailsModal) {
            toolDetailsModal.classList.remove('active');
            toolItems.forEach(item => item.classList.remove('active'));
        }
    });
    
    // Close modal with escape key
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && toolDetailsModal.classList.contains('active')) {
            toolDetailsModal.classList.remove('active');
            toolItems.forEach(item => item.classList.remove('active'));
        }
    });
});
