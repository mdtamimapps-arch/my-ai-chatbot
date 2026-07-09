import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# ===============================================
# 🔐 Google Sheets সংযোগ (Environment Variable থেকে)
# ===============================================
def get_credentials():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS Environment Variable সেট করা হয়নি!")
    creds_dict = json.loads(creds_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

def get_sheet_data():
    creds = get_credentials()
    client = gspread.authorize(creds)
    sheet1 = client.open("মিলের হিসাব").sheet1
    sheet2 = client.open("বাসা ভাড়া").sheet1
    data1 = sheet1.get_all_values()
    data2 = sheet2.get_all_values()
    text_data = "📊 শীট ১ (মিলের হিসাব):\n"
    for row in data1:
        text_data += ", ".join(row) + "\n"
    text_data += "\n📊 শীট ২ (বাসা ভাড়া ও বিল):\n"
    for row in data2:
        text_data += ", ".join(row) + "\n"
    return text_data

# ===============================================
# 🧠 Groq AI সেটআপ (Environment Variable থেকে)
# ===============================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY Environment Variable সেট করা হয়নি!")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

def get_ai_response(user_question):
    sheet_data = get_sheet_data()
    prompt = f"""
তুমি একজন ডেটা অ্যানালিস্ট। নিচের ডেটা বিশ্লেষণ করে প্রশ্নের উত্তর দাও।

ডেটা:
{sheet_data}

প্রশ্ন: {user_question}

নির্দেশনা:
১. শুধু ডেটার ভিত্তিতে উত্তর দাও।
২. ডেটাতে উত্তর না থাকলে স্পষ্টভাবে বলে দাও।
৩. বাংলায় উত্তর দাও।
৪. প্রয়োজনে যোগ-বিয়োগ ও বিশ্লেষণ করো।
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # অথবা "llama-3.3-70b-versatile"
            messages=[
                {"role": "system", "content": "তুমি একজন ডেটা অ্যানালিস্ট।"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Groq API ত্রুটি: {str(e)}"

# ===============================================
# 🌐 ওয়েব রুট (পেজ ও এপিআই)
# ===============================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    user_question = data.get('question', '')
    if not user_question:
        return jsonify({'error': 'কোনো প্রশ্ন পাওয়া যায়নি'}), 400
    try:
        answer = get_ai_response(user_question)
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
