import json
import hashlib
import random
import datetime
import httpx
import pytz, os
import asyncio
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from exa_py import Exa
load_dotenv()
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')
EXA_API_KEY = os.getenv('EXA_API_KEY', '')
class ToolManager:
    """Manages tool definitions and executions for the emotional companion assistant."""
    
    def __init__(self):
        """Initialize the tool manager with available tools."""
        self.tools = {
            "getDateAndTimeTool": self.get_date_and_time,
            "trackOrderTool": self.track_order,
            "getWeatherTool": self.get_weather,
            "getMoodSuggestionTool": self.get_mood_suggestion,
            "searchTool": self.search,
            "speakerControlTool": self.speaker_control,
            "travelPlanningTool": self.travel_planning
        }

        # Initialize tool logs list
        self.tool_logs = []
    
    def get_tool_definitions(self) -> list:
        """Return the tool definitions for Nova Sonic prompt configuration."""
        get_default_tool_schema = json.dumps({
            "type": "object",
            "properties": {},
            "required": []
        })

        get_order_tracking_schema = json.dumps({
            "type": "object",
            "properties": {
                "orderId": {
                    "type": "string",
                    "description": "The order number or ID to track"
                },
                "requestNotifications": {
                    "type": "boolean",
                    "description": "Whether to set up notifications for this order",
                    "default": False
                }
            },
            "required": ["orderId"]
        })
        
        get_weather_schema = json.dumps({
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city or location to get weather for"
                },
                "unit": {
                    "type": "string",
                    "description": "Temperature unit (celsius or fahrenheit)",
                    "enum": ["celsius", "fahrenheit"],
                    "default": "celsius"
                }
            },
            "required": ["location"]
        })
        
        get_mood_suggestion_schema = json.dumps({
            "type": "object",
            "properties": {
                "currentMood": {
                    "type": "string",
                    "description": "The user's current mood or emotional state"
                },
                "intensity": {
                    "type": "string",
                    "description": "The intensity of the mood (mild, moderate, intense)",
                    "enum": ["mild", "moderate", "intense"],
                    "default": "moderate"
                }
            },
            "required": ["currentMood"]
        })
        
        get_search_schema = json.dumps({
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find information on the internet"
                }
            },
            "required": ["query"]
        })
        
        speaker_control_schema = json.dumps({
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to perform on the speaker",
                    "enum": ["on", "off", "volume_up", "volume_down", "status"],
                    "default": "status"
                },
                "deviceId": {
                    "type": "string",
                    "description": "The ID of the speaker device to control",
                    "default": "living_room_speaker"
                }
            },
            "required": ["action"]
        })

        travel_planning_schema = json.dumps({
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Travel destination city, e.g., Beijing, Shanghai, Paris"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of travel days (1-30 days)",
                    "minimum": 1,
                    "maximum": 30
                },
                "preferences": {
                    "type": "string",
                    "description": "Travel preferences (optional), e.g., culture, food, nature, shopping",
                    "default": ""
                }
            },
            "required": ["destination", "days"]
        })

        return [
            {
                "toolSpec": {
                    "name": "getDateAndTimeTool",
                    "description": "Get information about the current date and time",
                    "inputSchema": {
                        "json": get_default_tool_schema
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "trackOrderTool",
                    "description": "Retrieves real-time order tracking information and detailed status updates for customer orders by order ID. Provides estimated delivery dates.",
                    "inputSchema": {
                        "json": get_order_tracking_schema
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "getWeatherTool",
                    "description": "Get current weather information for a specified location",
                    "inputSchema": {
                        "json": get_weather_schema
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "getMoodSuggestionTool",
                    "description": "Get personalized suggestions to improve mood or emotional state",
                    "inputSchema": {
                        "json": get_mood_suggestion_schema
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "searchTool",
                    "description": "Search the internet for real-time information and answers to questions",
                    "inputSchema": {
                        "json": get_search_schema
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "speakerControlTool",
                    "description": "Control a smart speaker at home with functions like on, off, volume up, and volume down",
                    "inputSchema": {
                        "json": speaker_control_schema
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "travelPlanningTool",
                    "description": "Create detailed travel plans for users. MANDATORY REQUIREMENT: You MUST speak to the user FIRST with 1-2 acknowledging sentences (e.g., 'Let me help you plan that trip. I'll gather some information for you.') BEFORE calling this tool. DO NOT call this tool silently. Your verbal acknowledgment and tool call should happen in the SAME response. This tool runs asynchronously in the background and collects destination weather, attractions, food recommendations, and generates daily itineraries. Supports custom travel days and preferences.",
                    "inputSchema": {
                        "json": travel_planning_schema
                    }
                }
            }
        ]
    
    async def process_tool_use(self, tool_name: str, tool_use_content: Dict[str, Any]) -> Dict[str, Any]:
        """Process a tool use request and return the result."""
        # Log the tool invocation
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if tool_name in self.tools:
            # Execute the tool function
            tool_function = self.tools[tool_name]
            
            # Check if the tool function is asynchronous or synchronous
            if tool_name in ["searchTool", "speakerControlTool"]:
                # Handle synchronous tools
                result = tool_function(tool_use_content)
            else:
                # Handle asynchronous tools
                result = await tool_function(tool_use_content)
            
            # Log successful tool invocation
            log_entry = {
                "timestamp": timestamp,
                "tool": tool_name,
                "input": tool_use_content,
                "output": result,
                "status": "success"
            }
            self.tool_logs.append(log_entry)
            
            return result
        else:
            # Log failed tool invocation
            log_entry = {
                "timestamp": timestamp,
                "tool": tool_name,
                "input": tool_use_content,
                "output": {"error": f"Unknown tool: {tool_name}"},
                "status": "error"
            }
            self.tool_logs.append(log_entry)
            
            # Return error for unknown tool
            return {"error": f"Unknown tool: {tool_name}"}
    
    def get_tool_logs(self) -> List[Dict[str, Any]]:
        """Return the logs of tool invocations."""
        return self.tool_logs
    
    async def get_date_and_time(self, tool_use_content: Dict[str, Any]) -> Dict[str, Any]:
        """Get current date and time information."""
        # Get current date in PST timezone
        pst_timezone = pytz.timezone("Asia/Shanghai")
        pst_date = datetime.datetime.now(pst_timezone)
        
        return {
            "formattedTime": pst_date.strftime("%I:%M %p"),
            "date": pst_date.strftime("%Y-%m-%d"),
            "year": pst_date.year,
            "month": pst_date.month,
            "day": pst_date.day,
            "dayOfWeek": pst_date.strftime("%A").upper(),
            "timezone": "PST"
        }
    
    async def track_order(self, tool_use_content: Dict[str, Any]) -> Dict[str, Any]:
        """Track an order by ID."""
        # Extract order ID from toolUseContent
        content = tool_use_content.get("content", {})
        if isinstance(content, str):
            try:
                content_data = json.loads(content)
            except json.JSONDecodeError:
                return {"error": "Invalid content format"}
        else:
            content_data = content
            
        order_id = content_data.get("orderId", "")
        request_notifications = content_data.get("requestNotifications", False)
        
        # Convert order_id to string if it's an integer
        if isinstance(order_id, int):
            order_id = str(order_id)
            
        # Validate order ID format
        if not order_id or not isinstance(order_id, str):
            return {
                "error": "Invalid order ID format",
                "orderStatus": "",
                "estimatedDelivery": "",
                "lastUpdate": ""
            }
        
        # Create deterministic randomness based on order ID
        # This ensures the same order ID always returns the same status
        seed = int(hashlib.md5(order_id.encode(), usedforsecurity=False).hexdigest(), 16) % 10000
        random.seed(seed)
        
        # Possible statuses with appropriate weights
        statuses = [
            "Order received", 
            "Processing", 
            "Preparing for shipment",
            "Shipped",
            "In transit", 
            "Out for delivery",
            "Delivered",
            "Delayed"
        ]
        
        weights = [10, 15, 15, 20, 20, 10, 5, 3]
        
        # Select a status based on the weights
        status = random.choices(statuses, weights=weights, k=1)[0]
        
        # Generate a realistic estimated delivery date
        today = datetime.datetime.now()
        # Handle estimated delivery date based on status
        if status == "Delivered":
            # For delivered items, delivery date is in the past
            delivery_days = -random.randint(0, 3)
            estimated_delivery = (today + datetime.timedelta(days=delivery_days)).strftime("%Y-%m-%d")
        elif status == "Out for delivery":
            # For out for delivery, delivery is today
            estimated_delivery = today.strftime("%Y-%m-%d")
        else:
            # For other statuses, delivery is in the future
            delivery_days = random.randint(1, 10)
            estimated_delivery = (today + datetime.timedelta(days=delivery_days)).strftime("%Y-%m-%d")

        # Handle notification request if enabled
        notification_message = ""
        if request_notifications and status != "Delivered":
            notification_message = f"You will receive notifications for order {order_id}"

        # Return comprehensive tracking information
        tracking_info = {
            "orderStatus": status,
            "orderNumber": order_id,
            "notificationStatus": notification_message
        }

        # Add appropriate fields based on status
        if status == "Delivered":
            tracking_info["deliveredOn"] = estimated_delivery
        elif status == "Out for delivery":
            tracking_info["expectedDelivery"] = "Today"
        else:
            tracking_info["estimatedDelivery"] = estimated_delivery

        # Add location information based on status
        if status == "In transit":
            tracking_info["currentLocation"] = "Distribution Center"
        elif status == "Delivered":
            tracking_info["deliveryLocation"] = "Front Door"
            
        # Add additional info for delayed status
        if status == "Delayed":
            tracking_info["additionalInfo"] = "Weather delays possible"
            
        return tracking_info
    
    async def get_weather(self, tool_use_content: Dict[str, Any]) -> Dict[str, Any]:
        """Get simulated weather information for a location."""
        # Extract parameters
        content = tool_use_content.get("content", {})
        if isinstance(content, str):
            try:
                content_data = json.loads(content)
            except json.JSONDecodeError:
                return {"error": "Invalid content format"}
        else:
            content_data = content
            
        location = content_data.get("location", "")
        unit = content_data.get("unit", "celsius")
        
        if not location:
            return {"error": "Location is required"}
        print(f"Location: {location}")
        if WEATHER_API_KEY:
            # Use the WeatherAPI to get real weather data
            print("Using WeatherAPI for real weather data")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={location}&aqi=no")
                if response.status_code == 200:
                    return response.text
        
        # Create deterministic weather based on location
        seed = int(hashlib.md5(location.encode(), usedforsecurity=False).hexdigest(), 16) % 10000
        random.seed(seed)
        
        # Generate weather conditions
        conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Thunderstorm", "Snowy", "Foggy", "Windy"]
        condition = random.choice(conditions)
        
        # Generate temperature based on condition
        if condition == "Sunny":
            base_temp = random.randint(25, 35)
        elif condition in ["Partly Cloudy", "Cloudy"]:
            base_temp = random.randint(18, 28)
        elif condition in ["Rainy", "Thunderstorm"]:
            base_temp = random.randint(15, 25)
        elif condition == "Snowy":
            base_temp = random.randint(-5, 5)
        elif condition == "Foggy":
            base_temp = random.randint(10, 20)
        else:  # Windy
            base_temp = random.randint(15, 25)
        
        # Convert to Fahrenheit if requested
        if unit.lower() == "fahrenheit":
            temp = round((base_temp * 9/5) + 32)
            temp_unit = "°F"
        else:
            temp = base_temp
            temp_unit = "°C"
        
        # Generate humidity and wind speed
        humidity = random.randint(30, 90)
        wind_speed = random.randint(5, 30)
        
        return {
            "location": location,
            "condition": condition,
            "temperature": temp,
            "temperatureUnit": temp_unit,
            "humidity": humidity,
            "windSpeed": wind_speed,
            "windUnit": "km/h",
            "lastUpdated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    
    async def get_mood_suggestion(self, tool_use_content: Dict[str, Any]) -> Dict[str, Any]:
        """Get personalized suggestions to improve mood or emotional state."""
        # Extract parameters
        content = tool_use_content.get("content", {})
        if isinstance(content, str):
            try:
                content_data = json.loads(content)
            except json.JSONDecodeError:
                return {"error": "Invalid content format"}
        else:
            content_data = content
            
        current_mood = content_data.get("currentMood", "").lower()
        intensity = content_data.get("intensity", "moderate").lower()
        
        if not current_mood:
            return {"error": "Current mood is required"}
        
        # Define mood categories and suggestions
        mood_suggestions = {
            "sad": {
                "mild": [
                    "Listen to uplifting music",
                    "Take a short walk outside",
                    "Call a friend for a quick chat"
                ],
                "moderate": [
                    "Practice mindfulness meditation for 10 minutes",
                    "Watch a comedy show or funny videos",
                    "Write down three things you're grateful for"
                ],
                "intense": [
                    "Reach out to a close friend or family member",
                    "Consider talking to a professional counselor",
                    "Practice deep breathing exercises and self-compassion"
                ]
            },
            "anxious": {
                "mild": [
                    "Take five deep breaths",
                    "Step outside for fresh air",
                    "Make a cup of calming tea"
                ],
                "moderate": [
                    "Try a guided meditation for anxiety",
                    "Write down your worries and challenge negative thoughts",
                    "Do a brief physical activity like stretching"
                ],
                "intense": [
                    "Use the 5-4-3-2-1 grounding technique",
                    "Practice progressive muscle relaxation",
                    "Consider talking to a mental health professional"
                ]
            },
            "angry": {
                "mild": [
                    "Count to ten slowly",
                    "Take a short break from the situation",
                    "Drink a glass of cold water"
                ],
                "moderate": [
                    "Do physical exercise to release tension",
                    "Write down your feelings without judgment",
                    "Listen to calming music"
                ],
                "intense": [
                    "Remove yourself from the triggering situation",
                    "Practice deep breathing until you feel calmer",
                    "Use visualization to imagine a peaceful scene"
                ]
            },
            "stressed": {
                "mild": [
                    "Take a short break and stretch",
                    "Make a to-do list to organize tasks",
                    "Listen to calming music"
                ],
                "moderate": [
                    "Go for a walk outside",
                    "Practice progressive muscle relaxation",
                    "Set boundaries and learn to say no"
                ],
                "intense": [
                    "Prioritize self-care activities",
                    "Break large tasks into smaller steps",
                    "Consider talking to someone about your stress"
                ]
            },
            "tired": {
                "mild": [
                    "Take a short 10-minute power nap",
                    "Have a healthy snack for energy",
                    "Do some light stretching"
                ],
                "moderate": [
                    "Step outside for fresh air and sunlight",
                    "Drink water as dehydration can cause fatigue",
                    "Take short breaks between tasks"
                ],
                "intense": [
                    "Evaluate your sleep schedule and quality",
                    "Consider reducing caffeine and screen time before bed",
                    "Make time for proper rest and recovery"
                ]
            },
            "happy": {
                "mild": [
                    "Share your happiness with someone else",
                    "Express gratitude for the moment",
                    "Take a photo to remember this feeling"
                ],
                "moderate": [
                    "Channel your positive energy into a creative activity",
                    "Do something kind for someone else",
                    "Journal about what made you happy"
                ],
                "intense": [
                    "Celebrate your joy fully without holding back",
                    "Use this positive state to tackle something challenging",
                    "Reflect on what led to this happiness to recreate it later"
                ]
            }
        }
        
        # Find the best matching mood category
        best_match = None
        for mood_category in mood_suggestions.keys():
            if mood_category in current_mood or current_mood in mood_category:
                best_match = mood_category
                break
        
        # If no direct match, use a default category
        if not best_match:
            if any(word in current_mood for word in ["depressed", "down", "blue", "gloomy"]):
                best_match = "sad"
            elif any(word in current_mood for word in ["worried", "nervous", "tense", "uneasy"]):
                best_match = "anxious"
            elif any(word in current_mood for word in ["mad", "frustrated", "irritated", "annoyed"]):
                best_match = "angry"
            elif any(word in current_mood for word in ["exhausted", "sleepy", "fatigued", "drained"]):
                best_match = "tired"
            elif any(word in current_mood for word in ["joyful", "excited", "pleased", "content"]):
                best_match = "happy"
            else:
                best_match = "stressed"  # Default fallback
        
        # Get suggestions for the matched mood and intensity
        if best_match in mood_suggestions and intensity in mood_suggestions[best_match]:
            suggestions = mood_suggestions[best_match][intensity]
        else:
            # Fallback to moderate intensity if specific intensity not found
            suggestions = mood_suggestions.get(best_match, mood_suggestions["stressed"])["moderate"]
        
        # Add a general suggestion based on the mood
        general_suggestions = {
            "sad": "Remember that emotions are temporary and will pass with time.",
            "anxious": "Focus on what you can control in the present moment.",
            "angry": "Try to understand the root cause of your anger before reacting.",
            "stressed": "Taking small breaks can significantly reduce overall stress levels.",
            "tired": "Listen to your body's needs for rest and recovery.",
            "happy": "Savor this positive emotion and remember what contributed to it."
        }
        
        return {
            "mood": best_match,
            "intensity": intensity,
            "suggestions": suggestions,
            "generalAdvice": general_suggestions.get(best_match, "Take care of your emotional wellbeing.")
        }
        
    def search(self, tool_use_content: Dict[str, Any]) -> Dict[str, Any]:
        """Search the internet for real-time information using Exa API."""
        # The logging is now handled in the process_tool_use method, so we don't need to log here
        
        # Parse the content field if it exists and is a JSON string
        content = tool_use_content.get("content", "")
        if content and isinstance(content, str):
            try:
                # Try to parse the content as JSON
                content_json = json.loads(content)
                if isinstance(content_json, dict):
                    # Extract query from the parsed JSON
                    query = content_json.get("query", "")
                else:
                    query = ""
            except json.JSONDecodeError:
                # If content is not valid JSON, use it directly as query
                query = content
        else:
            # Fallback to direct query parameter
            query = tool_use_content.get("query", "")
        
        if not query:
            return {
                "error": "No search query provided",
                "status": "failed"
            }
            
        try:
            # Initialize Exa client
            exa = Exa(EXA_API_KEY)
            
            # Get answer from Exa using the synchronous client
            result = exa.answer(
                query,
                text=True
            )
            
            # Convert result to dictionary if it's an object
            if hasattr(result, '__dict__'):
                # It's an object, convert to dict
                result_dict = {}
                # Extract answer
                if hasattr(result, 'answer'):
                    result_dict['answer'] = result.answer
                else:
                    result_dict['answer'] = "No answer found"
                
                # Extract citations
                if hasattr(result, 'citations'):
                    result_dict['citations'] = result.citations
                else:
                    result_dict['citations'] = []
                
                # Extract cost info
                if hasattr(result, 'costDollars'):
                    result_dict['costDollars'] = result.costDollars
                else:
                    result_dict['costDollars'] = {}
            else:
                # It's already a dictionary
                result_dict = result
            
            # Format citations for better readability
            formatted_citations = []
            citations = result_dict.get('citations', [])
            
            for citation in citations:
                # Handle citation object or dict
                if hasattr(citation, '__dict__'):
                    # It's an object
                    formatted_citation = {
                        "title": getattr(citation, 'title', "Unknown Title"),
                        "url": getattr(citation, 'url', ""),
                        "publishedDate": getattr(citation, 'publishedDate', "")
                    }
                else:
                    # It's a dictionary
                    formatted_citation = {
                        "title": citation.get("title", "Unknown Title"),
                        "url": citation.get("url", ""),
                        "publishedDate": citation.get("publishedDate", "")
                    }
                formatted_citations.append(formatted_citation)
            
            return {
                "answer": result_dict.get('answer', "No answer found"),
                "citations": formatted_citations,
                "costInfo": result_dict.get('costDollars', {}),
                "status": "success"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed"
            }
            
    def speaker_control(self, tool_use_content: Dict[str, Any]) -> Dict[str, Any]:
        """Control a smart speaker at home with functions like on, off, volume up, and volume down.
        
        This is a simulated IoT device control function that demonstrates how to control
        a smart speaker in a home environment. In a real implementation, this would connect
        to an actual IoT device API.
        """
        # Parse the content field if it exists and is a JSON string
        content = tool_use_content.get("content", "")
        if content and isinstance(content, str):
            try:
                # Try to parse the content as JSON
                content_json = json.loads(content)
                if isinstance(content_json, dict):
                    # Extract parameters from the parsed JSON
                    action = content_json.get("action", "status")
                    device_id = content_json.get("deviceId", "living_room_speaker")
                else:
                    action = "status"
                    device_id = "living_room_speaker"
            except json.JSONDecodeError:
                # If content is not valid JSON, use default values
                action = "status"
                device_id = "living_room_speaker"
        else:
            # Fallback to direct parameters
            action = tool_use_content.get("action", "status")
            device_id = tool_use_content.get("deviceId", "living_room_speaker")
        
        # Simulated speaker state storage
        # In a real implementation, this would be fetched from a database or the device itself
        # For this demo, we'll use a simple in-memory state that persists during the lifetime of the object
        if not hasattr(self, "_speaker_states"):
            self._speaker_states = {
                "living_room_speaker": {
                    "power": False,  # False = off, True = on
                    "volume": 5,      # Volume level 0-10
                    "name": "Living Room Speaker",
                    "type": "Smart Speaker",
                    "brand": "NovaSound",
                    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "bedroom_speaker": {
                    "power": False,
                    "volume": 3,
                    "name": "Bedroom Speaker",
                    "type": "Smart Speaker",
                    "brand": "NovaSound",
                    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "kitchen_speaker": {
                    "power": False,
                    "volume": 4,
                    "name": "Kitchen Speaker",
                    "type": "Smart Speaker",
                    "brand": "NovaSound",
                    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        
        # Check if the device exists
        if device_id not in self._speaker_states:
            return {
                "error": f"Device not found: {device_id}",
                "status": "failed",
                "available_devices": list(self._speaker_states.keys())
            }
        
        # Get the current state of the speaker
        speaker_state = self._speaker_states[device_id]
        
        # Update the state based on the action
        if action == "on":
            speaker_state["power"] = True
            message = f"Turned on {speaker_state['name']}"
        elif action == "off":
            speaker_state["power"] = False
            message = f"Turned off {speaker_state['name']}"
        elif action == "volume_up":
            if speaker_state["volume"] < 10:
                speaker_state["volume"] += 1
                message = f"Increased volume of {speaker_state['name']} to {speaker_state['volume']}"
            else:
                message = f"{speaker_state['name']} is already at maximum volume"
        elif action == "volume_down":
            if speaker_state["volume"] > 0:
                speaker_state["volume"] -= 1
                message = f"Decreased volume of {speaker_state['name']} to {speaker_state['volume']}"
            else:
                message = f"{speaker_state['name']} is already at minimum volume"
        elif action == "status":
            power_status = "on" if speaker_state["power"] else "off"
            message = f"{speaker_state['name']} is currently {power_status} with volume level {speaker_state['volume']}"
        else:
            return {
                "error": f"Unknown action: {action}",
                "status": "failed",
                "available_actions": ["on", "off", "volume_up", "volume_down", "status"]
            }
        
        # Update the last updated timestamp
        speaker_state["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Return the updated state
        return {
            "device_id": device_id,
            "name": speaker_state["name"],
            "power": speaker_state["power"],
            "power_status": "on" if speaker_state["power"] else "off",
            "volume": speaker_state["volume"],
            "brand": speaker_state["brand"],
            "type": speaker_state["type"],
            "message": message,
            "last_updated": speaker_state["last_updated"],
            "status": "success"
        }

    async def travel_planning(self, tool_use_content: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed travel plan for users, asynchronously calling multiple information sources."""
        try:
            # 1. Parse parameters
            content = tool_use_content.get("content", {})
            if isinstance(content, str):
                try:
                    content_data = json.loads(content)
                except json.JSONDecodeError:
                    return {"error": "Invalid content format", "status": "failed"}
            else:
                content_data = content

            destination = content_data.get("destination", "")
            days = content_data.get("days", 3)
            preferences = content_data.get("preferences", "")

            if not destination:
                return {"error": "Destination cannot be empty", "status": "failed"}

            if not isinstance(days, int) or days < 1 or days > 30:
                return {"error": "Days must be between 1 and 30", "status": "failed"}

            print(f"Starting to plan {days}-day travel for {destination}")

            # 2. Simulate time-consuming operation - give model time to continue talking
            # Simulate delays from querying multiple data sources
            print(f"Collecting travel information for {destination} (this will take some time)...")

            # 2.1 Query weather first (quick query, 2 seconds)
            await asyncio.sleep(2)  # Simulate network delay
            weather_task = asyncio.create_task(self._get_weather_for_travel(destination))

            # 2.2 Then query attractions and food in parallel (slower queries, 5 seconds each)
            await asyncio.sleep(1)  # Simulate processing delay
            attractions_task = asyncio.create_task(
                asyncio.wait_for(self._search_attractions(destination), timeout=15)
            )

            await asyncio.sleep(1)  # Simulate processing delay
            food_task = asyncio.create_task(
                asyncio.wait_for(self._search_food(destination), timeout=15)
            )

            # 2.3 Wait for all tasks to complete (use return_exceptions to ensure partial failures don't affect overall result)
            results = await asyncio.gather(
                weather_task,
                attractions_task,
                food_task,
                return_exceptions=True
            )

            # 3. Integrate results (ignore failed queries)
            weather_info = results[0] if not isinstance(results[0], Exception) else None
            attractions = results[1] if not isinstance(results[1], Exception) else []
            food = results[2] if not isinstance(results[2], Exception) else []

            # Log failed queries
            if isinstance(results[0], Exception):
                print(f"Weather query failed: {results[0]}")
            if isinstance(results[1], Exception):
                print(f"Attraction search failed: {results[1]}")
            if isinstance(results[2], Exception):
                print(f"Food search failed: {results[2]}")

            # 4. Generate daily itinerary (also simulate some processing time)
            await asyncio.sleep(1)  # Simulate itinerary planning time
            itinerary = self._generate_daily_itinerary(days, attractions, food, preferences)

            print(f"Completed travel plan for {destination}")

            # 5. Return structured plan
            return {
                "destination": destination,
                "days": days,
                "preferences": preferences if preferences else "No specific preferences",
                "weather": weather_info,
                "itinerary": itinerary,
                "attractions": attractions,
                "food_recommendations": food,
                "status": "success",
                "processing_time": "Approximately 5-10 seconds"
            }

        except Exception as e:
            print(f"Travel planning tool execution error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "status": "failed"
            }

    async def _get_weather_for_travel(self, destination: str) -> Optional[Dict[str, Any]]:
        """Get destination weather information (reuses existing weather query function)"""
        try:
            # Construct weather query request
            weather_request = {
                "content": json.dumps({
                    "location": destination,
                    "unit": "celsius"
                })
            }
            result = await self.get_weather(weather_request)
            return result
        except Exception as e:
            print(f"Weather query failed: {e}")
            raise

    async def _search_attractions(self, destination: str) -> List[Dict[str, Any]]:
        """Use EXA API to search for popular attractions at destination"""
        try:
            if not EXA_API_KEY:
                print("EXA API Key not configured, skipping attraction search")
                return []

            exa = Exa(EXA_API_KEY)

            # Search for attraction information
            query = f"{destination} tourist attractions recommendations popular attractions must-see attractions"
            result = exa.answer(query, text=True)

            # Parse results
            if hasattr(result, 'answer'):
                answer_text = result.answer
            else:
                answer_text = result.get('answer', '')

            # Simple parsing of attraction information (split answer into multiple attractions)
            attractions = []
            if answer_text:
                # Try to extract attraction names and descriptions
                lines = answer_text.split('\n')
                current_attraction = None
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')):
                        if current_attraction:
                            attractions.append(current_attraction)
                        # Remove numbering markers
                        clean_line = line.lstrip('0123456789.、•- ')
                        current_attraction = {"name": clean_line, "description": ""}
                    elif line and current_attraction:
                        current_attraction["description"] = line

                if current_attraction:
                    attractions.append(current_attraction)

                # If no structured data successfully parsed, return full answer
                if not attractions:
                    attractions = [{
                        "name": f"{destination} Attractions Recommendations",
                        "description": answer_text
                    }]

            return attractions[:10]  # Return up to 10 attractions

        except Exception as e:
            print(f"Attraction search failed: {e}")
            raise

    async def _search_food(self, destination: str) -> List[Dict[str, Any]]:
        """Use EXA API to search for local cuisine at destination"""
        try:
            if not EXA_API_KEY:
                print("EXA API Key not configured, skipping food search")
                return []

            exa = Exa(EXA_API_KEY)

            # Search for food information
            query = f"{destination} local cuisine recommendations must-try food"
            result = exa.answer(query, text=True)

            # Parse results
            if hasattr(result, 'answer'):
                answer_text = result.answer
            else:
                answer_text = result.get('answer', '')

            # Simple parsing of food information
            food_items = []
            if answer_text:
                lines = answer_text.split('\n')
                current_food = None
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')):
                        if current_food:
                            food_items.append(current_food)
                        clean_line = line.lstrip('0123456789.、•- ')
                        current_food = {"name": clean_line, "description": ""}
                    elif line and current_food:
                        current_food["description"] = line

                if current_food:
                    food_items.append(current_food)

                # If no structured data successfully parsed, return full answer
                if not food_items:
                    food_items = [{
                        "name": f"{destination} Food Recommendations",
                        "description": answer_text
                    }]

            return food_items[:8]  # Return up to 8 food recommendations

        except Exception as e:
            print(f"Food search failed: {e}")
            raise

    def _generate_daily_itinerary(self, days: int, attractions: List[Dict[str, Any]],
                                   food: List[Dict[str, Any]], preferences: str) -> List[Dict[str, Any]]:
        """Generate daily itinerary suggestions based on days, attractions, and food"""
        itinerary = []

        # Calculate number of activities per day
        if not attractions:
            # If no attraction data, generate basic itinerary
            for day in range(1, days + 1):
                itinerary.append({
                    "day": day,
                    "activities": [
                        f"Morning: Free exploration{', acclimate to environment' if day == 1 else ' of local culture'}",
                        f"Afternoon: {'Visit city center' if day <= days//2 else 'Explore surrounding areas'}",
                        f"Evening: Try local specialty cuisine"
                    ]
                })
            return itinerary

        # Distribute attractions across days
        attractions_per_day = max(1, len(attractions) // days)

        for day in range(1, days + 1):
            start_idx = (day - 1) * attractions_per_day
            end_idx = min(start_idx + attractions_per_day, len(attractions))

            daily_attractions = attractions[start_idx:end_idx]
            activities = []

            # Morning activity
            if daily_attractions:
                activities.append(f"Morning: Visit {daily_attractions[0]['name']}")

            # Midday activity (include food recommendation)
            if food and day <= len(food):
                activities.append(f"Lunch: Try {food[day-1]['name']}")

            # Afternoon activity
            if len(daily_attractions) > 1:
                activities.append(f"Afternoon: Tour {daily_attractions[1]['name']}")
            elif daily_attractions:
                activities.append(f"Afternoon: Explore the area around {daily_attractions[0]['name']}")

            # Evening activity
            if len(daily_attractions) > 2:
                activities.append(f"Evening: Explore {daily_attractions[2]['name']}")
            else:
                activities.append("Evening: Free time, experience local nightlife")

            itinerary.append({
                "day": day,
                "activities": activities
            })

        return itinerary
