from datetime import datetime

from sqlalchemy import (
    DateTime, Float, ForeignKey, Integer, JSON, LargeBinary, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Leitura(Base):
    __tablename__ = "leituras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int | None] = mapped_column(
        ForeignKey("clientes.id", ondelete="SET NULL")
    )
    nome_arquivo: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(Text)
    imagem: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    tamanho_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20), default="pendente", server_default="pendente"
    )
    erro: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duracao_ms: Mapped[float | None] = mapped_column(Float)


class MetadadosLeitura(Base):
    __tablename__ = "metadados_leitura"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    leitura_id: Mapped[int] = mapped_column(ForeignKey("leituras.id", ondelete="CASCADE"))
    evento_id: Mapped[int | None] = mapped_column(
        ForeignKey("eventos.id", ondelete="SET NULL")
    )
    placa: Mapped[str] = mapped_column(Text)
    texto_ocr: Mapped[str] = mapped_column(Text)
    confianca_deteccao: Mapped[float] = mapped_column(Float)
    confianca_ocr: Mapped[float | None] = mapped_column(Float)
    bbox: Mapped[list[int]] = mapped_column(JSON)
    modelo: Mapped[str] = mapped_column(Text)
    imgsz: Mapped[int] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
