import os
import requests
import gradio as gr
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MURFAI_API_KEY = os.getenv("MURFAI_API_KEY")
MURFAI_USER_ID = os.getenv("MURFAI_USER_ID")

# Try to import LangChain components with fallback
LANGCHAIN_AVAILABLE = False
llm_chain = None

try:
    from langchain_openai import ChatOpenAI
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    from langchain.memory import ConversationBufferMemory
    LANGCHAIN_AVAILABLE = True
    print("✓ LangChain imports successful")
except ImportError as e:
    print(f"⚠ LangChain import error: {e}")
    print("⚠ Continuing with fallback text responses")

# Initialize LangChain only if available and API key is present
if LANGCHAIN_AVAILABLE and OPENAI_API_KEY:
    try:
        template = """As an adventurous and globetrotting college student, you're constantly on the lookout for new cultures, experiences, and breathtaking landscapes. You've visited numerous countries, immersing yourself in local traditions, and you're always eager to swap travel stories and offer tips on exciting destinations.
        {chat_history}
        User: {user_message}
        Chatbot:"""

        prompt = PromptTemplate(
            input_variables=["chat_history", "user_message"], 
            template=template
        )

        memory = ConversationBufferMemory(memory_key="chat_history")

        llm_chain = LLMChain(
            llm=ChatOpenAI(
                temperature=0.5, 
                model_name="gpt-3.5-turbo",
                openai_api_key=OPENAI_API_KEY
            ),
            prompt=prompt,
            verbose=False,
            memory=memory,
        )
        print("✓ LangChain initialized successfully")
    except Exception as e:
        print(f"⚠ LangChain initialization failed: {e}")
        llm_chain = None
else:
    if not OPENAI_API_KEY:
        print("⚠ OPENAI_API_KEY not set")
    if not LANGCHAIN_AVAILABLE:
        print("⚠ LangChain not available")

# Fallback responses if LangChain fails
FALLBACK_RESPONSES = {
    "travel experience": "One of my most memorable travel experiences was hiking through the Swiss Alps at sunrise. The way the light hit the snow-capped peaks was absolutely magical!",
    "hidden gem": "I discovered this incredible little island in Thailand called Koh Lipe. It's not as crowded as the other islands, with crystal clear water and amazing snorkeling right off the beach!",
    "prepare for trip": "I always research local customs first, learn a few basic phrases in the local language, pack light but smart, and make sure to try the street food - it's often the most authentic!",
    "adventure sport": "I tried paragliding in Nepal over the Himalayas - absolutely breathtaking views and such an adrenaline rush!",
    "one country": "That's tough! I'd probably choose Japan - it has this perfect blend of ancient tradition and futuristic innovation, amazing food, and the people are incredibly kind."
}

def get_fallback_response(message):
    """Provide fallback responses when LangChain is unavailable"""
    message_lower = message.lower()
    
    if "memorable" in message_lower or "experience" in message_lower:
        return FALLBACK_RESPONSES["travel experience"]
    elif "hidden" in message_lower or "gem" in message_lower:
        return FALLBACK_RESPONSES["hidden gem"]
    elif "prepare" in message_lower or "culture" in message_lower:
        return FALLBACK_RESPONSES["prepare for trip"]
    elif "adventure" in message_lower or "sport" in message_lower:
        return FALLBACK_RESPONSES["adventure sport"]
    elif "one country" in message_lower or "rest of your life" in message_lower:
        return FALLBACK_RESPONSES["one country"]
    else:
        return "I'd love to share more about my travel adventures! While I'm having some technical difficulties with my full capabilities, I can tell you about amazing destinations, travel tips, or cultural experiences. What would you like to know?"

def get_text_response(user_message):
    """Get text response from LLM or fallback"""
    if llm_chain and OPENAI_API_KEY:
        try:
            response = llm_chain.predict(user_message=user_message)
            return response
        except Exception as e:
            print(f"LLM chain error: {e}")
            return get_fallback_response(user_message)
    else:
        return get_fallback_response(user_message)

# Murf AI Configuration
MURFAI_URL = "https://api.murf.ai/v1/speech/generate"
MURF_VOICE_ID = "Caleb"

headers_murf = {
    "accept": "application/json",
    "content-type": "application/json",
    "Authorization": f"Bearer {MURFAI_API_KEY}",
}

