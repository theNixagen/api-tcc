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
    imagem: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
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
    capturado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    captura_informada: Mapped[bool] = mapped_column(default=False, server_default="false")
    iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tentativas: Mapped[int] = mapped_column(default=0, server_default="0")
    tentativas_limite: Mapped[int] = mapped_column(default=3, server_default="3")
    proxima_tentativa_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resultado: Mapped[str | None] = mapped_column(String(20))


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
    resultado: Mapped[str] = mapped_column(String(20), default="revisao", server_default="revisao")
    motivo: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RevisaoLeitura(Base):
    __tablename__ = "revisoes_leitura"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    leitura_id: Mapped[int] = mapped_column(ForeignKey("leituras.id"))
    metadado_id: Mapped[int | None] = mapped_column(ForeignKey("metadados_leitura.id"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    username: Mapped[str] = mapped_column(Text)
    acao: Mapped[str] = mapped_column(String(10))
    placa_anterior: Mapped[str] = mapped_column(Text)
    placa_corrigida: Mapped[str | None] = mapped_column(Text)
    motivo: Mapped[str] = mapped_column(Text)
    evento_id: Mapped[int | None] = mapped_column(ForeignKey("eventos.id", ondelete="SET NULL"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
