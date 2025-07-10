# app/models.py

from pydantic import BaseModel
from typing import Optional

# Pydantic model for JWT token response
class Token(BaseModel):
    """
    Represents the structure of a JWT token response.
    """
    access_token: str
    token_type: str

# Pydantic model for data contained within a JWT token
class TokenData(BaseModel):
    """
    Represents the payload data extracted from a JWT token.
    Contains optional username (subject) and role.
    """
    username: Optional[str] = None
    role: Optional[str] = None

# Pydantic model for creating new shipment data
class ShipmentCreateData(BaseModel):
    """
    Represents the required fields for creating a new shipment.
    All fields are strings and are mandatory.
    """
    shipment_id: str
    po_number: str
    route_details: str
    device: str
    ndc_number: str
    serial_number: str
    container_number: str
    goods_type: str
    expected_delivery_date: str # Consider adding a date validation later if needed
    delivery_number: str
    batch_id: str
    origin: str
    destination: str
    shipment_description: str

