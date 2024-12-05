from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Literal
from datetime import date

SYSTEMS = {
    'dx': 'http://hl7.org/fhir/sid/icd-10-cm',
    'pr': 'https://bluebutton.cms.gov/resources/codesystem/hcpcs',
    'specialty': 'https://bluebutton.cms.gov/resources/variables/prvdr_spclty',
    'role': 'http://hl7.org/fhir/us/carin-bb/CodeSystem/C4BBClaimCareTeamRole',
    'claim_type': 'https://bluebutton.cms.gov/resources/variables/nch_clm_type_cd'
}

# Models
class Coding(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None

class CodeableConcept(BaseModel):
    coding: Optional[List[Coding]] = []

class Period(BaseModel):
    start: Optional[date] = None
    end: Optional[date] = None

class Diagnosis(BaseModel):
    sequence: Optional[int] = None
    diagnosisCodeableConcept: Optional[CodeableConcept] = None

class CareTeamMember(BaseModel):
    role: Optional[CodeableConcept] = None
    qualification: Optional[CodeableConcept] = None

class EoBItem(BaseModel):
    productOrService: Optional[CodeableConcept] = None
    diagnosisSequence: Optional[List[int]] = None
    servicedPeriod: Optional[Period] = None

class ExplanationOfBenefit(BaseModel):
    model_config = ConfigDict(frozen=True)
    resourceType: Literal["ExplanationOfBenefit"] = "ExplanationOfBenefit"
    type: Optional[CodeableConcept] = None
    diagnosis: Optional[List[Diagnosis]] = []
    item: Optional[List[EoBItem]] = []
    careTeam: Optional[List[CareTeamMember]] = []
    billablePeriod: Optional[Period] = None

def extract_mde(eob_data: dict) -> List[dict]:
    """Extract medical data elements from FHIR ExplanationOfBenefit data."""
    try:
        eob = ExplanationOfBenefit.model_validate(eob_data)
        
        # Get codes from CodeableConcept
        get_code = lambda concept, system: next((
            c.code for c in (concept.coding or [])
            if c and c.system == system and c.code
        ), None)
        
        # Get date from Period
        get_date = lambda period: (
            period.end.isoformat() if period and period.end
            else period.start.isoformat() if period and period.start
            else None
        )
        
        # Create diagnosis lookup
        dx_lookup = {
            d.sequence: get_code(d.diagnosisCodeableConcept, SYSTEMS['dx'])
            for d in (eob.diagnosis or [])
            if d.sequence is not None and d.diagnosisCodeableConcept
        }
        
        # Get claim-level data
        claim_type = get_code(eob.type, SYSTEMS['claim_type'])
        
        # Get provider specialty
        specialty = next((
            get_code(m.qualification, SYSTEMS['specialty'])
            for m in (eob.careTeam or [])
            if m.role and m.qualification
            and get_code(m.role, SYSTEMS['role']) in {'performing', 'rendering'}
        ), None)
        
        results = []
        for item in (eob.item or []):
            if not item.productOrService:
                continue
                
            pr_code = get_code(item.productOrService, SYSTEMS['pr'])
            if not pr_code:
                continue
            
            # Get associated data
            dos = get_date(item.servicedPeriod) or get_date(eob.billablePeriod)
            dx_codes = [dx_lookup[seq] for seq in (item.diagnosisSequence or [])
                       if seq in dx_lookup]
            
            # Build result
            result = {k: v for k, v in {
                'procedure_code': pr_code,
                'diagnosis_codes': dx_codes,
                'claim_type': claim_type,
                'provider_specialty': specialty,
                'service_date': dos
            }.items()}
            
            results.append(result)
            
        return results
        
    except Exception as e:
        raise ValueError(f"Error processing EOB: {str(e)}")

def extract_mde_list(eob_data_list: List[dict]) -> List[dict]:
    """Process a list of EOB data dictionaries."""
    results = []
    for eob_data in eob_data_list:
        try:
            results.extend(extract_mde(eob_data))
        except ValueError as e:
            print(f"Warning: Skipping invalid EOB: {str(e)}")
    return results