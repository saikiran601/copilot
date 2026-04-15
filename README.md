# RAG Architecture with LangChain

This project demonstrates a Retrieval-Augmented Generation (RAG) architecture using LangChain with a class-based implementation, including Text-to-Speech (TTS) and Speech-to-Text (STT) capabilities.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up your API keys:
   - Edit the `.env` file and replace the placeholders with your actual API keys:
     - `OPENAI_API_KEY`
     - `ELEVENLABS_API_KEY` (for TTS)
     - `DEEPGRAM_API_KEY` (for STT)

3. Place your DOCX documents in the `data` folder.

The system will automatically create and persist a FAISS vector database in the `vector_db` folder for faster subsequent loads.

## Usage

Run the RAG script:
```
python rag.py
```

This will load DOCX documents from the `data` folder, create embeddings, store them in a FAISS vector database, and perform a sample query.

## TTS and STT

The project includes separate modules for text-to-speech and speech-to-text:

### ElevenLabs TTS
Located in `tts_stt/elevenlabs_tts.py`. Use this to convert text to speech.

Example:
```python
from tts_stt.elevenlabs_tts import ElevenLabsTTS
tts = ElevenLabsTTS()
tts.generate_speech("Hello world", voice="Rachel", output_file="hello.mp3")
```

### Deepgram STT
Located in `tts_stt/deepgram_stt.py`. Use this to transcribe audio to text.

Example:
```python
from tts_stt.deepgram_stt import DeepgramSTT

## Web Scraping

The `webscrapping.py` script uses Playwright to scrape Gmail email addresses from a given website.

### Usage

```
python webscrapping.py <url>
```

Replace `<url>` with the website URL you want to scrape.

### Requirements

Ensure Playwright browsers are installed:

```
playwright install
```

This is already done if you followed the setup.

### Troubleshooting

- If you get network errors, check your internet connection.
- For dynamic content, the script waits for network idle, but may need adjustments for specific sites.

## Voice Activity with OpenAI Realtime

The `voice_activity.py` script uses OpenAI's Realtime API for real-time voice conversation from microphone, integrating STT, RAG, and TTS.

### Features
- Real-time microphone input/output using OpenAI's GPT-4o Realtime Preview model
- Automatic STT (Speech-to-Text) from speech
- Queries the RAG system for answers
- Generates TTS (Text-to-Speech) responses played back through speakers
- Terminal-based interaction with continuous conversation

### Usage

1. Ensure you have an OpenAI API key set in `.env` as `OPENAI_API_KEY`.

2. Run the agent:
   ```
   python voice_activity.py
   ```

3. Speak into your microphone. The system will transcribe, query RAG, and speak the response.

### Requirements

- Latest `openai` package (supports realtime API)
- Microphone and speakers configured
- PyAudio for audio handling

### Troubleshooting

- Ensure microphone is not muted and has proper permissions.
- Check OpenAI API key and quota.
- For audio issues, verify PyAudio installation and audio device settings.

## Voice Activity Detection (VAD)

The `tts_stt/vad.py` module provides real-time voice activity detection using WebRTC VAD:

- Detects when speech begins and ends in audio streams
- Supports continuous listening or single-shot recording
- Integrates with microphone input for real-time processing

## Main Voice Agent

The `main.py` script provides a complete real-time voice agent with VAD integration:

### Features
- **VAD**: Detects speech in real-time from microphone
- **STT**: Transcribes detected speech using Deepgram
- **RAG**: Processes queries against your document knowledge base
- **TTS**: Speaks responses using ElevenLabs (no audio files saved)

### Usage Modes
1. **Single Query**: Records until silence, processes one query
2. **Continuous**: Listens continuously, processes each speech segment

### Running the Agent
```bash
python main.py
```

Choose your preferred mode and start speaking! The system will:
1. Detect when you start speaking
2. Transcribe your speech to text
3. Query your RAG system for relevant information
4. Speak the answer back to you

## WebSocket Voice Agent

The `websocket_server.py` provides a web-based real-time voice agent using FastAPI WebSockets:

### Features
- **WebSocket Connection**: Continuous interaction until client disconnects
- **Browser-based Client**: Built-in HTML interface for easy testing
- **Real-time Processing**: Processes audio streams as they arrive
- **VAD Integration**: Detects speech segments in the audio stream
- **Full Pipeline**: STT → RAG → TTS over WebSocket

### Running the WebSocket Server
```bash
python websocket_server.py
```

### Terminal Client
For terminal-based interaction, use the terminal client:

```bash
python terminal_client.py
```

This connects to the WebSocket server and:
- Records audio from your microphone
- Sends audio data in real-time
- Receives and plays TTS responses
- Continues until you press Ctrl+C

### WebSocket Protocol
- **Endpoint**: `ws://localhost:8000/voice`
- **Client sends**: Raw PCM audio data (16-bit, 16kHz, mono)
- **Server sends**: TTS audio responses (MP3 format)

