import asyncio
import webrtcvad
import io
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import numpy as np
from tts_stt.deepgram_stt import DeepgramSTT
from tts_stt.elevenlabs_tts import ElevenLabsTTS
from rag import RAGSystem

app = FastAPI()

class WebSocketVoiceAgent:
    def __init__(self):
        self.stt = DeepgramSTT()
        self.tts = ElevenLabsTTS()
        self.rag = RAGSystem()
        self.vad = webrtcvad.Vad(3)  # Aggressiveness level 3

    async def process_audio_stream(self, websocket: WebSocket):
        """Process continuous audio stream from WebSocket."""
        sample_rate = 16000  # Assume 16kHz
        frame_duration = 30  # 30ms frames
        frame_size = int(sample_rate * frame_duration / 1000)
        
        ring_buffer = []
        triggered = False
        voiced_frames = []
        
        try:
            while True:
                # Receive audio data (expecting bytes)
                data = await websocket.receive_bytes()
                
                # Convert to numpy array (assuming 16-bit PCM)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Split into frames
                for i in range(0, len(audio_data), frame_size):
                    frame = audio_data[i:i+frame_size]
                    if len(frame) < frame_size:
                        continue
                    
                    # Convert back to bytes for VAD
                    frame_bytes = frame.tobytes()
                    
                    is_speech = self.vad.is_speech(frame_bytes, sample_rate)
                    
                    if not triggered:
                        ring_buffer.append((frame_bytes, is_speech))
                        if len(ring_buffer) > 10:
                            ring_buffer.pop(0)
                        
                        num_voiced = sum(1 for _, speech in ring_buffer if speech)
                        if num_voiced > 8:  # 80% of buffer has speech
                            triggered = True
                            print("Speech detected")
                            # Add buffered frames
                            for f, _ in ring_buffer:
                                voiced_frames.append(f)
                            ring_buffer = []
                    else:
                        voiced_frames.append(frame_bytes)
                        
                        # Check for silence
                        ring_buffer.append((frame_bytes, is_speech))
                        if len(ring_buffer) > 10:
                            ring_buffer.pop(0)
                        
                        num_unvoiced = sum(1 for _, speech in ring_buffer if not speech)
                        if num_unvoiced > 8:  # 80% silence
                            triggered = False
                            print("Speech ended, processing...")
                            
                            # Process the speech segment
                            await self.process_speech_segment(b''.join(voiced_frames), websocket)
                            ring_buffer = []
                            voiced_frames = []
                            
        except WebSocketDisconnect:
            print("Client disconnected")

    async def process_speech_segment(self, audio_bytes, websocket: WebSocket):
        """Process a detected speech segment."""
        try:
            # STT
            query = self.stt.transcribe_audio(audio_bytes)
            if not query:
                print("Failed to transcribe")
                return
            
            print(f"Query: {query}")
            
            # RAG
            if self.rag:
                answer = self.rag.query(query)
            else:
                answer = "RAG system not available"
            
            print(f"Answer: {answer}")
            
            # TTS
            audio_response = self.tts.generate_speech_bytes(answer)
            if audio_response:
                # Send audio back to client
                await websocket.send_bytes(audio_response)
                print("Response sent")
                
        except Exception as e:
            print(f"Error processing speech segment: {e}")

agent = WebSocketVoiceAgent()

@app.websocket("/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")
    await agent.process_audio_stream(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)