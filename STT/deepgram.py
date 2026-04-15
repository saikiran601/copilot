# import websockets
# import json
# import os

# class DeepgramSTT:
#     def __init__(self):
#         self.api_key = os.getenv("DEEPGRAM_API_KEY")
#         self.url = "wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000"

#     async def connect(self):
#         self.ws = await websockets.connect(
#             self.url,
#             extra_headers={"Authorization": f"Token {self.api_key}"}
#         )

#     async def send_audio(self, audio_chunk):
#         await self.ws.send(audio_chunk)

#     async def receive_transcript(self):
#         response = await self.ws.recv()
#         data = json.loads(response)

#         if "channel" in data:
#             return data["channel"]["alternatives"][0]["transcript"]

#         return None


import os
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)


class DeepgramSTT:
    def __init__(self):
        self.dg_connection = None
        self.callback = None
        self.parts = []

    def set_callback(self, callback):
        self.callback = callback

    async def connect(self):
        print("🔗 Connecting to Deepgram...")

        config = DeepgramClientOptions(options={"keepalive": "true"})
        deepgram = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"), config)

        self.dg_connection = deepgram.listen.asynclive.v("1")

        # 🎤 Handle transcripts
        async def on_message(self, result, **kwargs):
            print("🧠 Deepgram raw:", result)
            print("🧠 speech_final:", result.speech_final)

            sentence = result.channel.alternatives[0].transcript

            if not result.speech_final:
                if sentence:
                    self.parts.append(sentence)
            else:
                if sentence:
                    self.parts.append(sentence)

                full_sentence = " ".join(self.parts).strip()
                print("🗣 Caller:", full_sentence)

                self.parts = []

                # 🔥 Only trigger if valid text
                if self.callback and full_sentence:
                    await self.callback(full_sentence)

        async def on_error(self, error, **kwargs):
            print("❌ Deepgram Error:", error)

        self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)

        # CRITICAL FIX HERE
        options = LiveOptions(
            model="nova-2",
            punctuate=True,
            language="en-US",
            encoding="mulaw",
            sample_rate=8000,
            channels=1,
            endpointing=300, 
        )

        await self.dg_connection.start(options)
        print("Deepgram connected")

    async def send_audio(self, audio_bytes):
        await self.dg_connection.send(audio_bytes)

    async def close(self):
        try:
            if self.dg_connection:
                await self.dg_connection.finish()
        except Exception as e:
            print("Close error:", e)