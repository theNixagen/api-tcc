from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Camera(Base):
    __tablename__ = "cameras"
    __table_args__ = (CheckConstraint("direcao IN ('entrada', 'saida')", name="cameras_direcao_check"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    direcao: Mapped[str | None] = mapped_column(String(10))
    chave_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
