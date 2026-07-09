import os
import json
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# ===============================================
# 📂 JSON ফাইল থেকে ডেটা পড়া
# ===============================================
def get_data_from_json():
    """data.json ফাইল থেকে ডেটা লোড করে"""
    with open('data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

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
# 💬 স্মার্ট প্রম্পট (JSON ডেটা থেকে)
# ===============================================
def get_ai_response(user_question):
    data = get_data_from_json()
    
    # ডেটাকে কম্প্যাক্ট টেক্সটে রূপান্তর
    compact_data = f"""
📊 **সারাংশ:**
- মোট জমা: {data['summary']['total_deposit']} টাকা
- মোট খরচ: {data['summary']['total_expense']} টাকা
- মোট লোন: {data['summary']['total_loan']} টাকা
- বর্তমান ব্যালেন্স: {data['summary']['current_balance']} টাকা

📋 **জমার তালিকা:**
{chr(10).join([f"- {d['date']}: {d['name']} → {d['amount']} টাকা" for d in data['deposits']])}

📋 **খরচের তালিকা:**
{chr(10).join([f"- {e['date']}: {e['description']} → {e['amount']} টাকা (দিয়েছেন: {e['paid_by']})" for e in data['expenses']])}

📋 **লোনের তালিকা:**
{chr(10).join([f"- {l['name']}: {l['amount']} টাকা ({l['note']})" for l in data['loans']])}

📋 **ড্যাশবোর্ড (বাসা ভাড়া ও অন্যান্য):**
{chr(10).join([f"- {d['name']}: বাসা {d['house_rent']}, খালা {d['khala']}, ওয়াইফাই {d['wifi']}, গ্যাস {d['gas']}, কারেন্ট {d['current']}, সার্ভিস {d['service']} = Due {d['total_due']}, Paid {d['paid']}, Status: {d['status']}" for d in data['dashboard']])}

📋 **বিলের সারাংশ:**
- মোট কারেন্ট বিল: {data['bills_summary']['total_current_bill']} টাকা
- মোট সার্ভিস চার্জ: {data['bills_summary']['total_service_charge']} টাকা
- প্রতি সদস্যের গ্যাস বিল: {data['bills_summary']['gas_bill_per_member']} টাকা
- প্রতি সদস্যের খালা বিল: {data['bills_summary']['khala_bill_per_member']} টাকা
- প্রতি সদস্যের ওয়াইফাই বিল: {data['bills_summary']['wifi_bill_per_member']} টাকা

👥 সদস্য: {', '.join(data['members'])}
"""
    
    system_prompt = """
তুমি একজন বুদ্ধিমান ও বন্ধুসুলভ AI সহায়ক। তোমার নাম 'মেসবট'।
তোমার কাজ হলো ব্যবহারকারীর প্রশ্নের উত্তর দেওয়া, বিশেষ করে ডেটা বিশ্লেষণ করে।

ডেটা দেওয়া আছে। সেখান থেকে উত্তর খুঁজে বের করো।
যদি ডেটাতে সরাসরি উত্তর না থাকে, তাহলে স্পষ্টভাবে বলে দাও "এই ডেটাতে এই প্রশ্নের উত্তর নেই"।

ব্যবহারকারী সাধারণ কথাও বলতে পারে (হাই, সালাম, কেমন আছো) — সেক্ষেত্রে বন্ধুসুলভ উত্তর দাও।
কোনো রোমান্টিক বা ফ্লার্ট করা যাবে না।
"""
    
    user_prompt = f"""
ডেটা:
{compact_data}

প্রশ্ন: {user_question}
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
