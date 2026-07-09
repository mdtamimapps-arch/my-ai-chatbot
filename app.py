import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# .env ফাইল থেকে API Key লোড করা (নিরাপত্তার জন্য)
load_dotenv()

app = Flask(__name__)

# ------------------- ১. গুগল শীটস কানেক্ট করা -------------------
def get_sheet_data():
    """গুগল শীট থেকে সব ডেটা পড়ে টেক্সট আকারে রিটার্ন করে"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # credentials.json ফাইলটি অবশ্যই এই ফোল্ডারে থাকতে হবে
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    # 📌 এখানে আপনার শীটের নাম দিন (যেমন: "Mess Bill" বা শীটের URL)
    sheet = client.open("আপনার_শীটের_নাম_এখানে").sheet1
    data = sheet.get_all_values()
    
    # ডেটাকে লাইন বাই লাইন টেক্সটে কনভার্ট করা
    text_data = ""
    for row in data:
        text_data += ", ".join(row) + "\n"
    return text_data

# ------------------- ২. জেমিনি এআই সেটআপ -------------------
# Render-এ Environment Variable হিসেবে GEMINI_API_KEY সেট করুন
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY Environment Variable সেট করা হয়নি!")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')  # অথবা 'gemini-1.5-flash'

# ------------------- ৩. এআই রেসপন্স ফাংশন -------------------
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
"""
    response = model.generate_content(prompt)
    return response.text

# ------------------- ৪. ওয়েব রুট (পেজ ও এপিআই) -------------------
@app.route('/')
def index():
    """হোম পেজ দেখায়"""
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    """ইউজারের প্রশ্ন নিয়ে উত্তর ফেরত দেয়"""
    data = request.get_json()
    user_question = data.get('question', '')
    
    if not user_question:
        return jsonify({'error': 'কোনো প্রশ্ন পাওয়া যায়নি'}), 400
    
    try:
        answer = get_ai_response(user_question)
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ------------------- ৫. অ্যাপ চালু করা -------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
