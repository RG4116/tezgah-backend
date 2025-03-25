from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    colors = relationship("Color", back_populates="product", cascade="all, delete")

class Color(Base):
    __tablename__ = "colors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    price = Column(Float, nullable=False)  # ✅ Fiyat alanı eklendi
    currency = Column(String, nullable=False)  # ✅ Para birimi alanı eklendi

    product = relationship("Product", back_populates="colors")
