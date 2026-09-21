import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

load_dotenv('/home/hermes/doshie/.env')

app = Flask(__name__)

# Initialize client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Preferred models in priority order
MODELS = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-3.5-flash-lite",
]

SYSTEM_INSTRUCTION = "You are Doshie, a helpful, intelligent personal AI assistant running locally on Kali Linux."

chat_session = None
current_model = None

def init_chat_session():
    global chat_session, current_model
    for model_name in MODELS:
        try:
            chat_session = client.chats.create(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                )
            )
            current_model = model_name
            print(f"Initialized Doshie chat session with {model_name}")
            return chat_session
        except Exception as e:
            print(f"Failed to init chat session with {model_name}: {e}")
    chat_session = None
    current_model = None
    return None

init_chat_session()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    global chat_session, current_model
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'reply': 'Please enter a message.'}), 400

    reply_text = None
    last_error = None

    # Try existing chat_session first if available
    if chat_session:
        try:
            response = chat_session.send_message(user_message)
            reply_text = response.text
        except Exception as e:
            last_error = e
            print(f"Error sending message with {current_model}: {e}")
            chat_session = None

    # If send_message failed or no chat_session, attempt with candidate models
    if not reply_text:
        for model_name in MODELS:
            try:
                new_session = client.chats.create(
                    model=model_name,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION
                    )
                )
                response = new_session.send_message(user_message)
                reply_text = response.text
                chat_session = new_session
                current_model = model_name
                break
            except Exception as err:
                last_error = err
                print(f"Model {model_name} failed: {err}")
                continue

    if not reply_text:
        reply_text = f"Error communicating with Gemini: {str(last_error)}"

    return jsonify({'reply': reply_text, 'model': current_model})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
