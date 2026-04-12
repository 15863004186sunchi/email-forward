from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///data/email_routes.db")
Base = declarative_base()
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {})
Session = sessionmaker(bind=engine)


class EmailRoute(Base):
    __tablename__ = "email_routes"

    local_part  = Column(String(100), primary_key=True)   # e.g. abc123
    forward_to  = Column(String(200), nullable=True)       # user's real email
    active      = Column(Boolean, default=False)
    order_id    = Column(String(100), nullable=True)
    buyer_name  = Column(String(200), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ForwardLog(Base):
    __tablename__ = "forward_logs"

    id          = Column(String(64), primary_key=True)
    local_part  = Column(String(100))
    from_addr   = Column(String(200))
    forward_to  = Column(String(200))
    subject     = Column(Text)
    status      = Column(String(20))   # success / failed / no_route
    error       = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)
