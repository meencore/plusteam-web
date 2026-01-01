import os
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import secrets

# --- ปิดเสียงแจ้งเตือนขยะ ---
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# --- GLOBAL VARIABLE เช็คคนใช้งาน (1 User Limit) ---
ACTIVE_USER_SESSION = None 

# --- API KEY ---
raw_api_key = "AIzaSyDs4JlSatJNjH62lNmY6ekgRwP6PysxB9Y"
my_clean_key = raw_api_key.strip() 
os.environ["GOOGLE_API_KEY"] = my_clean_key
genai.configure(api_key=my_clean_key)
model = genai.GenerativeModel('models/gemini-2.5-flash')
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- LOGIN / LOGOUT ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    global ACTIVE_USER_SESSION
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == '123456':
            if ACTIVE_USER_SESSION is not None and ACTIVE_USER_SESSION != session.get('user_id'):
                return render_template('login.html', error="ระบบไม่ว่าง! มีผู้ใช้งานอยู่แล้ว")
            
            new_session_id = secrets.token_hex(8)
            session['logged_in'] = True
            session['user_id'] = new_session_id
            ACTIVE_USER_SESSION = new_session_id
            
            return redirect(url_for('home')) # เข้าสู่หน้าแรก
        else:
            return render_template('login.html', error="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    global ACTIVE_USER_SESSION
    if session.get('user_id') == ACTIVE_USER_SESSION:
        ACTIVE_USER_SESSION = None
    session.clear()
    return redirect(url_for('home')) # ออกแล้วกลับมาหน้าแรก

# --- ROUTES ---

@app.route('/')
def home():
    # เปิดให้ทุกคนเข้าหน้าแรกได้ (เพื่อเห็นปุ่ม Login)
    return render_template('dashmain.html')

@app.route('/center')
def center():
    # หน้าเลือกเกม (ต้อง Login)
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('main.html')

@app.route('/baccarat')
def baccarat_app():
    # หน้าสูตร (ต้อง Login)
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html')

# --- API PREDICT ---
@app.route('/predict', methods=['POST'])
def predict():
    if not session.get('logged_in'):
        return jsonify({'result': json.dumps({"prediction": "-", "confidence": "0", "reason": "Unauthorized"}), 'status': 'error'})

    try:
        data = request.json
        full_history = data.get('history', [])
        current_view = full_history[-60:]
        history_str = ", ".join(current_view)

        prompt = f"""
        Role: Grandmaster Baccarat Analyst (Statistical Expert).
        Current Shoe DNA: [{history_str}]
        
        Analyze using 9 GOLDEN RULES (Dragon, Ping Pong, etc.).
        Output format (JSON ONLY):
        {{
            "prediction": "Player" or "Banker",
            "confidence": "0-100",
            "reason": "Explain in Thai (ภาษาไทย)"
        }}
        """

        response = model.generate_content(prompt, safety_settings=safety_settings)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        return jsonify({'result': clean_text, 'status': 'success'})

    except Exception as e:
        print(f"Error: {e}")
        fallback = json.dumps({
            "prediction": "Banker", "confidence": "50", "reason": "AI ประมวลผลไม่ทัน (แนะนำ B)"
        })
        return jsonify({'result': fallback, 'status': 'success'})

if __name__ == '__main__':
    from waitress import serve
    print("🚀 PLUS TEAM SYSTEM READY!")
    print("👉 Portal: http://127.0.0.1:5000")
    serve(app, host="0.0.0.0", port=5000, threads=8)

