"""Database setup: two tables — source documents and field-level extractions."""
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer,
                        String, Text, create_engine)
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column,
                            relationship, sessionmaker)

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://trial:trial@localhost:5432/trialtrace"
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Document(Base):
    """One ClinicalTrials.gov record. `text` is the only thing the LLM sees;
    `ground_truth` holds the registry's structured fields, used for evaluation."""

    __tablename__ = "documents"
    nct_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    ground_truth: Mapped[dict] = mapped_column(JSON)
    raw: Mapped[dict] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    extractions: Mapped[list["Extraction"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Extraction(Base):
    """One extracted field, with provenance: exact character span in the source."""

    __tablename__ = "extractions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nct_id: Mapped[str] = mapped_column(ForeignKey("documents.nct_id"), index=True)
    field: Mapped[str] = mapped_column(String(40))
    value: Mapped[str | None] = mapped_column(Text, nullable=True)  # None = "not found"
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)  # what the LLM said
    source_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    span_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    span_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked_hallucination: Mapped[bool] = mapped_column(Boolean, default=False)
    model: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    document: Mapped[Document] = relationship(back_populates="extractions")


def init_db() -> None:
    Base.metadata.create_all(engine)
