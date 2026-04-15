import asyncio
import json
import os
import base64
import logging
from dotenv import load_dotenv

from STT.deepgram import DeepgramSTT
from TTS.elevenlabs import stream_tts_to_twilio
from rag import RAGSystem

from fastapi import FastAPI, Request, Response, WebSocket
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client

import uvicorn

load_dotenv()

# 🔥 LOGGER
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()


class CallAgent:
    def __init__(self):
        logger.info("🚀 Initializing CallAgent")

        self.rag = RAGSystem()
        self.deepgram = DeepgramSTT()
        self.stream_sid = None

        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")

        self.twilio_client = Client(
            self.twilio_account_sid,
            self.twilio_auth_token
        )

        logger.info("✅ CallAgent initialized")

    # 📞 OUTBOUND CALL
    def make_outbound_call(self, to_number, from_number=None):
        if not from_number:
            from_number = os.getenv("TWILIO_FROM_NUMBER")

        host = os.getenv("HOST")

        logger.info(f"📞 Calling {to_number}")

        call = self.twilio_client.calls.create(
            to=to_number,
            from_=from_number,
            url=f"https://{host}/voice"
        )

        logger.info(f"📞 Call SID: {call.sid}")
        return call.sid

    # 🎤 STREAM HANDLER
    async def handle_twilio_stream(self, websocket: WebSocket):
        logger.info("🔗 Twilio WebSocket connected")

        await websocket.accept()

        # 🧠 TRANSCRIPT CALLBACK (DEFINE FIRST)
        async def on_transcript(text):
            logger.info(f"🗣 USER: {text}")

            answer = await asyncio.to_thread(self.rag.query, text)
            logger.info(f"🤖 AI: {answer}")

            await stream_tts_to_twilio(answer, websocket, self.stream_sid)
            logger.info("🔊 Response sent")

        # ✅ SET CALLBACK BEFORE CONNECT
        self.deepgram.set_callback(on_transcript)

        # ✅ CONNECT ONLY ONCE
        await self.deepgram.connect()
        logger.info("✅ Deepgram connected")

        try:
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)

                event = data.get("event")

                if event == "start":
                    self.stream_sid = data["start"]["streamSid"]
                    logger.info(f"📡 Stream started: {self.stream_sid}")

                elif event == "media":
                    payload = data["media"]["payload"]
                    audio_bytes = base64.b64decode(payload)

                    await self.deepgram.send_audio(audio_bytes)

                elif event == "stop":
                    logger.warning("🛑 Stream stopped")
                    break

        except Exception as e:
            logger.error(f"❌ Error: {e}")

        finally:
            await self.deepgram.close()
            logger.info("🔚 Deepgram closed")


agent = CallAgent()


# 📞 TWILIO WEBHOOK
@app.post("/voice")
async def voice(request: Request):
    host = os.getenv("HOST")

    logger.info("📞 Twilio webhook hit")

    response = VoiceResponse()

    response.connect().stream(
        url=f"wss://{host}/stream"
    )

    return Response(
        content=str(response),
        media_type="application/xml"
    )


# 🌐 WEBSOCKET
@app.websocket("/stream")
async def stream_endpoint(websocket: WebSocket):
    logger.info("🌐 WebSocket endpoint hit")
    await agent.handle_twilio_stream(websocket)


# 🚀 AUTO CALL
@app.on_event("startup")
async def startup_event():
    logger.info("⚡ Starting call...")
    agent.make_outbound_call("+916309546201")


if __name__ == "__main__":
    logger.info("🚀 Server starting...")
    uvicorn.run(app, host="0.0.0.0", port=8001)