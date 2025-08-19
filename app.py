# app.py – Cloudi ☁️ AI Internship Chatbot - Simple Enhancements

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

# ----------- Simple Improvements -----------

def normalize(text):
    if not text:
        return ""
    text = text.lower().strip()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return " ".join(text.split())

def stylize_response(answer):
    prefixes = [
        "Sure thing! Here's what I found for you ☁️\n\n",
        "Here's the info you asked for 📘\n\n",
        "Let me explain that for you 🧓\n\n",
        "Great question! Here's what I know ✨\n\n",
        "I've got you covered! 🎯\n\n"
    ]
    return random.choice(prefixes) + answer

# IMPROVEMENT 1: Better error handling for logging
def log_unknown_question(question):
    log_file = 'learning_log.json'
    log_entry = {
        "question": question,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
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
                file.truncate()  # Remove any leftover content
    except Exception as e:
        print(f"Error logging question: {e}")

# IMPROVEMENT 2: Input validation (simple but effective)
def is_valid_input(user_input):
    if not user_input or len(user_input.strip()) == 0:
        return False, "Please enter a message"
    if len(user_input) > 500:
        return False, "Message too long. Please keep it under 500 characters."
    return True, ""

def apply_personality(response, mood, prefix=True):
    if prefix and random.random() < 0.5:
        response = stylize_response(response)
    if mood == "friendly":
        return response + " 😊"
    elif mood == "formal":
        return "Certainly. " + response
    elif mood == "funny":
        return response + " 😄"
    elif mood == "motivational":
        return response + " Keep going, you're doing great! 🚀"
    elif mood == "sassy":  # NEW personality option
        return "Well, " + response + " 💅"
    else:
        return response

# IMPROVEMENT 3: Better GPT error handling
def get_fallback_from_gpt(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You're Cloudi ☁️, a friendly AI assistant helping with academic, career, and personal guidance. Keep responses helpful and under 200 words."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message['content'].strip()
    except openai.error.RateLimitError:
        return "I'm getting lots of questions right now! Please try again in a moment. ☁️"
    except openai.error.InvalidRequestError:
        return "I didn't quite understand that. Could you rephrase your question? 🤔"
    except Exception as e:
        print("GPT error:", e)
        return "Oops! I'm having trouble thinking right now. Please try again! ☁️💤"

def get_cloudi_response(user_input, mood="formal"):
    # IMPROVEMENT 4: Add input validation
    valid, error_msg = is_valid_input(user_input)
    if not valid:
        return error_msg
    
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

# IMPROVEMENT 5: More casual replies
casual_replies = {
    "hi": "Hey there! 👋",
    "hello": "Hi! How can I help you today? 😊",
    "hey": "Heyy! I'm here for you ☁️",
    "how are you": "I'm just a cloud, but thanks for asking! ☁️ How about you?",
    "what's up": "Not much, just floating around! ☁️ What's up with you?",
    "whats up": "Not much, just floating around! ☁️ What's up with you?",
    "help": "Sure! What do you need help with? 🤔",
    "thanks": "You're welcome! 😊 If you need anything else, just ask!",
    "thank you": "No problem! I'm here to help! 😊",
    "thx": "Anytime! 😊",
    "bye": "Goodbye! Take care! 👋",
    "goodbye": "See you later! ☁️",
    "good morning": "Good morning! ☀️ Let's make today productive!",
    "good evening": "Good evening! 🌙 How was your day?",
    "good night": "Good night! Sweet dreams! 🌙✨",
    "who are you": "I'm Cloudi ☁️, your friendly AI assistant!",
    "what is your name": "I'm Cloudi ☁️! Nice to meet you!",
    # NEW casual replies
    "lol": "Haha, glad I could make you laugh! 😄",
    "awesome": "I'm so happy you think so! ⭐",
    "cool": "Right? Pretty cool stuff! 😎",
    "wow": "I know, right? 🤩",
    "nice": "Thanks! I try my best! 😊"
}

@app.route('/chat', methods=['POST'])
def chat():
    try:
        original_input = request.form['message'].strip()
        
        # IMPROVEMENT 6: Check for empty input
        if not original_input:
            flash("Please type something before sending! 😊", "error")
            return redirect(url_for('home'))
        
        mood = request.form.get("personality") or session.get("personality", "formal")
        session["personality"] = mood

        lower_input = original_input.lower()
        is_casual = lower_input in casual_replies

        if is_casual:
            response = casual_replies[lower_input]
        else:
            response = get_cloudi_response(original_input, mood)

        update_analytics(mood)
        
        # IMPROVEMENT 7: Better session history management
        if "history" not in session:
            session["history"] = []
        
        session["history"].append({
            "question": original_input, 
            "answer": response,
            "timestamp": datetime.now().strftime("%H:%M")  # Show time
        })
        
        # Keep only last 8 conversations (instead of unlimited)
        if len(session["history"]) > 8:
            session["history"] = session["history"][-8:]
        
        session.modified = True

        return render_template(
            "response.html",
            question=original_input,
            answer=response,
            history=session["history"],
            is_casual=is_casual
        )
    
    except Exception as e:
        print(f"Chat error: {e}")
        flash("Something went wrong! Please try again. 🤖", "error")
        return redirect(url_for('home'))

# IMPROVEMENT 8: Better SMS logging
def save_sms_log(phone, message):
    log = {
        "phone": phone,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        logs = []
        if os.path.exists("sms_logs.json"):
            with open("sms_logs.json", "r") as file:
                try:
                    logs = json.load(file)
                except json.JSONDecodeError:
                    logs = []
        
        logs.append(log)
        
        # Keep only last 100 SMS logs to prevent file from getting huge
        if len(logs) > 100:
            logs = logs[-100:]
        
        with open("sms_logs.json", "w") as file:
            json.dump(logs, file, indent=4)
    except Exception as e:
        print(f"Error saving SMS log: {e}")

# IMPROVEMENT 9: Enhanced analytics with daily tracking
def update_analytics(mood, source="web"):
    try:
        with open("analytics.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {
            "total_chats": 0,
            "sources": {"web": 0},
            "personalities": {"formal": 0, "friendly": 0, "motivational": 0, "funny": 0, "sassy": 0},
            "feedback": {"positive": 0, "negative": 0},
            "today_chats": 0,
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        }

    # Reset daily counter if it's a new day
    today = datetime.now().strftime("%Y-%m-%d")
    if data.get("last_updated") != today:
        data["today_chats"] = 0
        data["last_updated"] = today

    data["total_chats"] += 1
    data["today_chats"] += 1
    data["sources"][source] = data["sources"].get(source, 0) + 1
    data["personalities"][mood] = data["personalities"].get(mood, 0) + 1

    with open("analytics.json", "w") as f:
        json.dump(data, f, indent=4)

# IMPROVEMENT 10: Load FAQ with better error handling
try:
    with open('faq_data.json', 'r') as file:
        raw_faq = json.load(file)
        faq = {normalize(k): v for k, v in raw_faq.items()}
        print(f"✅ Loaded {len(faq)} FAQ entries")
except FileNotFoundError:
    print("⚠️ FAQ file not found, creating empty one...")
    faq = {}
    # Create empty FAQ file
    with open('faq_data.json', 'w') as file:
        json.dump({"hello": "Hi there! Welcome to Cloudi!"}, file, indent=4)
except Exception as e:
    print(f"❌ Error loading FAQ: {e}")
    faq = {}

# ----------- Routes (Minor Improvements) -----------

@app.route('/')
def home():
    # IMPROVEMENT 11: Show some stats on home page
    total_conversations = len(session.get("history", []))
    return render_template(
        "chat.html", 
        intro_message="Hi, I'm Cloudi ☁️!", 
        sub_message="Ask anything about internships, IAC, domains, docs...",
        conversation_count=total_conversations
    )

@app.route('/reset')
def reset():
    session.pop('history', None)
    flash("✨ Chat cleared! Ready for new questions.", "success")
    return redirect(url_for('home'))

# IMPROVEMENT 12: Enhanced admin analytics
@app.route("/analytics")
def analytics():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")

    try:
        with open("analytics.json", "r") as f:
            data = json.load(f)
        
        # Calculate most popular personality
        personalities = data.get("personalities", {})
        most_popular = max(personalities, key=personalities.get) if personalities else "formal"
        
        return render_template("analytics.html", 
                             analytics=data,
                             most_popular_personality=most_popular)
    except Exception as e:
        print(f"Analytics error: {e}")
        flash("Error loading analytics!", "error")
        return redirect("/admin-login")

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == os.getenv("ADMIN_USERNAME") and password == os.getenv("ADMIN_PASSWORD"):
            session["admin_logged_in"] = True
            flash("Welcome back! 👋", "success")
            return redirect("/analytics")
        else:
            flash("Wrong username or password! 🔐", "error")
    return render_template("admin_login.html")

@app.route('/sms-logs')
def sms_logs():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")
    
    try:
        with open('sms_logs.json', 'r') as file:
            logs = json.load(file)
        # Show newest first
        logs.reverse()
    except:
        logs = []
    return render_template('sms_logs.html', logs=logs, total_logs=len(logs))

@app.route('/clear-sms-logs', methods=['POST'])
def clear_sms_logs():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")
    
    with open('sms_logs.json', 'w') as f:
        json.dump([], f)
    flash("SMS logs cleared! 🗑️", "success")
    return redirect(url_for('sms_logs'))

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("admin_logged_in", None)
    flash("See you later! 👋", "success")
    return redirect("/admin-login")

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

    # IMPROVEMENT 13: Better feedback handling
    try:
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
                f.truncate()
        else:
            with open(feedback_file, "w") as f:
                json.dump([feedback_entry], f, indent=4)

        flash("✅ Thanks for your feedback! It really helps me improve.", "success")
    except Exception as e:
        print(f"Feedback error: {e}")
        flash("Oops! Couldn't save your feedback. Please try again.", "error")
    
    return redirect(url_for("home"))

# ----------- Webhooks (Same but with better error messages) -----------

@app.route("/webhook/facebook", methods=["GET", "POST"])
def fb_webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Invalid", 403

    try:
        data = request.get_json()
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
    try:
        user_input = request.values.get('Body', '')
        phone = request.values.get('From', '').replace("whatsapp:", "")
        reply = get_cloudi_response(user_input)
        send_whatsapp_reply(phone, reply)
    except Exception as e:
        print("WhatsApp webhook error:", e)
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
    try:
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
    except Exception as e:
        print("SMS webhook error:", e)
        return "ok", 200

# ----------- Send Functions (Same) -----------

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
    print("🚀 Starting Cloudi Chatbot...")
    print(f"📚 FAQ entries: {len(faq)}")
    print(f"💬 Casual replies: {len(casual_replies)}")

# app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