This enables continuous voice interaction through the terminal without saving any audio files locally.

## Call Agent with Twilio Integration

The `call_agent.py` provides a phone-based voice agent using Twilio for telephony and OpenAI's Realtime API for STT/TTS processing.

### Features
- **Outbound Calls**: Initiates calls to specified phone numbers
- **Real-time Audio Streaming**: Bidirectional audio stream between Twilio and OpenAI
- **RAG Integration**: Processes user speech through STT, queries RAG system, and responds via TTS
- **Audio Format Conversion**: Converts between Twilio's μ-law 8kHz and OpenAI's PCM16 24kHz formats

### Setup

1. **Twilio Account**: Sign up for a Twilio account and get a phone number.

2. **Environment Variables**: Add to `.env`:
   - `OPENAI_API_KEY` (already required)
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_FROM_NUMBER` (your Twilio phone number, e.g., +1234567890)
   - `HOST` (your public URL, e.g., abc123.ngrok.io)

3. **Public URL**: The server needs a public URL for Twilio webhooks. Use ngrok or similar:
   ```
   ngrok http 8000
   ```
   Set the `HOST` in `.env` to your ngrok URL (without https://).

### Running the Call Agent
```bash
python call_agent.py
```

This will automatically initiate an outbound call to the configured number and start the conversation.

### How It Works
1. Script runs and initiates outbound call to specified number
2. When call is answered, Twilio requests TwiML from `/voice` endpoint
3. Server responds with TwiML to start bidirectional stream to `/stream`
4. Audio flows: Twilio → Server → OpenAI Realtime API → RAG → TTS → Server → Twilio
5. Customer hears the response and can continue the conversation

### Requirements
- Twilio account and phone number
- Publicly accessible server (ngrok for development)
- OpenAI API key with Realtime API access
- Twilio credentials in .env

## Components

- **Document Loading**: Loads DOCX files from the `data` directory using Docx2txtLoader
- **Text Splitting**: Splits the documents into manageable chunks
- **Embeddings**: Uses OpenAI embeddings to vectorize the text
- **Vector Store**: FAISS for efficient similarity search
- **Retrieval QA**: Combines retrieval and generation for answering questions, with custom prompts to control hallucinations by ensuring answers are based only on retrieved context
- **TTS**: ElevenLabs for high-quality text-to-speech synthesis
- **STT**: Deepgram for accurate speech-to-text transcription (using REST API)

## RAGSystem Class

The `RAGSystem` class encapsulates the RAG functionality with built-in hallucination control:

- `load_documents(data_dir='data')`: Loads DOCX files from the specified directory
- `split_documents(chunk_size=1000, chunk_overlap=200)`: Splits documents into chunks
- `create_vectorstore()`: Creates FAISS vector store from document chunks
- `create_qa_chain()`: Sets up the retrieval QA chain with a custom prompt that instructs the model to only answer based on retrieved context and say "I don't know" for questions not covered
- `query(query)`: Performs a query and returns the answer

## Voice Agent

The `voice_agent.py` script provides a complete AI voice agent that integrates STT, RAG, and TTS:

- **STT**: Transcribes audio input to text using Deepgram
- **RAG**: Processes the transcribed query through the RAG system for accurate, context-aware responses
- **TTS**: Converts the RAG response to speech using ElevenLabs and plays it directly (no audio files saved)

### Usage
```python
from voice_agent import VoiceAgent
agent = VoiceAgent()
agent.process_audio_query("your_audio_file.wav", voice="Rachel")
```

This creates an end-to-end voice interaction system where users can speak queries, get AI-powered responses based on your documents, and hear the answers spoken back.#   c o p i l o t  
 #   c o p i l o t  
 