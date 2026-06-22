from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# ديف أوبس: قراءة بيانات الاتصال من ملف .env بأمان
POSTGRES_USER = os.getenv("POSTGRES_USER", "devops_admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "secure_password_2026")
POSTGRES_DB = os.getenv("POSTGRES_DB", "security_gateway_db")

# الاتصال بخدمة db الموجودة في ملف الـ docker-compose
SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@db:5432/{POSTGRES_DB}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

class FileScan(Base):
    __tablename__ = "file_scans"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    status = Column(String, default="Pending")
    user_id = Column(Integer, ForeignKey("users.id"))

# بناء الجداول أوتوماتيكياً
Base.metadata.create_all(bind=engine)
