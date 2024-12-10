from pydantic import BaseModel
from typing import List, Optional

class ServiceLevelData(BaseModel):
    """
    Represents standardized service-level data extracted from healthcare claims.
    
    Attributes:
        claim_id: Unique identifier for the claim
        procedure_code: Healthcare Common Procedure Coding System (HCPCS) code
        ndc: National Drug Code
        linked_diagnosis_codes: ICD-10 diagnosis codes linked to this service
        claim_diagnosis_codes: All diagnosis codes on the claim
        claim_type: Type of claim (e.g., NCH Claim Type Code, or 837I, 837P)
        provider_specialty: Provider taxonomy or specialty code
        performing_provider_npi: National Provider Identifier for performing provider
        billing_provider_npi: National Provider Identifier for billing provider
        patient_id: Unique identifier for the patient
        facility_type: Type of facility where service was rendered
        service_type: Type of service provided (facility type + service type = Type of Bill)
        service_date: Date service was performed (YYYY-MM-DD)
        place_of_service: Place of service code
        quantity: Number of units provided
        quantity_unit: Unit of measure for quantity
        modifiers: List of procedure code modifiers
        allowed_amount: Allowed amount for the service
    """
    claim_id: Optional[str] = None
    procedure_code: Optional[str] = None
    ndc: Optional[str] = None
    linked_diagnosis_codes: List[str] = []
    claim_diagnosis_codes: List[str] = []
    claim_type: Optional[str] = None
    provider_specialty: Optional[str] = None
    performing_provider_npi: Optional[str] = None
    billing_provider_npi: Optional[str] = None
    patient_id: Optional[str] = None
    facility_type: Optional[str] = None
    service_type: Optional[str] = None
    service_date: Optional[str] = None
    place_of_service: Optional[str] = None
    quantity: Optional[float] = None
    modifiers: List[str] = []
    allowed_amount: Optional[float] = None
