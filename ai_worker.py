import time
import os
import requests
import numpy as np
# استيراد موديول الذكاء الاصطناعي اللي سطبتيه
from sklearn.ensemble import IsolationForest 
# استيراد اتصال قاعدة البيانات من مشروعك
from database import SessionLocal, FileScan 

# 🛑 ضعي رابط الـ Webhook بتاع Slack هنا
SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/XXXX/XXXX/XXXX'

# 1️⃣ دالة الـ AI لاستخراج خصائص الملف (Feature Extraction)
def extract_file_features(file_path):
    try:
        file_size = os.path.getsize(file_path)
        
        # قراءة محتوى الملف لمعرفة ما بداخله
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read()
            
        # عد الكلمات المفتاحية الخطيرة التي تستخدم في الاختراق
        suspicious_words = ['eval', 'exec', 'system', 'os.popen', 'base64', 'cmd.exe', '/bin/bash', 'powershell']
        word_count = sum(content.lower().count(word) for word in suspicious_words)
        
        # حساب نسبة الرموز الغريبة (محاكاة للـ Entropy)
        special_chars = sum(1 for char in content if char in ['$', '{', '}', '[', ']', '\\', '#', '%'])
        char_ratio = special_chars / (len(content) + 1)
        
        # إرجاع الخصائص كـ مصفوفة أرقام يفهمها الـ AI
        return [file_size, word_count, char_ratio]
    except Exception as e:
        print(f"❌ خطأ أثناء استخراج خصائص الملف: {e}")
        return [0, 0, 0]

# 2️⃣ تجهيز وتدريب موديل الـ AI (Isolation Forest)
# هنعطيه أمثلة لملفات طبيعية عشان يتعلم شكل الـ CV السليم إيه
def train_security_ai():
    print("🧠 جاري تجهيز موديل الـ AI وتدريبه على السلوك الطبيعي...")
    
    # بيانات تدريب افتراضية (ملفات طبيعية: حجم صغير، صفر كلمات مريبة، رموز قليلة)
    normal_behavior = [
        [15000, 0, 0.01],
        [25000, 0, 0.02],
        [45000, 1, 0.01],
        [30000, 0, 0.015]
    ]
    
    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(normal_behavior)
    return model

# 3️⃣ دالة إرسال التنبيه لـ Slack وكتابة الـ Playbook ديناميكياً
def handle_malicious_file(filename, ip="192.168.1.99"):
    # الـ AI بيقوم بكتابة الـ Ansible Playbook فوراً في الخلفية
    playbook_content = f"""---
- name: Dynamic Block Malicious Uploader
  hosts: localhost
  connection: local
  become: yes
  tasks:
    - name: Block attacker IP via iptables
      iptables:
        chain: INPUT
        source: "{ip}"
        jump: DROP
        state: present
"""
    with open("block_ip.yml", "w") as f:
        f.write(playbook_content)

    # إرسال التنبيه لـ Slack
    payload = {
        "text": f"🚨 *AI ALERT: ملف خبيث تم اكتشافه بالذكاء الاصطناعي!* 🚨\n\n"
                f"📁 *اسم الملف:* `{filename}`\n"
                f"👤 *الـ IP الرافعه:* `{ip}`\n"
                f"📊 *قرار الـ AI:* الأنماط المكتشفة تشير إلى محاولة اختراق (Anomaly).\n"
                f"⚙️ *الـ Ansible:* تم توليد ملف `block_ip.yml` مخصص لحظر هذا الـ IP.\n\n"
                f"👉 لتنفيذ الحظر اضغطي يدوياً:\n`ansible-playbook block_ip.yml`"
    }
    requests.post(SLACK_WEBHOOK_URL, json=payload)

# 4️⃣ المشغل الرئيسي (Background Worker)
def run_ai_worker():
    # تدريب الموديل أول ما يشتغل السكريبت
    ai_model = train_security_ai()
    db = SessionLocal()
    
    print("🚀 الـ AI شغال دلوقتي ومستني أي ملف Pending في الداتابيز...")
    
    try:
        while True:
            # اسحب أول ملف معلق
            scan_job = db.query(FileScan).filter(FileScan.status == "Pending").first()
            
            if scan_job:
                print(f"\n🔍 الـ AI يفحص الآن: {scan_job.filename}")
                file_path = f"uploads/{scan_job.filename}"
                
                if os.path.exists(file_path):
                    # استخراج الخصائص
                    features = extract_file_features(file_path)
                    
                    # توقع الـ AI (1 يعني سليم، -1 يعني خبيث/شاذ)
                    prediction = ai_model.predict([features])[0]
                    
                    if prediction == -1:
                        scan_job.status = "Malicious"
                        print(f"🚨 نتيجة الـ AI: الملف خبيث!")
                        handle_malicious_file(scan_job.filename)
                    else:
                        scan_job.status = "Safe"
                        print(f"✅ نتيجة الـ AI: الملف سليم.")
                        
                    db.commit()
                else:
                    scan_job.status = "Error (Missing)"
                    db.commit()
                    
            time.sleep(3) # فحص كل 3 ثواني
    except KeyboardInterrupt:
        print("🛑 تم إيقاف الـ AI.")
    finally:
        db.close()

if __name__ == "__main__":
    run_ai_worker()