def get_generated_audio(text):
    """Generate audio using Murf AI API"""
    if not MURFAI_API_KEY:
        return {
            "type": "ERROR",
            "audio_url": "",
            "response": "Murf AI API key not configured"
        }
    
    payload = {
        "voiceId": MURF_VOICE_ID,
        "text": text,
        "format": "MP3"
    }
    
    generated_response = {
        "type": "",
        "audio_url": "",
        "response": ""
    }
    
    try:
        response = requests.post(MURFAI_URL, json=payload, headers=headers_murf, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Murf returns audioFile directly
        audio_url = data.get("audioFile", "")
        if audio_url:
            generated_response["type"] = "SUCCESS"
            generated_response["audio_url"] = audio_url
            generated_response["response"] = data
        else:
            generated_response["type"] = "ERROR"
            generated_response["response"] = f"No audio URL returned. Response: {data}"
            
    except requests.exceptions.RequestException as e:
        generated_response["type"] = "ERROR"
        generated_response["response"] = f"API Request failed: {str(e)}"
    except Exception as e:
        generated_response["type"] = "ERROR"
        generated_response["response"] = f"Unexpected error: {str(e)}"
        
    return generated_response

def download_audio_file(url):
    """Download audio file from URL"""
    final_response = {
        "content": None,
        "error": "",
        "filename": ""
    }
    
    try:
        response = requests.get(url, timeout=15, stream=True)
        
        if response.status_code != 200:
            final_response["error"] = f"Download failed. Status: {response.status_code}"
            return final_response
            
        content_type = response.headers.get("Content-Type", "")
        
        # Generate filename
        import hashlib
        filename_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        filename = f"audio_{filename_hash}.mp3"
        content = response.content
        
        final_response["content"] = content
        final_response["filename"] = filename
        
    except Exception as e:
        final_response["error"] = f"Download error: {str(e)}"
        
    return final_response

def get_text_and_audio_response(user_message):
    """Get both text and audio responses"""
    # 1. Get text response
    text_reply = get_text_response(user_message)

    # 2. Generate audio (if Murf AI is configured)
    if MURFAI_API_KEY:
        audio_event = get_generated_audio(text_reply)
        
        if audio_event["type"] == "SUCCESS":
            audio_url = audio_event["audio_url"]
            
            # 3. Download audio file
            download_result = download_audio_file(audio_url)
            
            if not download_result["error"]:
                # Save audio file
                filename = download_result["filename"]
                with open(filename, "wb") as f:
                    f.write(download_result["content"])
                return text_reply, filename
    
    # Return text only if audio generation fails or Murf AI not configured
    return text_reply, None

def chat_bot_response(message, history):
    """Gradio chat interface response handler"""
    text_reply, audio_file = get_text_and_audio_response(message)
    
    # Update chat history
    if history is None:
        history = []
    history.append((message, text_reply))
    
    # Return both text and audio if available
    if audio_file and os.path.exists(audio_file):
        return history, history, audio_file
    
    # Return only text if audio failed
    return history, history, None

# Create Gradio interface
with gr.Blocks(title="🌍 Travel Voice Chatbot", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🌍 Travel Voice Chatbot")
    gr.Markdown("Chat with an adventurous travel bot! Responses are spoken using Murf AI.")
    
    if not LANGCHAIN_AVAILABLE:
        gr.Markdown("> ⚠ **Note**: Running in fallback mode. Some features may be limited.")
    if not OPENAI_API_KEY:
        gr.Markdown("> ⚠ **Note**: OpenAI API key not configured. Using fallback responses.")
    if not MURFAI_API_KEY:
        gr.Markdown("> ⚠ **Note**: Murf AI API key not configured. Audio responses disabled.")
    
    chatbot = gr.Chatbot(height=800, label="Travel Chat")
    
    with gr.Row():
        msg = gr.Textbox(
            label="Your message",
            placeholder="Ask about travel experiences, destinations, or tips...",
            lines=5,
            scale=4
        )
        submit_btn = gr.Button("Send", variant="primary", scale=1)
    
    audio_output = gr.Audio(label="Voice Response", autoplay=True)
    clear_btn = gr.Button("Clear Chat")
    
    examples = gr.Examples(
        examples=[
            "What's the most memorable travel experience you've had so far?",
            "Share a hidden gem destination that you discovered during your travels.",
            "How do you prepare for a trip to a new country with a different culture?",
            "Tell me about an exciting activity or adventure sport you've tried during your travels.",
            "If you could only visit one country for the rest of your life, which one would it be, and why?"
        ],
        inputs=msg,
        label="Example Questions"
    )
    
    def respond(message, chat_history):
        new_history, _, audio = chat_bot_response(message, chat_history)
        return "", new_history, audio
    
    msg.submit(
        respond,
        [msg, chatbot],
        [msg, chatbot, audio_output]
    )
    
    submit_btn.click(
        respond,
        [msg, chatbot],
        [msg, chatbot, audio_output]
    )
    
    clear_btn.click(
        lambda: ([], None),
        outputs=[chatbot, audio_output]
    )

if __name__ == "__main__":
    demo.launch(share=False, debug=True)
