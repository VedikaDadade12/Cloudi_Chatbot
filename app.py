# app.py – Cloudi ☁️ AI Internship Chatbot

import json
import difflib
import random
import string
import os
import requests
import openai
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, session, redirect, url_for, request, render_template, flash
from twilio.twiml.messaging_response import MessagingResponse

# Load environment variables
load_dotenv()

# OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Twilio (WhatsApp & SMS)
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

# Admin
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Flask secret key
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Facebook & Instagram
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID")
INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Check critical envs
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY missing.")
if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_PHONE]):
    raise ValueError("Twilio credentials missing.")
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY missing.")

# ----------- Utility Functions -----------

# Normalize text by lowercasing, stripping whitespace, and removing punctuation
def normalize(text):
    text = text.lower().strip()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return " ".join(text.split())

# Stylize the response with a random prefix
def stylize_response(answer):
    prefixes = [
        "Sure thing! Here's what I found for you ☁️\n\n",
        "Here's the info you asked for 📘\n\n",
        "Let me explain that for you 🧓\n\n"
    ]
    return random.choice(prefixes) + answer

# Log unknown questions to a JSON file
def log_unknown_question(question):
    log_file = 'learning_log.json'
    log_entry = {
        "question": question,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    if not os.path.exists(log_file):
        with open(log_file, 'w') as file:
            json.dump([log_entry], file, indent=4)
    else:
        with open(log_file, 'r+') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
            data.append(log_entry)
            file.seek(0)
            json.dump(data, file, indent=4)

# Apply personality to the response based on mood
def apply_personality(response, mood, prefix=True):
    if prefix and random.random() < 0.5:
        response = stylize_response(response)
    if mood == "friendly":
        return response
    elif mood == "formal":
        return "Certainly. " + response
    elif mood == "funny":
        return response + " 😄"
    elif mood == "motivational":
        return response + " Keep going, you're doing great! 🚀"
    else:
        return response

# Get Cloudi's response based on user input
def get_cloudi_response(user_input, mood="formal"):
    normalized_input = normalize(user_input)
    casual_keys = list(casual_replies.keys())
    closest_match = difflib.get_close_matches(normalized_input, casual_keys, n=1, cutoff=0.7)
    if closest_match:
        reply = casual_replies[closest_match[0]]
        print("✅ Matched casual:", closest_match[0])
        return apply_personality(reply, mood, prefix=False)

    closest_match = difflib.get_close_matches(normalized_input, faq.keys(), n=1, cutoff=0.85)
    if closest_match:
        matched_answer = faq[closest_match[0]]
        return apply_personality(matched_answer, mood, prefix=True)

    log_unknown_question(user_input)
    gpt_reply = get_fallback_from_gpt(user_input)
    print("🤖 GPT fallback:", gpt_reply)
    return apply_personality(gpt_reply, mood, prefix=True)

# Get fallback response from GPT
def get_fallback_from_gpt(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You're Cloudi ☁️, a friendly AI assistant helping with academic, career, and personal guidance."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        print("GPT error:", e)
        return "Oops! I'm having trouble reaching my brain right now. ☁️💤"


casual_replies = {
    "hi": "Hey there! 👋",
    "hello": "Hi! How can I help you today? 😊",
    "hey": "Heyy! I'm here for you ☁️",
    "how are you": "I'm just a cloud, but thanks for asking! ☁️ How about you?",
    "what's up": "Not much, just floating around! ☁️ What's up with you?",
    "help": "Sure! What do you need help with? 🤔",
    "thanks": "You're welcome! 😊 If you need anything else, just ask!",
    "thank you": "No problem! I'm here to help! 😊",
    "bye": "Goodbye! Take care! 👋",
    "goodbye": "See you later! ☁️",
    "good morning": "Good morning! ☀️ Let's make today productive!",
    "good evening": "Good evening! 🌙 How was your day?"
}

@app.route('/chat', methods=['POST'])
def chat():
    original_input = request.form['message'].strip()
    mood = request.form.get("personality") or session.get("personality", "formal")
    session["personality"] = mood

    lower_input = original_input.lower()
    is_casual = lower_input in casual_replies

    if is_casual:
        response = casual_replies[lower_input]
    else:
        response = get_cloudi_response(original_input, mood)

    update_analytics(mood)
    session.setdefault("history", []).append({"question": original_input, "answer": response})
    session.modified = True

    return render_template(
        "response.html",
        question=original_input,
        answer=response,
        history=session["history"],
        is_casual=is_casual
    )

# Save SMS log to a JSON file
def save_sms_log(phone, message):
    log = {
        "phone": phone,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    logs = []
    if os.path.exists("sms_logs.json"):
        with open("sms_logs.json", "r") as file:
            try:
                logs = json.load(file)
            except:
                logs = []
    logs.append(log)
    with open("sms_logs.json", "w") as file:
        json.dump(logs, file, indent=4)

# Update analytics data
def update_analytics(mood, source="web"):
    try:
        with open("analytics.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {
            "total_chats": 0,
            "sources": {"web": 0},
            "personalities": {"formal": 0, "friendly": 0, "motivational": 0, "sassy": 0},
            "feedback": {"positive": 0, "negative": 0}
        }

    data["total_chats"] += 1
    data["sources"][source] = data["sources"].get(source, 0) + 1
    data["personalities"][mood] = data["personalities"].get(mood, 0) + 1

    with open("analytics.json", "w") as f:
        json.dump(data, f, indent=4)

# ----------- Data Loading -----------

with open('faq_data.json', 'r') as file:
    raw_faq = json.load(file)
    faq = {normalize(k): v for k, v in raw_faq.items()}


# ----------- Routes -----------

# Home Page
@app.route('/')
def home():
    return render_template("chat.html", intro_message="Hi, I'm Cloudi ☁️!", sub_message="Ask anything about internships, IAC, domains, docs...")


# Reset chat history
@app.route('/reset')
def reset():
    session.pop('history', None)
    return redirect(url_for('home'))

# Admin Routes
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == os.getenv("ADMIN_USERNAME") and password == os.getenv("ADMIN_PASSWORD"):
            session["admin_logged_in"] = True
            return redirect("/analytics")
        else:
            flash("Invalid credentials", "error")
    return render_template("admin_login.html")

# Admin Logs
@app.route('/sms-logs')
def sms_logs():
    try:
        with open('sms_logs.json', 'r') as file:
            logs = json.load(file)
    except:
        logs = []
    return render_template('sms_logs.html', logs=logs)

# Admin Analytics
@app.route("/analytics")
def analytics():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")

    with open("analytics.json", "r") as f:
        data = json.load(f)

    return render_template("analytics.html", analytics=data)

# Clear SMS logs
@app.route('/clear-sms-logs', methods=['POST'])
def clear_sms_logs():
    with open('sms_logs.json', 'w') as f:
        json.dump([], f)
    return redirect(url_for('sms_logs'))

# Logout
@app.route("/logout", methods=["POST"])
def logout():
    session.pop("admin_logged_in", None)
    return redirect("/admin-login")


# Feedback Submission
@app.route("/submit-feedback", methods=["POST"])
def submit_feedback():
    feedback = request.form.get("feedback")
    question = request.form.get("question")
    answer = request.form.get("answer")

    feedback_entry = {
        "question": question,
        "answer": answer,
        "feedback": feedback,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    feedback_file = "feedback.json"
    if os.path.exists(feedback_file):
        with open(feedback_file, "r+") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
            data.append(feedback_entry)
            f.seek(0)
            json.dump(data, f, indent=4)
    else:
        with open(feedback_file, "w") as f:
            json.dump([feedback_entry], f, indent=4)

    flash("✅ Thanks for your feedback!")
    return redirect(url_for("home"))


# ----------- Webhooks -----------

@app.route("/webhook/facebook", methods=["GET", "POST"])
def fb_webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Invalid", 403

    data = request.get_json()
    try:
        messaging_event = data["entry"][0]["messaging"][0]
        if "message" in messaging_event and "text" in messaging_event["message"]:
            sender = messaging_event["sender"]["id"]
            user_input = messaging_event["message"]["text"]
            reply = get_cloudi_response(user_input)
            send_facebook_reply(sender, reply)
    except Exception as e:
        print("Facebook webhook error:", e)
    return "ok", 200

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    user_input = request.values.get('Body', '')
    phone = request.values.get('From', '').replace("whatsapp:", "")
    reply = get_cloudi_response(user_input)
    send_whatsapp_reply(phone, reply)
    return "ok", 200

@app.route('/webhook/instagram', methods=['GET', 'POST'])
def instagram_webhook():
    if request.method == 'GET':
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "Forbidden", 403
    if request.method == 'POST':
        data = request.get_json()
        print("📩 New Instagram Message:", data)
        return "EVENT_RECEIVED", 200

@app.route('/webhook/sms', methods=['POST'])
def sms_webhook():
    user_input = request.values.get('Body', '')
    phone = request.values.get('From', '')
    reply = get_cloudi_response(user_input)
    save_sms_log(phone, user_input)

    log_entry = {
        "from": phone,
        "question": user_input,
        "answer": reply,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    sms_log_file = 'sms_history.json'
    logs = []
    if os.path.exists(sms_log_file):
        with open(sms_log_file, 'r') as f:
            try:
                logs = json.load(f)
            except:
                logs = []
    logs.append(log_entry)
    with open(sms_log_file, 'w') as f:
        json.dump(logs, f, indent=4)

    return f"<Response><Message>{reply}</Message></Response>", 200

# ----------- Send Functions -----------

def send_whatsapp_reply(phone, message):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    data = {
        "From": TWILIO_PHONE,
        "To": f"whatsapp:{phone}",
        "Body": message
    }
    requests.post(url, data=data, auth=(TWILIO_SID, TWILIO_TOKEN))

def send_facebook_reply(recipient_id, message):
    url = "https://graph.facebook.com/v18.0/me/messages"
    headers = {"Content-Type": "application/json"}
    params = {"access_token": FB_PAGE_ACCESS_TOKEN}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message}
    }
    requests.post(url, params=params, headers=headers, json=payload)

def send_instagram_reply(user_id, text):
    url = "https://graph.facebook.com/v18.0/me/messages"
    headers = {"Content-Type": "application/json"}
    params = {"access_token": INSTAGRAM_ACCESS_TOKEN}
    payload = {
        "recipient": {"id": user_id},
        "message": {"text": text}
    }
    requests.post(url, params=params, headers=headers, json=payload)

def send_sms(to, message):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    data = {
        "From": TWILIO_PHONE,
        "To": to,
        "Body": message
    }
    requests.post(url, data=data, auth=(TWILIO_SID, TWILIO_TOKEN))

# ----------- Run App -----------
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
