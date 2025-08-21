# file: models.py

from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, nullable=False)
    phone_number = Column(String, nullable=False, unique=True)
    payment_token = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(DECIMAL(10, 2), nullable=False)
    sku = Column(String, nullable=False, unique=True)
    image_url = Column(String, nullable=True)

class Shopping_Session(Base):
    __tablename__ = "shopping_sessions"
    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entry_time = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    exit_time = Column(TIMESTAMP(timezone=True), nullable=True)
    status = Column(String, nullable=False, default='active')

class Cart_Item(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, nullable=False)
    session_id = Column(Integer, ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price_at_pickup = Column(DECIMAL(10, 2), nullable=False)

class Receipt(Base):
    __tablename__ = "receipts"
    id = Column(Integer, primary_key=True, nullable=False)
    session_id = Column(Integer, ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    transaction_id = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

class Receipt_Details(Base):
    __tablename__ = "receipt_details"
    id = Column(Integer, primary_key=True, nullable=False)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    subtotal = Column(DECIMAL(10, 2), nullable=False)



class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id = Column(Integer, primary_key=True, nullable=False)
    alert_type = Column(String, nullable=False, default="tailgating")
    session_id = Column(Integer, ForeignKey("shopping_sessions.id"), nullable=True)
    details = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
