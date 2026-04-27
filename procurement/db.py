import os
import hashlib
import secrets
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "app.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def hash_password(password: str, salt: str = None) -> str:
    salt = salt or secrets.token_hex(8)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(160), nullable=False)
    role = Column(String(20), default="buyer")  # buyer | supplier
    market_type = Column(String(20), default="retail")  # retail | wholesale
    reset_token = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    __tablename__ = "sessions"
    token = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    supplier_name = Column(String(200))
    lot_no = Column(String(80))
    product = Column(Text)
    customer = Column(String(200))
    quantity = Column(Integer, default=1)
    price = Column(Float, default=0)
    net_profit = Column(Float, default=0)
    status = Column(String(20), default="sent")  # sent | accepted | rejected | completed | cancelled
    created_at = Column(DateTime, default=datetime.utcnow)


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    number = Column(String(40), unique=True)
    product = Column(Text)
    quantity = Column(Integer)
    unit_price = Column(Float)
    total = Column(Float)
    supplier_name = Column(String(200))
    customer_name = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)


class SupplierProduct(Base):
    __tablename__ = "supplier_products"
    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(String(80))
    price = Column(Float, default=0)
    market_type = Column(String(20), default="retail")
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)


@contextmanager
def db_session():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
