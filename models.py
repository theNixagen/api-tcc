from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Evento(Base):
    __tablename__ = "eventos"
    __table_args__ = (
        CheckConstraint("tipo_evento IN ('entrada', 'saida')", name="eventos_tipo_evento_check"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo_evento: Mapped[str] = mapped_column(String(10), nullable=False)
    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    placa: Mapped[str] = mapped_column(String(10), nullable=False)
