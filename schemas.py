

from pydantic import BaseModel
from typing import Optional, List 
from datetime import datetime   

class UserCreate(BaseModel):
    phone_number: str

class UserResponse(BaseModel):
    id: int
    phone_number: str
    payment_token: Optional[str] = None
    class Config:
        from_attributes = True

class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    class Config:
        from_attributes = True

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1

class CartItemResponse(BaseModel):
    product_id: int
    name: str
    quantity: int
    price: float
    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    session_id: int
    items: List[CartItemResponse]
    current_total: float

class ReceiptDetailResponse(BaseModel):
    product_name: str
    quantity: int
    price: float
    subtotal: float
    class Config:
        from_attributes = True

class ReceiptResponse(BaseModel):
    receipt_id: int
    session_id: int
    total_amount: float
    transaction_id: Optional[str] = None
    created_at: datetime
    items: List[ReceiptDetailResponse]
    class Config:
        from_attributes = True

class SessionCreate(BaseModel):
    user_id: int

class SessionResponse(BaseModel):
    id: int
    user_id: int
    status: str
    entry_time: datetime

    class Config:
        from_attributes = True   


class UserVerify(BaseModel):
    phone_number: str
    otp_code: str                 



class Token(BaseModel):
    access_token: str
    token_type: str



class TailgatingAlert(BaseModel):
    pass 



class PaymentTokenUpdate(BaseModel):
    payment_token: str
