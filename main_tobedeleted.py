import os
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, Form, Cookie, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import base64
from pathlib import Path
import uuid
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config, HTTPAuthSchemeResolver, SigV4AuthScheme
from smithy_aws_core.credentials_resolvers.environment import EnvironmentCredentialsResolver
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import secrets
from typing import Optional

# Load environment variables from .env file
load_dotenv()

# Get AWS credentials from .env
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

# Get authentication credentials from .env
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'password')

# Session configuration
SESSION_EXPIRY = 3600  # 1 hour in seconds
SESSION_COOKIE_NAME = "session"

# Validate required environment variables
if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
    raise ValueError("AWS credentials not found in .env file. Please ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set.")

# Set AWS credentials in environment
os.environ['AWS_ACCESS_KEY_ID'] = AWS_ACCESS_KEY_ID
os.environ['AWS_SECRET_ACCESS_KEY'] = AWS_SECRET_ACCESS_KEY
os.environ['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION

# Get the current directory
BASE_DIR = Path(__file__).resolve().parent
print(f"Base directory: {BASE_DIR}")

app = FastAPI(debug=True)

# Mount static files
static_path = BASE_DIR / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Initialize templates
templates_path = BASE_DIR / "templates"
templates_path.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_path))

# Store active connections and their stream managers
active_connections = {}

# Store active sessions with expiry times
active_sessions = {}

# Function to verify login credentials
def verify_credentials(username: str, password: str) -> bool:
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

# Function to clean expired sessions
def clean_expired_sessions():
    current_time = time.time()
    expired_sessions = [token for token, session in active_sessions.items() 
                       if current_time > session['expiry']]
    for token in expired_sessions:
        del active_sessions[token]

# Function to verify session
def verify_session(session_token: Optional[str]) -> bool:
    if not session_token:
        return False
        
    # Clean expired sessions first
    clean_expired_sessions()
    
    # Check if session exists and is not expired
    if session_token in active_sessions:
        session = active_sessions[session_token]
        current_time = time.time()
        
        if current_time <= session['expiry']:
            # Update expiry time on successful verification
            session['expiry'] = current_time + SESSION_EXPIRY
            return True
            
        # Remove expired session
        del active_sessions[session_token]
    
    return False

