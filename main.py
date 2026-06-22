from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import shutil, os
from database import SessionLocal, User, FileScan # تأكد أن ملف database موجود في نفس الفولدر
from fastapi import Request
from prometheus_client import Counter
app = FastAPI()
@app.middleware("http")
async def track_ip_middleware(request: Request, call_next):
    # 1. سحب الـ IP بتاع الزائر
    client_ip = request.client.host
    
    # 2. تزويد العداد للـ IP ده بخطوة واحدة
    ip_request_counter.labels(client_ip=client_ip).inc()
    
    # 3. تمرير الطلب عشان التطبيق يكمل شغله العادي
    response = await call_next(request)
    return response
UPLOAD_COUNTER = Counter('total_uploaded_files', 'Total number of uploaded files')
# عداد لتسجيل عدد الطلبات وربطها بالـ IP
ip_request_counter = Counter('http_requests_by_ip_total', 'Total HTTP Requests by IP', ['client_ip'])
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    db.add(User(username=username, password=password))
    db.commit()
    return {"message": "Success"}

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username, User.password == password).first()
    if not user: raise HTTPException(status_code=400, detail="Wrong credentials")
    return {"user_id": user.id}

@app.post("/upload")
def upload(user_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    os.makedirs("uploads", exist_ok=True)
    with open(f"uploads/{file.filename}", "wb") as f:
        shutil.copyfileobj(file.file, f)
    UPLOAD_COUNTER.inc()
    scan = FileScan(filename=file.filename, status="Pending", user_id=user_id)
    db.add(scan)
    db.commit()
    return {"message": "Uploaded successfully"}

@app.get("/scans")
def get_scans(db: Session = Depends(get_db)):
    return db.query(FileScan).all()

# الواجهة الجديدة الاحترافية (Tailwind + JS Logic)
@app.get("/", response_class=HTMLResponse)
def frontend():
    return """
<!DOCTYPE html>
<html lang="ar" class="dark">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <title>Security Gateway | Dashboard</title>
</head>
<body class="bg-gray-900 text-white min-h-screen font-sans p-6">

    <nav class="p-6 border-b border-gray-700 flex justify-between items-center mb-8">
        <h1 class="text-2xl font-bold text-blue-400">🛡️ Autonomous Security Gateway</h1>
    </nav>

    <div id="login-section" class="max-w-md mx-auto bg-gray-800 p-8 rounded-xl shadow-xl">
        <h2 class="text-xl mb-4 text-center">دخول النظام</h2>
        <input id="user" placeholder="Username" class="w-full p-2 mb-4 bg-gray-700 rounded text-white">
        <input id="pass" type="password" placeholder="Password" class="w-full p-2 mb-4 bg-gray-700 rounded text-white">
        <div class="flex gap-2">
            <button onclick="auth('/login')" class="w-full bg-blue-600 p-2 rounded">Login</button>
            <button onclick="auth('/register')" class="w-full bg-gray-600 p-2 rounded">Register</button>
        </div>
    </div>

    <main id="main-section" class="max-w-4xl mx-auto mt-10 p-6 bg-gray-800 rounded-xl shadow-xl hidden">
        <h2 class="text-xl mb-4">رفع ملفات الفحص</h2>
        <div class="border-2 border-dashed border-gray-600 p-10 text-center rounded-lg hover:border-blue-500 transition mb-6">
            <input type="file" id="fileInput" class="hidden">
            <label for="fileInput" class="cursor-pointer text-gray-400">اضغطي هنا أو اسحبي الملف للرفع</label>
            <button onclick="uploadFile()" class="block w-full mt-4 bg-blue-600 p-2 rounded">رفع الملف</button>
        </div>

        <h3 class="text-lg mb-4">سجل الفحص (Scans Log)</h3>
        <table class="w-full text-left border-collapse">
            <tbody id="logsBody"></tbody>
        </table>
    </main>

    <script>
        let currentUserId = null;
        async function auth(url) {
            let formData = new FormData();
            formData.append('username', document.getElementById('user').value);
            formData.append('password', document.getElementById('pass').value);
            let res = await fetch(url, {method: 'POST', body: formData});
            let data = await res.json();
            if(res.ok && data.user_id) {
                currentUserId = data.user_id;
                document.getElementById('login-section').style.display='none';
                document.getElementById('main-section').style.display='block';
                loadScans();
            } else { alert(data.detail || data.message); }
        }
        async function uploadFile() {
            let file = document.getElementById('fileInput').files[0];
            let formData = new FormData();
            formData.append('user_id', currentUserId);
            formData.append('file', file);
            let res = await fetch('/upload', {method: 'POST', body: formData});
            if(res.ok) { alert("Done!"); loadScans(); }
        }
        async function loadScans() {
            let res = await fetch('/scans');
            let scans = await res.json();
            let tbody = document.getElementById('logsBody');
            tbody.innerHTML = "";
            scans.forEach(s => {
                tbody.innerHTML += `<tr class="border-b border-gray-700"><td class="py-3">${s.filename}</td><td class="py-3 text-yellow-400">${s.status}</td></tr>`;
            });
        }
    </script>
</body>
</html>
    """
