from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
from database import db, HiddenLink
from cryptography.fernet import Fernet
import base64

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///links.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit

# إنشاء الجدول عند التشغيل الأول
with app.app_context():
    db.create_all()

@app.route('/save-link', methods=['POST'])
def save_link():
    data = request.json
    new_link = HiddenLink(
        url=data['url'],
        cover_text=data['cover_text'],
        hidden_code=data['hidden_code']
    )
    db.session.add(new_link)
    db.session.commit()
    return jsonify({"message": "تم الحفظ بنجاح!"})

@app.route('/get-link/<int:id>', methods=['GET'])
def get_link(id):
    link = HiddenLink.query.get(id)
    if link:
        return jsonify({
            "url": link.url,
            "cover_text": link.cover_text
        })
    return jsonify({"error": "الرابط غير موجود"}), 404

@app.route('/get-all-links', methods=['GET'])
def get_all_links():
    links = HiddenLink.query.all()
    return jsonify([{
        "id": link.id,
        "cover_text": link.cover_text
    } for link in links])


# استخدم API key من ImgBB (سجل واحصل على مفتاحك من https://api.imgbb.com)
IMG_BB_API_KEY = '7df41720671e5063a5a28347fce407a8'

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify(success=False, error='لم يتم اختيار ملف'), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify(success=False, error='اسم ملف غير صالح'), 400

        # التحقق من نوع الملف
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if file.mimetype not in allowed_types:
            return jsonify(success=False, error='نوع الملف غير مدعوم'), 400

        # إعداد طلب الرفع لـ ImgBB
        files = {'image': (file.filename, file.stream, file.mimetype)}
        response = requests.post(
            'https://api.imgbb.com/1/upload',
            files=files,
            data={'key': IMG_BB_API_KEY}
        )

        # تحليل الاستجابة
        response_data = response.json()
        if response.status_code != 200 or not response_data.get('success'):
            error_msg = response_data.get('error', {}).get('message', 'فشل في عملية الرفع')
            return jsonify(success=False, error=error_msg), 500

        direct_link = response_data['data']['url']
        return jsonify(success=True, url=direct_link)

    except requests.exceptions.RequestException as e:
        return jsonify(success=False, error=f'خطأ في الاتصال: {str(e)}'), 500
    except Exception as e:
        return jsonify(success=False, error=f'خطأ غير متوقع: {str(e)}'), 500
    finally:
        if 'file' in locals():
            file.close()


# توليد مفتاح تشفير (يُخزن بشكل آمن في البيئة الحقيقية)
key = Fernet.generate_key()
cipher = Fernet(key)

@app.route('/encrypt', methods=['POST'])
def encrypt():
    data = request.json
    url = data.get('url')
    cover_text = data.get('cover_text')
    
    if not url or not cover_text:
        return jsonify({"error": "Missing data"}), 400
    
    # تشفير الرابط
    encrypted_url = cipher.encrypt(url.encode()).decode()
    
    # دمج النص الظاهر مع الرابط المشفر (بفاصل خاص)
    hidden_content = f"{cover_text}||{encrypted_url}"
    
    return jsonify({"hidden_text": hidden_content})

@app.route('/decrypt', methods=['POST'])
def decrypt():
    data = request.json
    hidden_text = data.get('hidden_text')
    
    if not hidden_text:
        return jsonify({"error": "Missing data"}), 400
    
    # فصل النص عن الرابط المشفر
    parts = hidden_text.split('||')
    if len(parts) != 2:
        return jsonify({"error": "Invalid format"}), 400
    
    try:
        # فك تشفير الرابط
        decrypted_url = cipher.decrypt(parts[1].encode()).decode()
        return jsonify({"url": decrypted_url})
    except:
        return jsonify({"error": "Decryption failed"}), 400
        
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "مرحبًا! هذا API لإدارة الروابط. استخدم /save-link لإضافة رابط، و /get-link/<id> لجلبه.",
        "status": "success"
    })        

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
