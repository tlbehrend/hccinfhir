from pydantic import BaseModel
from typing import List, Optional

class MinimalDataElement(BaseModel):
    procedure_code: Optional[str] = None
    ndc: Optional[str] = None
    diagnosis_codes: List[str] = []
    claim_type: Optional[str] = None
    provider_specialty: Optional[str] = None
    provider_npi: Optional[str] = None
    patient_id: Optional[str] = None
    facility_type: Optional[str] = None
    service_type: Optional[str] = None
    service_date: Optional[str] = None
    place_of_service: Optional[str] = None
    quantity: Optional[float] = None
    quantity_unit: Optional[str] = None
    modifiers: List[str] = []
    allowed_amount: Optional[float] = None
