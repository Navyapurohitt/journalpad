from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, String, Text, Boolean, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime, timezone
import uuid
import os

# ── DB setup ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./writingpad.db")

# Railway gives postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ── Model ─────────────────────────────────────────────────────────────────────
class Pad(Base):
    __tablename__ = "pads"

    id            = Column(String(12), primary_key=True, index=True)
    content       = Column(Text, nullable=False, default="")
    password_hash = Column(String, nullable=True)        # None = public
    is_protected  = Column(Boolean, default=False)
    view_count    = Column(Integer, default=0)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(bind=engine)

# ── Password hashing ──────────────────────────────────────────────────────────
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

# ── Schemas ───────────────────────────────────────────────────────────────────
class PadCreate(BaseModel):
    content: str
    password: str | None = None   # optional password

class PadRead(BaseModel):
    password: str | None = None   # send password to unlock

class PadUpdate(BaseModel):
    content: str
    password: str | None = None   # must supply if protected

class PadResponse(BaseModel):
    id: str
    content: str
    is_protected: bool
    view_count: int
    created_at: datetime
    updated_at: datetime

class PadMeta(BaseModel):
    id: str
    is_protected: bool
    view_count: int
    created_at: datetime

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="WritingPad API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ── Dependency ────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_id(length: int = 10) -> str:
    return uuid.uuid4().hex[:length]

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/pads", response_model=dict, status_code=201)
def create_pad(data: PadCreate, db: Session = Depends(get_db)):
    pad_id = generate_id()
    pad = Pad(
        id=pad_id,
        content=data.content,
        is_protected=bool(data.password),
        password_hash=hash_password(data.password) if data.password else None,
    )
    db.add(pad)
    db.commit()
    db.refresh(pad)
    return {
        "id": pad.id,
        "is_protected": pad.is_protected,
        "created_at": pad.created_at.isoformat(),
    }


@app.get("/pads/{pad_id}/meta", response_model=PadMeta)
def get_pad_meta(pad_id: str, db: Session = Depends(get_db)):
    """Returns metadata (no content) — used to check if a pad is password-protected."""
    pad = db.query(Pad).filter(Pad.id == pad_id).first()
    if not pad:
        raise HTTPException(status_code=404, detail="Pad not found")
    return PadMeta(
        id=pad.id,
        is_protected=pad.is_protected,
        view_count=pad.view_count,
        created_at=pad.created_at,
    )


@app.post("/pads/{pad_id}/read", response_model=PadResponse)
def read_pad(pad_id: str, data: PadRead, db: Session = Depends(get_db)):
    """Fetch pad content. Requires password body if pad is protected."""
    pad = db.query(Pad).filter(Pad.id == pad_id).first()
    if not pad:
        raise HTTPException(status_code=404, detail="Pad not found")

    if pad.is_protected:
        if not data.password:
            raise HTTPException(status_code=401, detail="Password required")
        if not verify_password(data.password, pad.password_hash):
            raise HTTPException(status_code=403, detail="Wrong password")

    # increment view count
    pad.view_count += 1
    db.commit()
    db.refresh(pad)

    return PadResponse(
        id=pad.id,
        content=pad.content,
        is_protected=pad.is_protected,
        view_count=pad.view_count,
        created_at=pad.created_at,
        updated_at=pad.updated_at,
    )


@app.put("/pads/{pad_id}", response_model=dict)
def update_pad(pad_id: str, data: PadUpdate, db: Session = Depends(get_db)):
    """Update pad content (must verify password if protected)."""
    pad = db.query(Pad).filter(Pad.id == pad_id).first()
    if not pad:
        raise HTTPException(status_code=404, detail="Pad not found")

    if pad.is_protected:
        if not data.password:
            raise HTTPException(status_code=401, detail="Password required to edit")
        if not verify_password(data.password, pad.password_hash):
            raise HTTPException(status_code=403, detail="Wrong password")

    pad.content = data.content
    pad.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": pad.id, "updated": True}


@app.delete("/pads/{pad_id}", response_model=dict)
def delete_pad(pad_id: str, data: PadRead, db: Session = Depends(get_db)):
    """Delete a pad (must verify password if protected)."""
    pad = db.query(Pad).filter(Pad.id == pad_id).first()
    if not pad:
        raise HTTPException(status_code=404, detail="Pad not found")

    if pad.is_protected:
        if not data.password or not verify_password(data.password, pad.password_hash):
            raise HTTPException(status_code=403, detail="Wrong password")

    db.delete(pad)
    db.commit()
    return {"id": pad_id, "deleted": True}
