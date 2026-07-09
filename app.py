import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# .env ফাইল থেকে লোড (যদি লোকালে ব্যবহার করেন)
load_dotenv()

app = Flask(__name__)

# ===============================================
# 🔐 Google Sheets সংযোগ (Environment Variable থেকে)
# ===============================================
def get_credentials():
    """GOOGLE_CREDENTIALS এনভায়রনমেন্ট ভেরিয়েবল থেকে JSON লোড করে Credentials তৈরি করে"""
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS Environment Variable সেট করা হয়নি!")
    try:
        creds_dict = json.loads(creds_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"GOOGLE_CREDENTIALS JSON ডিকোড করতে ব্যর্থ: {e}")
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

def get_sheet_data():
    """দুটি গুগল শীট থেকে সব ডেটা পড়ে টেক্সট আকারে রিটার্ন করে"""
    creds = get_credentials()
    client = gspread.authorize(creds)

    # আপনার শীটের নাম (ড্রাইভে যেভাবে আছে)
    try:
        sheet1 = client.open("মিলের হিসাব").sheet1
        sheet2 = client.open("বাসা ভাড়া").sheet1
    except gspread.exceptions.SpreadsheetNotFound:
        # নাম দিয়ে না পেলে ID ব্যবহার করুন (নিচে আনকমেন্ট করুন)
        # SHEET1_ID = "1vUo7IGmVJXB0-FcduSVk7_fHGSUxZfk0c3Q-nOIco0U"
        # SHEET2_ID = "1YFnyNrBJTnXIIb0tYh6uAsXRHNzboRMdQotUuUZO_gQ"
        # sheet1 = client.open_by_key(SHEET1_ID).sheet1
        # sheet2 = client.open_by_key(SHEET2_ID).sheet1
        raise Exception("শীট খুঁজে পাওয়া যায়নি! নাম বা ID চেক করুন।")

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
# 🧠 Gemini AI সেটআপ (এনভায়রনমেন্ট ভেরিয়েবল থেকে)
# ===============================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY Environment Variable সেট করা হয়নি! Google AI Studio থেকে Key নিয়ে Set করুন।")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')  # অথবা 'gemini-1.5-flash'

def get_ai_response(user_question):
    """শীটের ডেটা পড়ে জেমিনিকে প্রশ্ন পাঠায় ও উত্তর নিয়ে আসে"""
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
    response = model.generate_content(prompt)
    return response.text

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

# ===============================================
# 🚀 অ্যাপ চালু করা
# ===============================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
