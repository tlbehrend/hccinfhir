from pydantic import BaseModel, ConfigDict, HttpUrl
from typing import List, Optional, Literal, Final
from datetime import date
from urllib.parse import urlparse

# Constants
SYSTEMS: Final = {
    'dx': HttpUrl('http://hl7.org/fhir/sid/icd-10-cm'),
    'pr': HttpUrl('https://bluebutton.cms.gov/resources/codesystem/hcpcs'),
    'specialty': HttpUrl('https://bluebutton.cms.gov/resources/variables/prvdr_spclty'),
    'claim_type': HttpUrl('https://bluebutton.cms.gov/resources/variables/nch_clm_type_cd')
}

# Models
class Coding(BaseModel):
    system: HttpUrl
    code: str
    display: Optional[str] = None

    def model_post_init(self, _) -> None:
        # Validate URL format
        urlparse(str(self.system))

class CodeableConcept(BaseModel):
    coding: List[Coding]

class Diagnosis(BaseModel):
    sequence: int
    diagnosisCodeableConcept: CodeableConcept
    type: Optional[List[CodeableConcept]] = None

class IdentifierType(BaseModel):
    coding: List[Coding]

class Identifier(BaseModel):
    type: IdentifierType
    value: str

class Provider(BaseModel):
    identifier: Identifier

class CareTeamMember(BaseModel):
    sequence: int
    provider: Provider
    qualification: CodeableConcept
    role: CodeableConcept

class Period(BaseModel):
    start: date
    end: date

class ServiceQuantity(BaseModel):
    value: float

class EoBItem(BaseModel):
    sequence: int
    productOrService: CodeableConcept
    diagnosisSequence: Optional[List[int]] = None
    servicedPeriod: Optional[Period] = None
    quantity: Optional[ServiceQuantity] = None

class ExplanationOfBenefit(BaseModel):
    model_config = ConfigDict(frozen=True)
    resourceType: Literal["ExplanationOfBenefit"] = "ExplanationOfBenefit"
    type: CodeableConcept
    diagnosis: List[Diagnosis] = []
    item: List[EoBItem] = []
    careTeam: List[CareTeamMember] = []
    billablePeriod: Period

def extract_mde(eob_data: dict) -> List[dict]:
    """
    Extract procedure details with associated diagnoses, provider specialty, and dates
    from FHIR ExplanationOfBenefit data.

    Args:
        eob_data (dict): Raw FHIR ExplanationOfBenefit JSON data

    Returns:
        List[dict]: List of procedures with details including:
            - pr: Procedure code
            - dx: Associated diagnosis codes
            - type: Claim type code
            - prvdr_spclty: Provider specialty code
            - dos: Date of service (ISO format)

    Raises:
        ValueError: If EOB data is invalid or processing fails
    """
    try:
        eob = ExplanationOfBenefit.model_validate(eob_data)
        
        # Create diagnosis lookup for ICD-10-CM diagnoses
        diagnosis_lookup = {
            d.sequence: d.diagnosisCodeableConcept.coding[0].code 
            for d in eob.diagnosis
            if d.diagnosisCodeableConcept.coding[0].system == SYSTEMS['dx']
        }
        
        # Extract claim type and provider specialty
        nch_type = next(
            (coding.code for coding in eob.type.coding 
             if coding.system == SYSTEMS['claim_type']),
            None
        )
        
        # provider specialty extraction
        # attending/operation roles are not extracted, as inpatient claims are filtered based on ToB (Type of BIll)
        provider_specialty = next(
            (member.qualification.coding[0].code for member in eob.careTeam
             if member.role.coding[0].code in {"performing", "rendering"} and 
                member.qualification.coding[0].system == SYSTEMS['specialty']),
            None
        )
        
        # Process procedures
        return [
            {
                "pr": item.productOrService.coding[0].code,
                "dx": [diagnosis_lookup.get(seq) for seq in (item.diagnosisSequence or [])],
                "type": nch_type,
                "prvdr_spclty": provider_specialty,
                "dos": (item.servicedPeriod.end if item.servicedPeriod 
                       else eob.billablePeriod.end).isoformat()
            }
            for item in eob.item
            if item.productOrService.coding[0].system == SYSTEMS['pr']
        ]
        
    except Exception as e:
        raise ValueError(f"Error processing EOB: {str(e)}")
    
def extract_mde_list(eob_data_list: List[dict]) -> List[dict]:
    """
    Wrapper function to extract MDE from a list of EOB data dictionaries.
    
    Args:
        eob_data_list: List of EOB data dictionaries
        
    Returns:
        List of extracted MDE dictionaries
    """
    result = []
    for eob_data in eob_data_list:
        result.extend(extract_mde(eob_data))
    return result