import asyncio
import json
import os
from dotenv import load_dotenv
# from STT.deepgram import DeepgramSTT
# from TTS.elevenlabs import ElevenLabsTTS
from rag import RAGSystem
from fastapi import FastAPI, Request, Response, WebSocket
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
import uvicorn
import aiohttp

load_dotenv()

app = FastAPI()


class CallAgent:
    def __init__(self):
        print("DEBUG: Initializing CallAgent")
        self.rag = RAGSystem()
        # self.deepgram = DeepgramSTT()
        # self.tts = ElevenLabsTTS()

        self.stream_sid = None
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")

        self.twilio_client = Client(
            self.twilio_account_sid,
            self.twilio_auth_token
        )

        print("DEBUG: CallAgent initialized successfully")


    def make_outbound_call(self, to_number, from_number=None):

        if not from_number:
            from_number = os.getenv("TWILIO_FROM_NUMBER")

        host = os.getenv("HOST")

        twiml_url = f"https://{host}/voice"

        call = self.twilio_client.calls.create(
            to=to_number,
            from_=from_number,
            url=twiml_url
        )

        print(f"Outbound call initiated: {call.sid}")

        return call.sid

    async def handle_twilio_stream(self, websocket):

        print("DEBUG: Twilio stream connected")
        openai_ws_url = "wss://api.openai.com/v1/realtime?model=gpt-realtime"

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "OpenAI-Beta": "realtime=v1"
        }

        async with aiohttp.ClientSession() as session:

            async with session.ws_connect(
                openai_ws_url,
                headers=headers
            ) as openai_ws:

                print("DEBUG: Connected to OpenAI Realtime")

                await self._configure_session(openai_ws)

                await asyncio.gather(
                    self._twilio_to_openai(websocket, openai_ws),
                    self._openai_to_twilio(websocket, openai_ws)
                )

    async def _configure_session(self, openai_ws):

        print("DEBUG: Configuring OpenAI session")

        session_update = {
            "type": "session.update",
            "session": {
                        "instructions": '''You are a gentle and sweet-sounding Indian female voice assistant. 
                        Your speaking style should be warm, soft, caring, and pleasant—like a friendly young Indian lady.
                        
                        Voice Characteristics:
                        - Soft, smooth, and sweet tone
                        - Gentle and warm delivery
                        - Mild Indian English accent with clear pronunciation
                        - Natural emotional warmth in every sentence
                        - Calm, polite, and patient style
                        - Light smile in your voice
                        
                        Speaking Style:
                        - Use friendly expressions like “ji”, “haan sure”, “just a moment please”, “don’t worry, I’ll help you”.
                        - Keep responses polite, empathetic, and human-like.
                        - Pace should be steady and soothing—not fast, not robotic.
                        - Add natural speech patterns like slight pauses and soft intonation.
                        
                        Avoid:
                        - Robotic tone
                        - Overly formal or stiff sentences
                        - Flat or monotone delivery
                        
                        Your goal is to sound like a sweet, caring Indian woman who speaks gently and reassures the listener.
                        ''',
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "input_audio_transcription": {"model": "whisper-1"},
                "voice": "alloy",
                "turn_detection": {
                    "type": "server_vad"
                }
            }
        }

        await openai_ws.send_str(json.dumps(session_update))

        print("DEBUG: Session initialized")

    async def _twilio_to_openai(self, websocket, openai_ws):
        
        print("DEBUG: Starting Twilio → OpenAI audio stream")
        while True:

            message = await websocket.receive_text()
            data = json.loads(message)

            if data["event"] == "start":

                self.stream_sid = data["start"]["streamSid"]

                print("DEBUG: Twilio stream started", self.stream_sid)

            elif data["event"] == "media":
                await openai_ws.send_str(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": data["media"]["payload"]
                }))
            elif data["event"] == "stop":
                print("DEBUG: Twilio stream stopped")

                break

    async def _openai_to_twilio(self, websocket, openai_ws):
        print("DEBUG: Starting OpenAI → Twilio stream")

        response_in_progress = False
        while True:
            msg = await openai_ws.receive()

            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)

                print("DEBUG: OpenAI event:", data.get("type"))

                if data.get("type") == "error":
                    print("DEBUG: OpenAI error:", json.dumps(data, indent=2))
                    continue

                if data.get("type") == "session.created":
                    print("DEBUG: Session created successfully")
                    continue

                if data.get("type") == "session.updated":
                    print("DEBUG: Session updated")
                    continue

                if data.get("type") == "input_audio_buffer.speech_started":
                    print("DEBUG: Speech started")
                    continue

                if data.get("type") == "input_audio_buffer.speech_stopped":
                    print("DEBUG: Speech stopped")
                    continue

                if data.get("type") == "input_audio_buffer.committed":
                    print("DEBUG: Audio buffer committed")
                    continue

                if data.get("type") == "response.created":
                    print("DEBUG: Response created")
                    response_in_progress = True
                    continue

                if data.get("type") == "response.done":
                    print("DEBUG: Response done")
                    response_in_progress = False
                    continue

                if data.get("type") == "conversation.item.input_audio_transcription.completed":
                    transcript = data.get("transcript", "")

                    print("DEBUG: User transcription completed:", transcript)
                    if transcript and not response_in_progress:
                        response_in_progress = True
                        answer = await asyncio.to_thread(
                            self.rag.query,
                            transcript
                        )
                        print("DEBUG: RAG Answer:", answer)

                        await openai_ws.send_str(json.dumps({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "assistant",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": answer
                                    }
                                ]
                            }
                        }))

                        print("DEBUG: Sent conversation item to OpenAI")

                        await openai_ws.send_str(json.dumps({
                            "type": "response.create"
                        }))

                        print("DEBUG: Sent response.create to OpenAI")
                    continue

                if data.get("type") == "conversation.item.created":
                    item = data.get("item", {})
                    print("DEBUG: Conversation item created:", item.get("role"))
                    print("DEBUG: Item content:", json.dumps(item.get("content", []), indent=2))

                    # Skip processing user items here, wait for transcription
                    continue

                elif data.get("type") == "response.audio.delta":

                    await websocket.send_json({
                        "event": "media",
                        "streamSid": self.stream_sid,
                        "media": {
                            "payload": data["delta"]
                        }
                    })


agent = CallAgent()


@app.post("/voice")
async def voice(request: Request):
    host = os.getenv("HOST")
    response = VoiceResponse()
    response.connect().stream(
        url=f"wss://{host}/stream"
    )

    return Response(
        content=str(response),
        media_type="application/xml"
    )

@app.websocket("/stream")
async def stream_endpoint(websocket: WebSocket):
    await websocket.accept()

    await agent.handle_twilio_stream(websocket)


@app.on_event("startup")
async def startup_event():
    to_number = "+916309546201"
    agent.make_outbound_call(to_number)


if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8001)