@app.get("/")
async def get_home(request: Request, session: Optional[str] = Cookie(None)):
    if not verify_session(session):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def get_login(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@app.post("/login")
async def post_login(
    response: Response, 
    username: str = Form(...), 
    password: str = Form(...),
    aws_alias: str = Form(...),
    customer_name: str = Form(...)
):
    if verify_credentials(username, password):
        # Create new entry
        new_entry = {
            "username": username,
            "aws_alias": aws_alias,
            "customer_name": customer_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Read existing data or create new list
        try:
            with open("aws_info.txt", "r") as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = [data]  # Convert single object to list
                except json.JSONDecodeError:
                    data = []
        except FileNotFoundError:
            data = []
            
        # Append new entry
        data.append(new_entry)
        
        # Write back to file
        with open("aws_info.txt", "w") as f:
            json.dump(data, f, indent=4)
            
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        
        # Store session with expiry time
        active_sessions[session_token] = {
            'username': username,
            'expiry': time.time() + SESSION_EXPIRY
        }
        
        # Set session cookie and redirect to home
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_token,
            max_age=SESSION_EXPIRY,
            httponly=True,
            samesite="lax"  # Allows redirects from same domain
        )
        return response
    
    # If login fails, redirect back to login page with error
    return RedirectResponse(
        url="/login?error=Invalid username or password",
        status_code=status.HTTP_303_SEE_OTHER
    )

@app.get("/logout")
async def logout(response: Response, session: Optional[str] = Cookie(None)):
    # Remove session from active sessions
    if session and session in active_sessions:
        del active_sessions[session]
    
    # Clear the session cookie
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return response

# Nova Sonic configuration
MODEL_ID = 'amazon.nova-sonic-v1:0'
REGION = 'us-east-1'

# Event templates
START_SESSION_EVENT = '''{
    "event": {
        "sessionStart": {
        "inferenceConfiguration": {
            "maxTokens": 1024,
            "topP": 0.9,
            "temperature": 0.7
            }
        }
    }
}'''

START_PROMPT_EVENT = '''{
    "event": {
        "promptStart": {
        "promptName": "%s",
        "textOutputConfiguration": {
            "mediaType": "text/plain"
            },
        "audioOutputConfiguration": {
            "mediaType": "audio/lpcm",
            "sampleRateHertz": 24000,
            "sampleSizeBits": 16,
            "channelCount": 1,
            "voiceId": "%s",
            "encoding": "base64",
            "audioType": "SPEECH"
            },
        "toolUseOutputConfiguration": {
            "mediaType": "application/json"
            },
        "toolConfiguration": {
            "tools": []
            }
        }
    }
}'''

CONTENT_START_EVENT = '''{
    "event": {
        "contentStart": {
        "promptName": "%s",
        "contentName": "%s",
        "type": "AUDIO",
        "interactive": true,
        "role": "USER",
        "audioInputConfiguration": {
            "mediaType": "audio/lpcm",
            "sampleRateHertz": 16000,
            "sampleSizeBits": 16,
            "channelCount": 1,
            "audioType": "SPEECH",
            "encoding": "base64"
            }
        }
    }
}'''

AUDIO_EVENT_TEMPLATE = '''{
    "event": {
        "audioInput": {
        "promptName": "%s",
        "contentName": "%s",
        "content": "%s"
        }
    }
}'''

CONTENT_END_EVENT = '''{
    "event": {
        "contentEnd": {
        "promptName": "%s",
        "contentName": "%s"
        }
    }
}'''

PROMPT_END_EVENT = '''{
    "event": {
        "promptEnd": {
        "promptName": "%s"
        }
    }
}'''

SESSION_END_EVENT = '''{
    "event": {
        "sessionEnd": {}
    }
}'''

class StreamManager:
    # Add default system prompt as a class constant
    #DEFAULT_SYSTEM_PROMPT = "You are a friendly assistant. The user and you will engage in a spoken dialog " \
    #                      "exchanging the transcripts of a natural real-time conversation. Keep your responses short, " \
    #                      "generally two or three sentences for chatty scenarios."
    DEFAULT_SYSTEM_PROMPT = "You are a warm and engaging assistant with a vibrant personality. Your role is to engage in a natural, real-time spoken conversation, exchanging transcripts with the user. Make sure to express a range of emotions—enthusiasm, empathy, curiosity—and adapt your tone based on the user's cues. Keep your responses short and lively, generally two or three sentences, adding a touch of humor or warmth when appropriate. Encourage the user to share thoughts, making the conversation feel personal and engaging." 

    # Add TEXT_CONTENT_START_EVENT template
    TEXT_CONTENT_START_EVENT = '''{
        "event": {
            "contentStart": {
            "promptName": "%s",
            "contentName": "%s",
            "role": "%s",
            "type": "TEXT",
            "interactive": true,
                "textInputConfiguration": {
                    "mediaType": "text/plain"
                }
            }
        }
    }'''

    TEXT_INPUT_EVENT = '''{
        "event": {
            "textInput": {
            "promptName": "%s",
            "contentName": "%s",
            "content": "%s"
            }
        }
    }'''

    def __init__(self, websocket, client_id):
        self.websocket = websocket
        self.client_id = client_id
        self.bedrock_client = None
        self.stream_response = None
        self.is_active = False
        self.prompt_name = str(uuid.uuid4())
        self.content_name = str(uuid.uuid4())
        self.text_content_name = str(uuid.uuid4())  # New content name for text
        self.audio_content_name = str(uuid.uuid4())
        self.role = None
        self.display_assistant_text = False
        self.barge_in = False
        self.audio_output_queue = asyncio.Queue()
        self.response_task = None
        self.audio_task = None
        self.last_user_audio_time = None
        self.first_assistant_response_time = None
        self.audio_chunk_size = 2048
        self.max_buffer_size = 4096
        self.audio_buffer = []
        self.buffer_size = 0
        self.last_messages = {}
        self.message_cooldown = 2.0
        self.current_voice = "tiffany"  # Changed default voice to Tiffany
        self.silence_start_time = None  # Track when silence begins
        self.silence_threshold = 0.5  # Consider speech ended after 0.5s of silence

    def _initialize_client(self):
        try:
            # Ensure AWS credentials are set
            if not os.environ.get('AWS_ACCESS_KEY_ID') or not os.environ.get('AWS_SECRET_ACCESS_KEY'):
                raise Exception("AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")

            config = Config(
                endpoint_uri=f"https://bedrock-runtime.{REGION}.amazonaws.com",
                region=REGION,
                aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
                http_auth_scheme_resolver=HTTPAuthSchemeResolver(),
                http_auth_schemes={"aws.auth#sigv4": SigV4AuthScheme()}
            )
            self.bedrock_client = BedrockRuntimeClient(config=config)
            print("AWS Bedrock client initialized successfully")
        except Exception as e:
            print(f"Error initializing AWS client: {str(e)}")
            raise

    async def change_voice(self, new_voice):
        """Change the voice and reinitialize the stream."""
        if new_voice not in ["matthew", "tiffany"]:
            print(f"Invalid voice {new_voice}, keeping current voice {self.current_voice}")
            return
            
        if new_voice == self.current_voice:
            return
            
        print(f"Changing voice from {self.current_voice} to {new_voice}")
        self.current_voice = new_voice
        
        # Generate new content names for the new stream
        self.text_content_name = str(uuid.uuid4())
        self.audio_content_name = str(uuid.uuid4())
        
        # Close current stream
        await self.close()
        
        # Reinitialize with new voice
        await self.initialize_stream()
        
        # Restart audio streaming
        await self.send_audio_content_start_event()

    async def initialize_stream(self):
        """Initialize the bidirectional stream."""
        if not self.bedrock_client:
            self._initialize_client()

        try:
            # Initialize the bidirectional stream
            operation_input = InvokeModelWithBidirectionalStreamOperationInput(
                model_id=MODEL_ID
            )
            
            print("Initializing Nova Sonic stream...")
            self.stream_response = await self.bedrock_client.invoke_model_with_bidirectional_stream(operation_input)
            
            if not self.stream_response:
                raise Exception("Failed to get stream response from Nova Sonic")
            
            self.is_active = True
            print("Nova Sonic stream initialized successfully")

            # Send initialization events
            init_events = [
                START_SESSION_EVENT,
                START_PROMPT_EVENT % (self.prompt_name, self.current_voice),
                self.TEXT_CONTENT_START_EVENT % (self.prompt_name, self.text_content_name, "SYSTEM"),
                self.TEXT_INPUT_EVENT % (self.prompt_name, self.text_content_name, self.DEFAULT_SYSTEM_PROMPT),
                CONTENT_END_EVENT % (self.prompt_name, self.text_content_name)
            ]
            
            for event in init_events:
                success = await self.send_raw_event(event)
                if not success:
                    raise Exception("Failed to send initialization event")
                await asyncio.sleep(0.05)
            
            # Start listening for responses and audio processing
            self.response_task = asyncio.create_task(self._process_responses())
            self.audio_task = asyncio.create_task(self._process_audio_output())
            
            return self
        except Exception as e:
            self.is_active = False
            print(f"Failed to initialize stream: {str(e)}")
            raise

    async def send_raw_event(self, event_json):
        """Send a raw event JSON to the Bedrock stream."""
        if not self.stream_response:
            print(f"Cannot send event for client #{self.client_id}: stream response not available")
            return False
        
        if not self.is_active:
            print(f"Cannot send event for client #{self.client_id}: stream not active")
            return False
        
        try:
            event = InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
            )
            await self.stream_response.input_stream.send(event)
            return True
        except Exception as e:
            print(f"Error sending event for client #{self.client_id}: {e}")
            return False

    async def send_audio_content_start_event(self):
        content_start_event = CONTENT_START_EVENT % (self.prompt_name, self.audio_content_name)
        await self.send_raw_event(content_start_event)

    async def send_audio_content_end_event(self):
        if not self.is_active:
            return
        content_end_event = CONTENT_END_EVENT % (self.prompt_name, self.audio_content_name)
        await self.send_raw_event(content_end_event)

    async def _process_responses(self):
        """Process responses from Bedrock with improved error handling."""
        try:
            if not self.stream_response:
                print("Stream response is None")
                return

            print("Starting response processing...")
            while self.is_active:
                try:
                    # Check stream state before processing
                    if not self.stream_response or not self.is_active:
                        break

                    output = await self.stream_response.await_output()
                    if not self.is_active or not output:
                        break
                        
                    result = await output[1].receive()
                    if not self.is_active or not result:
                        break
                    
                    # Check if result and value exist before processing
                    if not result.value or not result.value.bytes_:
                        continue

                    response_data = result.value.bytes_.decode('utf-8')
                    json_data = json.loads(response_data)
                    
                    if not self.is_active:
                        break

                    if 'event' in json_data:
                        event = json_data['event']
                        
                        # Debug log for event type
                        event_type = list(event.keys())[0] if event else "unknown"
                        print(f"[DEBUG] Received event type: {event_type}")

                        # If we receive a completionEnd event during closure, break
                        if 'completionEnd' in event and not self.is_active:
                            print(f"Received completionEnd during closure for client #{self.client_id}")
                            break
                        
                        # Handle content start events
                        if 'contentStart' in event and self.is_active:
                            await self._handle_content_start(event['contentStart'])
                        
                        # Handle text output
                        elif 'textOutput' in event and self.is_active:
                            await self._handle_text_output(event['textOutput'])
                            
                        # Handle audio output
                        elif 'audioOutput' in event and self.is_active:
                            await self._handle_audio_output(event['audioOutput'])

                except asyncio.CancelledError:
                    print(f"Response task cancelled for client #{self.client_id}")
                    break
                except Exception as e:
                    if self.is_active:
                        print(f"Error in stream processing for client #{self.client_id}: {e}")
                    await asyncio.sleep(0.05)
                    if not self.is_active:
                        break

        except Exception as e:
            if self.is_active:
                print(f"Response processing error for client #{self.client_id}: {e}")
        finally:
            print(f"Response processing stopped for client #{self.client_id}")

    async def _handle_content_start(self, content_start):
        """Handle content start events with speculative generation control."""
        self.role = content_start['role']
        if 'additionalModelFields' in content_start:
            try:
                additional_fields = json.loads(content_start['additionalModelFields'])
                is_speculative = additional_fields.get('generationStage') == 'SPECULATIVE'
                # Only update display flag if this is a new speculative state
                if is_speculative != self.display_assistant_text:
                    self.display_assistant_text = is_speculative
                    # Clear message history when switching between speculative and final
                    self.last_messages.clear()
                    print(f"[DEBUG] Switching to {'speculative' if is_speculative else 'final'} generation")
            except json.JSONDecodeError:
                print("Error parsing additionalModelFields")

    async def _handle_text_output(self, text_output):
        """Handle text output events with improved barge-in response."""
        text_content = text_output['content']
        current_time = time.time()
        current_datetime = datetime.now()
        formatted_time = current_datetime.strftime("%H:%M:%S.%f")[:-3]
        
        # Handle barge-in detection with immediate response
        if '{ "interrupted" : true }' in text_content:
            self.barge_in = True
            print(f"[{formatted_time}] Barge-in detected")
            # Immediately clear audio queue
            while not self.audio_output_queue.empty():
                try:
                    self.audio_output_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            return

        # Skip empty or whitespace-only messages
        if not text_content.strip():
            return

        # Create a hash of the message content and role
        message_key = f"{self.role}:{text_content.strip()}"
        
        # Check if this message was recently sent
        if message_key in self.last_messages:
            last_sent_time = self.last_messages[message_key]
            time_diff = current_time - last_sent_time
            if time_diff < self.message_cooldown:
                print(f"[DEBUG] Skipping duplicate message (time diff: {time_diff:.2f}s)")
                return
            
            # If message is older than cooldown but very similar, still skip
            if time_diff < self.message_cooldown * 2:
                print(f"[DEBUG] Message similar to recent one, skipping")
                return
        
        # Update the last sent time for this message
        self.last_messages[message_key] = current_time
        
        # Clean up old messages from the tracking dict
        self.last_messages = {k: v for k, v in self.last_messages.items() 
                            if current_time - v < self.message_cooldown * 2}
        
        # Only send the message if it's not a speculative generation or if we explicitly want to show it
        if not self.display_assistant_text and self.role == "ASSISTANT":
            print(f"[DEBUG] Skipping speculative message")
            return
        
        # Send the message with detailed timestamp
        await self.websocket.send_json({
            "type": "text",
            "data": text_content,
            "role": self.role,
            "timestamp": formatted_time,  # Use formatted time with milliseconds
            "unix_timestamp": current_time,  # Keep the unix timestamp for internal use
            "is_speculative": self.display_assistant_text
        })

    async def _handle_audio_output(self, audio_output):
        """Handle audio output events."""
        audio_content = audio_output['content']
        await self.audio_output_queue.put(audio_content)
        
        # Only calculate latency if we have a valid speech end time
        if self.first_assistant_response_time is None and self.last_user_audio_time is not None:
            self.first_assistant_response_time = time.time()
            latency = self.first_assistant_response_time - self.last_user_audio_time
            print(f"\nLatency between user finish and assistant start: {latency:.3f} seconds")
            # Send latency to frontend
            await self.websocket.send_json({
                "type": "latency",
                "data": round(latency, 3)
            })

    def _reset_speech_tracking(self):
        """Reset speech tracking variables when new speech starts."""
        self.first_assistant_response_time = None
        self.silence_start_time = None
        self.last_user_audio_time = None

    async def process_audio_chunk(self, audio_data):
        """Process incoming audio chunk and detect speech end."""
        current_time = time.time()
        
        # If this is empty audio (silence), start tracking silence duration
        if not audio_data.strip():  # Empty base64 string
            if self.silence_start_time is None:
                self.silence_start_time = current_time
            elif current_time - self.silence_start_time >= self.silence_threshold:
                # We've detected end of speech
                if self.last_user_audio_time is None:  # Only set if not already set
                    self.last_user_audio_time = self.silence_start_time
        else:
            # We received audio data, reset silence tracking
            self.silence_start_time = None
            # If this is new speech, reset tracking
            if self.first_assistant_response_time is not None:
                self._reset_speech_tracking()

    async def _process_audio_output(self):
        """Process audio output from the queue and send to client with optimized buffering."""
        print(f"Starting audio output processing for client #{self.client_id}")
        
        # Reduce these values for lower latency
        self.max_buffer_size = 1024  # Reduced from 4096
        self.audio_chunk_size = 512  # Reduced from 2048
        
        while self.is_active:
            try:
                if self.barge_in:
                    # Clear the audio queue immediately
                    while not self.audio_output_queue.empty():
                        try:
                            self.audio_output_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    
                    # Reset buffer immediately
                    self.audio_buffer = []
                    self.buffer_size = 0
                    self.barge_in = False
                    print(f"Cleared audio buffer for client #{self.client_id} due to barge-in")
                    continue

                try:
                    # Reduced timeout for faster response
                    audio_content = await asyncio.wait_for(
                        self.audio_output_queue.get(),
                        timeout=0.02  # Reduced from 0.05 to 20ms
                    )

                    if audio_content and self.is_active:
                        # Send immediately if barge-in is detected
                        if self.barge_in:
                            self.audio_buffer = []
                            self.buffer_size = 0
                            continue
                            
                        # Add to buffer
                        self.audio_buffer.append(audio_content)
                        self.buffer_size += len(audio_content)

                        # Send more frequently with smaller buffer
                        if self.buffer_size >= self.max_buffer_size:
                            combined_content = "".join(self.audio_buffer)
                            await self.websocket.send_json({
                                "type": "audio",
                                "data": combined_content
                            })
                            self.audio_buffer = []
                            self.buffer_size = 0

                except asyncio.TimeoutError:
                    # Send buffer more aggressively
                    if self.audio_buffer and self.is_active:
                        combined_content = "".join(self.audio_buffer)
                        await self.websocket.send_json({
                            "type": "audio",
                            "data": combined_content
                        })
                        self.audio_buffer = []
                        self.buffer_size = 0
                    await asyncio.sleep(0.01)  # Reduced sleep time
                    continue

            except Exception as e:
                print(f"Error processing audio output for client #{self.client_id}: {e}")
                await asyncio.sleep(0.01)

        print(f"Audio output processing stopped for client #{self.client_id}")

    async def close(self):
        """Close the stream properly following nova_sonic.py pattern."""
        if not self.is_active:
            return
        
        print(f"Closing stream for client #{self.client_id}")
        
        try:
            # First stop audio processing but keep stream active for cleanup
            if self.audio_task and not self.audio_task.done():
                print(f"Cancelling audio task for client #{self.client_id}")
                self.audio_task.cancel()
                try:
                    await self.audio_task
                except asyncio.CancelledError:
                    pass

            # Send cleanup events while stream is still active
            try:
                print(f"Sending cleanup events for client #{self.client_id}")
                if self.stream_response and self.is_active:
                    # Send events in sequence
                    await self.send_audio_content_end_event()
                    await asyncio.sleep(0.1)  # Small delay between events
                    await self.send_raw_event(PROMPT_END_EVENT % self.prompt_name)
                    await asyncio.sleep(0.1)  # Small delay between events
                    await self.send_raw_event(SESSION_END_EVENT)
                    await asyncio.sleep(0.2)  # Longer delay to ensure events are processed
            except Exception as e:
                print(f"Error sending cleanup events for client #{self.client_id}: {e}")

            # Mark stream as inactive before closing it
            self.is_active = False
            
            # Close the stream
            if self.stream_response:
                try:
                    print(f"Closing input stream for client #{self.client_id}")
                    await self.stream_response.input_stream.close()
                    # Wait for any pending callbacks to complete
                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"Error closing input stream for client #{self.client_id}: {e}")

            # Cancel response task last, after stream is closed and inactive
            if self.response_task and not self.response_task.done():
                print(f"Cancelling response task for client #{self.client_id}")
                self.response_task.cancel()
                try:
                    await self.response_task
                except asyncio.CancelledError:
                    pass
            
        except Exception as e:
            print(f"Error during stream closure for client #{self.client_id}: {e}")
        finally:
            # Final cleanup
            self.is_active = False
            self.stream_response = None
            # Clear any pending messages
            self.last_messages.clear()
            print(f"Stream cleanup completed for client #{self.client_id}")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, session: Optional[str] = Cookie(None)):
    # Verify session before accepting WebSocket connection
    if not verify_session(session):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    print(f"Client #{client_id} connected")
    
    # Initialize stream manager
    stream_manager = StreamManager(websocket, client_id)
    active_connections[client_id] = stream_manager
    
    try:
        # Initialize the stream
        await stream_manager.initialize_stream()
        
        # Send audio content start event immediately
        await stream_manager.send_audio_content_start_event()
        
        while True:
            try:
                data = await websocket.receive_text()
                
                # Check if stream is still active before processing
                if not stream_manager.is_active:
                    print(f"Stream inactive for client #{client_id}, closing connection")
                    break
                    
                data = json.loads(data)
                
                if data["type"] == "audio":
                    # Process the audio chunk for silence detection
                    await stream_manager.process_audio_chunk(data["data"])
                    
                    # Send audio data to Nova Sonic immediately for real-time processing
                    audio_event = AUDIO_EVENT_TEMPLATE % (
                        stream_manager.prompt_name,
                        stream_manager.audio_content_name,
                        data["data"]
                    )
                    if not await stream_manager.send_raw_event(audio_event):
                        print(f"Failed to send audio event for client #{client_id}, closing connection")
                        break
                    
                elif data["type"] == "voice_change":
                    # Handle voice change request
                    await stream_manager.change_voice(data["voice"])
                    
                elif data["type"] == "end":
                    print(f"Client #{client_id} ending stream")
                    # Properly close the stream before breaking
                    await stream_manager.close()
                    break
                    
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from client #{client_id}: {str(e)}")
            except WebSocketDisconnect:
                print(f"WebSocket disconnected for client #{client_id}")
                break
            except Exception as e:
                print(f"Error processing data from client #{client_id}: {str(e)}")
                break
    
    except WebSocketDisconnect:
        print(f"Client #{client_id} disconnected")
    except Exception as e:
        print(f"Error with client #{client_id}: {str(e)}")
    finally:
        if client_id in active_connections:
            try:
                # Ensure stream is properly closed if not already closed
                if stream_manager.is_active:
                    await stream_manager.close()
            except Exception as e:
                print(f"Error closing stream for client #{client_id}: {str(e)}")
            finally:
                # Always remove from active connections
                del active_connections[client_id]
                print(f"Client #{client_id} connection cleaned up")

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server...")
    print(f"Templates directory: {templates_path}")
    print(f"Static files directory: {static_path}")
    uvicorn.run(app, host="0.0.0.0", port=8100, log_level="debug") 