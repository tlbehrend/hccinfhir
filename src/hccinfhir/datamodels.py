from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any, TypedDict

# Define Model Name literal type
ModelName = Literal[
    "CMS-HCC Model V22",
    "CMS-HCC Model V24",
    "CMS-HCC Model V28",
    "CMS-HCC ESRD Model V21",
    "CMS-HCC ESRD Model V24",
    "RxHCC Model V08"
]
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

class Demographics(BaseModel):
    """
    Response model for demographic categorization
    """
    age: int = Field(..., description="Beneficiary age")
    sex: Literal['M', 'F', '1', '2'] = Field(..., description="Beneficiary sex")
    dual_elgbl_cd: Literal[None, 'NA', '99', '00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10'] = Field('NA', description="Dual status code")
    orec: Literal[None, '0', '1', '2', '3'] = Field('0', description="Original reason for entitlement")
    crec: Literal[None, '0', '1', '2', '3'] = Field('0', description="Current reason for entitlement")
    new_enrollee: bool = Field(False, description="True if beneficiary is a new enrollee")
    snp: bool = Field(False, description="True if beneficiary is in SNP")
    version: str = Field("V2", description="Version of categorization used (V2, V4, V6)")
    low_income: bool = Field(False, description="True if beneficiary is in low income; RxHCC only")
    graft_months: Optional[int] = Field(None, description="Number of months since transplant; ESRD Model only")
    category: str = Field(..., description="[derived] Age-sex category code")
    non_aged: bool = Field(False, description="[derived] True if age <= 64")
    orig_disabled: bool = Field(False, description="[derived] True if originally disabled (OREC='1' and not currently disabled)")
    disabled: bool = Field(False, description="[derived] True if currently disabled (age < 65 and OREC != '0')")
    esrd: bool = Field(False, description="[derived] True if ESRD (ESRD Model)")
    lti: bool = Field(False, description="[derived] True if LTI (LTI Model)") 
    fbd: bool = Field(False, description="[derived] True if FBD (FBD Model)") 
    pbd: bool = Field(False, description="[derived] True if PBD (PBD Model)")


class RAFResult(TypedDict):
    """Type definition for RAF calculation results"""
    risk_score: float
    hcc_list: List[str]
    details: Dict[str, Any]
    service_level_data: List[ServiceLevelData]