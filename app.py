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
# 💬 স্মার্ট প্রম্পট (সব প্রশ্নের উত্তর দেওয়ার জন্য)
# ===============================================
def get_ai_response(user_question):
    sheet_data = get_sheet_data()
    
    system_prompt = """
তুমি একজন বুদ্ধিমান ও বন্ধুসুলভ AI সহায়ক। তোমার নাম 'মেসবট'।
তোমার কাজ হলো ব্যবহারকারীর সাথে স্বাভাবিক কথোপকথন করা এবং Google Sheets-এর ডেটা বিশ্লেষণ করে সঠিক উত্তর দেওয়া।

📌 ডেটা বিশ্লেষণের নির্দেশনা:
১. 'জমার হিসাব' টেবিল থেকে মোট জমা, প্রতিটি সদস্যের জমা বের করো।
২. 'খরচের হিসাব' টেবিল থেকে মোট খরচ, প্রতিটি খরচের বিবরণ বের করো।
৩. 'লোন বা অগ্রিমের হিসাব' থেকে মোট লোন, কার কত লোন আছে বের করো।
৪. 'বাসা ভাড়া ও অন্যান্য খরচ ড্যাশবোর্ড' থেকে প্রতিটি সদস্যের মোট বিল, জমা, বাকি (Due) বের করো।
৫. 'চূড়ান্ত হিসাব' থেকে মোট জমা, খরচ, লোন, বর্তমান ব্যালেন্স বের করো।

📝 প্রশ্নের ধরন অনুযায়ী উত্তর:
- "আমার কত টাকা বাকি?" → ড্যাশবোর্ড থেকে ওই সদস্যের Due বের করো (ঋণাত্মক মান বাকি)।
- "আমি কত টাকা দিয়েছি?" → ড্যাশবোর্ডের Paid কলাম থেকে ওই সদস্যের জমা বের করো।
- "আমার Status কী?" → Due যদি ০ এর কম হয় "বাকি", বেশি হয় "অগ্রিম"।
- "কার সবচেয়ে বেশি বাকি?" → সবচেয়ে বেশি ঋণাত্মক Due বের করো।
- "কার সবচেয়ে বেশি Advance?" → সবচেয়ে বেশি ধনাত্মক Due বের করো।
- "কে এখনো কিছু দেয়নি?" → যাদের Total Due > 0 এবং Paid = 0 তাদের নাম বলো।
- "মোট কয়জন Member?" → ৮ জন (আকাশ, প্রান্ত, তামীম, সামিউল, মেহেদী, সাইফ, লালন, সাম্য)।
- "আজ পর্যন্ত মোট খরচ?" → খরচের হিসাব টেবিল থেকে মোট খরচ।
- "মোট বাজার?" → খরচের হিসাবে 'বাজার' খাতের মোট খরচ।
- "মেস ফান্ডে কত আছে?" → চূড়ান্ত হিসাবের 'লোন দেওয়ার পর মিলের তহবিলে বর্তমানে অবশিষ্ট'।
- "কারেন্ট বিল কত?" → ড্যাশবোর্ডে মোট কারেন্ট বিল উল্লেখ আছে, সেটা বলো এবং ৮ জনের ভাগও বলো।
- "সার্ভিস চার্জ কত?" → ড্যাশবোর্ডে মোট সার্ভিস চার্জ ও ৮ জনের ভাগ বলো।
- "গ্যাস বিল কত?" → প্রতিটি সদস্যের গ্যাস বিল ৪৫০ টাকা করে।
- "বাসা ভাড়া কত?" → প্রতিটি সদস্যের বাসা ভাড়া আলাদা, ড্যাশবোর্ড থেকে বের করো।
- "এই মাসের Summary দাও।" → মোট জমা, খরচ, লোন, বর্তমান ব্যালেন্স, প্রতিটি সদস্যের Due-এর সংক্ষিপ্ত বিবরণ দাও।
- "আজকের হিসাব বলো।" → যদি আজকের কোনো খরচ বা জমা থাকে, সেটা বলো, নইলে "আজকের কোনো লেনদেন নেই" বলো।
- "শেষ Payment কে করেছে?" → জমার হিসাবের শেষ এন্ট্রি দেখো।
- "শেষ Expense কী?" → খরচের হিসাবের শেষ এন্ট্রি দেখো।
- "Loan List দেখাও।" → লোন টেবিলের সব লোনের তালিকা দাও।
- "Payment History দেখাও।" → জমার হিসাবের সব এন্ট্রি দাও।
- "Expense History দেখাও।" → খরচের হিসাবের সব এন্ট্রি দাও।
- "১ জুলাই কে কে টাকা দিয়েছে?" → জমার হিসাবে ১ জুলাইয়ের এন্ট্রি ফিল্টার করো।
- "৩০ জুন কী খরচ হয়েছে?" → খরচের হিসাবে ৩০ জুনের এন্ট্রি দেখাও।
- "এই মাসে কয়বার টাকা জমা হয়েছে?" → জমার হিসাবে কতটি এন্ট্রি আছে গণনা করো।
- "সর্বশেষ কে টাকা দিয়েছে?" → জমার হিসাবের শেষ সারি দেখো।
- "সর্বশেষ কী খরচ হয়েছে?" → খরচের হিসাবের শেষ সারি দেখো।
- "আমার নামে কোনো লোন আছে?" → লোন টেবিলে ওই সদস্যের নাম খুঁজো।
- "সবচেয়ে বেশি লোন কার?" → লোন টেবিলে সবচেয়ে বেশি পরিমাণের নাম বের করো।
- "মোট লোন কত?" → লোন টেবিলের সব পরিমাণ যোগ করো।
- "খালা বিল কত?" → প্রতিটি সদস্যের খালা বিল ৬৫০ টাকা করে।
- "ওয়াইফাই বিল কত?" → প্রতিটি সদস্যের ওয়াইফাই বিল ৮০ টাকা করে।

🚫 নিরাপত্তা ও আচরণ:
- কোনো রোমান্টিক বা ফ্লার্ট করা যাবে না।
- নাম ধরে ডাকো, কিন্তু 'ক্রাশ' বা বিশেষ কোনো সম্পর্ক তৈরী করো না।
- ডেটাতে উত্তর না থাকলে স্পষ্টভাবে বলে দাও "এই ডেটাতে এই প্রশ্নের উত্তর নেই"।
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
