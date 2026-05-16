from sqlalchemy import Column, Integer, Float, Boolean, String
from database import Base

class Lectura(Base):

    __tablename__ = "lecturas"

    id = Column(Integer, primary_key=True, index=True)

    temperatura = Column(Float)
    humedad = Column(Float)
    luz = Column(Boolean)

    timestamp = Column(String)
