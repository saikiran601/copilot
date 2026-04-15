import os
from dotenv import load_dotenv
from STT.deepgram import DeepgramSTT
from TTS.elevenlabs import ElevenLabsTTS
from rag import RAGSystem

# Load environment variables
load_dotenv()

class VoiceAgent:
    def __init__(self):
        self.stt = DeepgramSTT()
        self.tts = ElevenLabsTTS()
        self.rag = RAGSystem()
        # RAG is initialized in constructor
        pass

    def process_audio_query(self, audio_file_path, voice="Rachel"):
        """
        Process an audio query through STT -> RAG -> TTS pipeline.

        Args:
            audio_file_path (str): Path to the audio file containing the query.
            voice (str): Voice to use for TTS response.
        """
        # Step 1: STT - Transcribe audio to text
        print("Transcribing audio...")
        query = self.stt.transcribe_audio(audio_file_path)
        if not query:
            print("Failed to transcribe audio.")
            return

        print(f"Transcribed query: {query}")

        # Step 2: RAG - Generate response based on query
        print("Generating response with RAG...")
        try:
            answer = self.rag.query(query)
            print(f"RAG Answer: {answer}")
        except Exception as e:
            print(f"RAG query failed: {e}")
            answer = "I'm sorry, I couldn't process your query."

        # Step 3: TTS - Convert answer to speech and play
        print("Converting answer to speech...")
        self.tts.play_speech(answer, voice=voice)
        print("Response played.")

# Example usage
# if __name__ == "__main__":
#     agent = VoiceAgent()
#     # Replace with actual audio file path
#     audio_file = "path_to_your_audio_query.wav"
#     agent.process_audio_query(audio_file, voice="Drew")