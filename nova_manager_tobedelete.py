import os
import asyncio
import base64
import json
import uuid
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config, HTTPAuthSchemeResolver, SigV4AuthScheme
from smithy_aws_core.credentials_resolvers.environment import EnvironmentCredentialsResolver

class NovaSonicManager:
    def __init__(self, model_id='amazon.nova-sonic-v1:0', region='us-east-1'):
        self.model_id = model_id
        self.region = region
        self.stream_response = None
        self.is_active = False
        self.prompt_name = str(uuid.uuid4())
        self.content_name = str(uuid.uuid4())
        self._initialize_client()

    def _initialize_client(self):
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
            http_auth_scheme_resolver=HTTPAuthSchemeResolver(),
            http_auth_schemes={"aws.auth#sigv4": SigV4AuthScheme()}
        )
        self.bedrock_client = BedrockRuntimeClient(config=config)

    async def initialize_stream(self):
        if not self.bedrock_client:
            self._initialize_client()

        self.stream_response = await self.bedrock_client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
        )
        self.is_active = True

        # Send initialization events
        await self._send_start_session()
        await self._send_start_prompt()
        await self._send_content_start()

    async def _send_raw_event(self, event_json):
        if not self.stream_response or not self.is_active:
            return

        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
        )
        await self.stream_response.input_stream.send(event)

    async def _send_start_session(self):
        event = {
            "event": {
                "sessionStart": {
                    "inferenceConfiguration": {
                        "maxTokens": 1024,
                        "topP": 0.9,
                        "temperature": 0.7
                    }
                }
            }
        }
        await self._send_raw_event(json.dumps(event))

    async def _send_start_prompt(self):
        event = {
            "event": {
                "promptStart": {
                    "promptName": self.prompt_name,
                    "textOutputConfiguration": {
                        "mediaType": "text/plain"
                    },
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 24000,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "voiceId": "matthew",
                        "encoding": "base64",
                        "audioType": "SPEECH"
                    }
                }
            }
        }
        await self._send_raw_event(json.dumps(event))

    async def _send_content_start(self):
        event = {
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": self.content_name,
                    "type": "AUDIO",
                    "interactive": True,
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
        }
        await self._send_raw_event(json.dumps(event))

    async def process_audio(self, audio_bytes, output_queue):
        if not self.is_active:
            return

        # Send audio data
        audio_event = {
            "event": {
                "audioInput": {
                    "promptName": self.prompt_name,
                    "contentName": self.content_name,
                    "content": base64.b64encode(audio_bytes).decode('utf-8')
                }
            }
        }
        await self._send_raw_event(json.dumps(audio_event))

        # Process response
        try:
            output = await self.stream_response.await_output()
            result = await output[1].receive()

            if result.value and result.value.bytes_:
                response_data = json.loads(result.value.bytes_.decode('utf-8'))
                
                if 'event' in response_data:
                    if 'audioOutput' in response_data['event']:
                        audio_content = response_data['event']['audioOutput']['content']
                        audio_bytes = base64.b64decode(audio_content)
                        await output_queue.put(audio_bytes)

        except Exception as e:
            print(f"Error processing response: {str(e)}")

    async def close(self):
        if not self.is_active:
            return

        # Send end events
        await self._send_content_end()
        await self._send_prompt_end()
        await self._send_session_end()

        if self.stream_response:
            await self.stream_response.input_stream.close()
        self.is_active = False

    async def _send_content_end(self):
        event = {
            "event": {
                "contentEnd": {
                    "promptName": self.prompt_name,
                    "contentName": self.content_name
                }
            }
        }
        await self._send_raw_event(json.dumps(event))

    async def _send_prompt_end(self):
        event = {
            "event": {
                "promptEnd": {
                    "promptName": self.prompt_name
                }
            }
        }
        await self._send_raw_event(json.dumps(event))

    async def _send_session_end(self):
        event = {
            "event": {
                "sessionEnd": {}
            }
        }
        await self._send_raw_event(json.dumps(event)) 