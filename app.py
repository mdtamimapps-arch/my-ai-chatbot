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
# 🔐 Google Sheets সংযোগ
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
    text_data += "\n📊 শীট ২ (বাসা ভাড়া ও অন্যান্য খরচ):\n"
    for row in data2:
        text_data += ", ".join(row) + "\n"
    return text_data

# ===============================================
# 🧠 Groq AI সেটআপ
# ===============================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY Environment Variable সেট করা হয়নি!")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ===============================================
# 💬 স্মার্ট প্রম্পট (ChatGPT-স্টাইল)
# ===============================================
def get_ai_response(user_question):
    sheet_data = get_sheet_data()
    
    system_prompt = """
তুমি একজন বুদ্ধিমান ও বন্ধুসুলভ AI সহায়ক। তোমার নাম 'মেসবট'।
তোমার কাজ হলো ব্যবহারকারীর সাথে স্বাভাবিক কথোপকথন করা এবং প্রয়োজনে তাদের Google Sheets-এর ডেটা বিশ্লেষণ করে উত্তর দেওয়া।

নির্দেশনা:
১. প্রথমে ব্যবহারকারীকে অভিবাদন জানাও এবং তার নাম জিজ্ঞেস করো (যদি না সে আগেই বলে থাকে)।
২. যদি ব্যবহারকারী তার নাম বলে, তবে পরবর্তী সব কথোপকথনে তাকে সেই নাম ধরে সম্বোধন করো।
৩. সাধারণ কথোপকথনের জন্য (যেমন: হাই, হ্যালো, সালাম, কেমন আছো, কী খবর, ইত্যাদি) ডেটা বিশ্লেষণ করো না, বরং বন্ধুসুলভ ও উষ্ণ উত্তর দাও।
৪. যদি ব্যবহারকারী ডেটা সম্পর্কিত কোনো প্রশ্ন করে (যেমন: জমা, খরচ, বিল, কার কত টাকা বাকি, ইত্যাদি), তাহলে নিচের ডেটা ভালোভাবে বিশ্লেষণ করে সঠিক উত্তর দাও।
৫. বিদায়ী শব্দ (যেমন: bye, goodbye, বিদায়, আল্লাহ হাফেজ, ইত্যাদি) শুনলে উপযুক্ত বিদায়ী উত্তর দাও।
৬. কোনো রোমান্টিক বা ফ্লার্ট করা যাবে না। শুধু পেশাদার ও বন্ধুসুলভ আচরণ করো।
"""
    
    user_prompt = f"""
নিচে ডেটা দেওয়া হলো:
{sheet_data}

ব্যবহারকারীর প্রশ্ন: {user_question}
"""
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Groq API ত্রুটি: {str(e)}"

# ===============================================
# 🌐 ওয়েব রুট
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
