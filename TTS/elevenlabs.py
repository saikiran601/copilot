# import os
# import base64
# import io
# from dotenv import load_dotenv
# from elevenlabs import ElevenLabs
# from pydub import AudioSegment

# load_dotenv()

# class ElevenLabsTTS:
#     def __init__(self):
#         self.api_key = os.getenv("ELEVENLABS_API_KEY")
#         self.client = ElevenLabs(api_key=self.api_key)

#     def generate_base64_audio(self, text, voice="Rachel"):
#         try:
#             # Step 1: Generate audio (MP3)
#             audio_bytes = self.client.generate(
#                 text=text,
#                 voice=voice,
#                 model="eleven_monolingual_v1"
#             )

#             # Step 2: Convert MP3 → PCM μ-law (Twilio format)
#             audio = AudioSegment.from_file(
#                 io.BytesIO(audio_bytes),
#                 format="mp3"
#             )
#             # Convert to 8kHz mono
#             audio = audio.set_frame_rate(8000).set_channels(1)

#             # Convert to raw PCM
#             raw_audio = audio.raw_data

#             # Step 3: Base64 encode
#             audio_base64 = base64.b64encode(raw_audio).decode("utf-8")

#             return audio_base64

#         except Exception as e:
#             print("ElevenLabs error:", e)
#             return None




import os
import base64
import aiohttp
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

# ✅ Logger setup
logger = logging.getLogger("TTS")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


DG_API_KEY = os.getenv("DEEPGRAM_API_KEY")
MODEL_NAME = "alpha-stella-en-v2"


async def stream_tts_to_twilio(text: str, websocket, stream_sid):
    logger.info(f"🔊 TTS started | Text: {text}")

    url = f"https://api.beta.deepgram.com/v1/speak?model={MODEL_NAME}&encoding=mulaw&sample_rate=8000"

    headers = {
        "Authorization": f"Token {DG_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {"text": text}

    start_time = asyncio.get_event_loop().time()
    first_chunk_sent = False
    chunk_count = 0

    try:
        # 🔥 Clear previous audio (important for Twilio)
        await websocket.send_json({
            "event": "clear",
            "streamSid": stream_sid
        })
        logger.info("🧹 Cleared previous audio stream")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:

                logger.info(f"🌐 Deepgram TTS response status: {response.status}")

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ TTS API error: {error_text}")
                    return

                async for chunk in response.content.iter_chunked(512):
                    if not chunk:
                        continue

                    chunk_count += 1

                    if not first_chunk_sent:
                        ttfb = (asyncio.get_event_loop().time() - start_time) * 1000
                        logger.info(f"⚡ First audio chunk received (TTFB): {int(ttfb)} ms")
                        first_chunk_sent = True

                    encoded_audio = base64.b64encode(chunk).decode("utf-8")

                    await websocket.send_json({
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {
                            "payload": encoded_audio
                        }
                    })

                    logger.debug(f"📡 Sent audio chunk #{chunk_count}")

                    # 🔥 prevent flooding Twilio
                    await asyncio.sleep(0.01)

        logger.info(f"✅ TTS streaming completed | Total chunks: {chunk_count}")

    except Exception as e:
        logger.error(f"❌ TTS Error: {str(e)}")