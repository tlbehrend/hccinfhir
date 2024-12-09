from pydantic import BaseModel, ConfigDict, Field, AliasChoices
from typing import List, Optional, Literal, TypedDict
from datetime import date
from .models import ServiceLevelData

# Core system URLs for different code types
SYSTEMS = {
    'icd10cm': 'http://hl7.org/fhir/sid/icd-10-cm',
    'icd10': 'http://hl7.org/fhir/sid/icd-10',
    'pr': 'https://bluebutton.cms.gov/resources/codesystem/hcpcs',
    'specialty': 'https://bluebutton.cms.gov/resources/variables/prvdr_spclty',
    'role': 'http://hl7.org/fhir/us/carin-bb/CodeSystem/C4BBClaimCareTeamRole',
    'claim_type': 'https://bluebutton.cms.gov/resources/variables/nch_clm_type_cd',
    'facility_type': 'https://bluebutton.cms.gov/resources/variables/clm_fac_type_cd',
    'service_type': 'https://bluebutton.cms.gov/resources/variables/clm_srvc_clsfctn_type_cd',
    'place_of_service': 'https://bluebutton.cms.gov/resources/variables/line_place_of_srvc_cd',
    'npi': 'http://hl7.org/fhir/us/carin-bb/CodeSystem/C4BBIdentifierType',
    'ndc': 'http://hl7.org/fhir/sid/ndc'
}


# FHIR Resource Models
class Coding(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None

class CodeableConcept(BaseModel):
    coding: Optional[List[Coding]] = []
    extension: Optional[List[dict]] = None 

class Identifier(BaseModel):
    type: Optional[CodeableConcept] = None
    value: Optional[str] = None

class Provider(BaseModel):
    identifier: Optional[Identifier] = None

class SimpleQuantity(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None

class Period(BaseModel):
    start: Optional[date] = None
    end: Optional[date] = None

class Amount(BaseModel):
    value: Optional[float] = None
    currency: Optional[str] = None

class Adjudication(BaseModel):
    category: Optional[CodeableConcept] = None
    amount: Optional[Amount] = None

class Diagnosis(BaseModel):
    sequence: Optional[int] = None
    diagnosisCodeableConcept: Optional[CodeableConcept] = None

class CareTeamMember(BaseModel):
    role: Optional[CodeableConcept] = None
    qualification: Optional[CodeableConcept] = None
    provider: Optional[Provider] = None

class EoBItem(BaseModel):
    productOrService: Optional[CodeableConcept] = Field(
        None, 
        validation_alias=AliasChoices('service', 'productOrService')
    )
    quantity: Optional[SimpleQuantity] = None
    diagnosisSequence: Optional[List[int]] = None
    servicedPeriod: Optional[Period] = None
    locationCodeableConcept: Optional[CodeableConcept] = None
    modifier: Optional[List[CodeableConcept]] = None
    adjudication: Optional[List[Adjudication]] = None

class ExplanationOfBenefit(BaseModel):
    model_config = ConfigDict(frozen=True)
    resourceType: Literal["ExplanationOfBenefit"] = "ExplanationOfBenefit"
    type: Optional[CodeableConcept] = None
    diagnosis: Optional[List[Diagnosis]] = []
    item: Optional[List[EoBItem]] = []
    careTeam: Optional[List[CareTeamMember]] = []
    billablePeriod: Optional[Period] = None
    patient: Optional[dict] = None
    facility: Optional[dict] = None
    extension: Optional[List[dict]] = None
    contained: Optional[List[dict]] = None

class FHIRExtractor:
    """Helper class for extracting data from FHIR resources"""
    
    @staticmethod
    def get_code(concept: Optional[CodeableConcept], system: str) -> Optional[str]:
        """Extract code from CodeableConcept for given system"""
        if not concept or not concept.coding:
            return None
        return next((
            c.code for c in concept.coding 
            if c and c.system == system and c.code
        ), None)

    @staticmethod
    def get_date(period: Optional[Period]) -> Optional[str]:
        """Get ISO formatted date from Period, preferring end date"""
        if not period:
            return None
        return (period.end.isoformat() if period.end 
                else period.start.isoformat() if period.start 
                else None)

    @staticmethod
    def get_npi(provider: Optional[Provider]) -> Optional[str]:
        """Extract NPI from Provider identifier"""
        if not provider or not provider.identifier:
            return None
        return (provider.identifier.value 
                if any(c.system == SYSTEMS['npi'] for c in (provider.identifier.type.coding or [])) 
                else None)

    @staticmethod
    def get_allowed_amount(item: EoBItem) -> Optional[float]:
        """Extract allowed amount from item adjudications"""
        if not item.adjudication:
            return None
        return next((
            adj.amount.value for adj in item.adjudication 
            if any(c.code == 'eligible' for c in (adj.category.coding or []))
        ), None)

    @staticmethod
    def find_extension_code(extensions: List[dict], system_url: str) -> Optional[str]:
        """Find code in extension array matching system URL"""
        for ext in extensions:
            if ext.get('url') == system_url:
                return ext.get('valueCoding', {}).get('code')
        return None

class DiagnosisLookup(TypedDict):
    sequence: int
    code: str

class CommonData(TypedDict):
    claim_type: Optional[str]
    provider_specialty: Optional[str]
    performing_provider_npi: Optional[str]
    patient_id: Optional[str]
    facility_type: Optional[str]
    service_type: Optional[str]
    billing_provider_npi: Optional[str]

def extract_sld_fhir(eob_data: dict) -> List[ServiceLevelData]:
    """Extract medical data elements from FHIR ExplanationOfBenefit"""
    try:
        eob = ExplanationOfBenefit.model_validate(eob_data)
        extractor = FHIRExtractor()
        
        # Build diagnosis lookup for faster access
        dx_lookup = {
            d.sequence: (extractor.get_code(d.diagnosisCodeableConcept, SYSTEMS['icd10cm'])
                         or extractor.get_code(d.diagnosisCodeableConcept, SYSTEMS['icd10']))
            for d in (eob.diagnosis or [])
            if d.sequence is not None and d.diagnosisCodeableConcept
        }

        # Find rendering provider from care team
        rendering_provider = next((
            m for m in eob.careTeam or []
            if m.role and extractor.get_code(m.role, SYSTEMS['role']) in {'performing', 'rendering'}
        ), None)

        # Extract claim-level data
        common_data = {
            'claim_type': extractor.get_code(eob.type, SYSTEMS['claim_type']),
            'provider_specialty': (extractor.get_code(rendering_provider.qualification, SYSTEMS['specialty']) 
                                 if rendering_provider else None),
            'performing_provider_npi': (extractor.get_npi(rendering_provider.provider) 
                           if rendering_provider else None),
            'patient_id': (eob.patient.get('reference', '').split('/')[-1] 
                         if eob.patient else None),
            'facility_type': (extractor.find_extension_code(eob.facility.get('extension', []), 
                                                          SYSTEMS['facility_type']) 
                            if eob.facility else None),
            'service_type': extractor.find_extension_code(eob_data.get('extension', []), 
                                                        SYSTEMS['service_type']),
            'billing_provider_npi': next((i.get('value') 
                   for c in (eob.contained or [])
                   for i in c.get('identifier', [])
                   if i.get('system') == 'http://hl7.org/fhir/sid/us-npi'), None)
        }

        if common_data['facility_type'] is not None and common_data['service_type'] is None:
            # In the  old version of BCDA, the service_type was found in `type`
            common_data['service_type'] = extractor.get_code(eob.type, SYSTEMS['service_type'])

        # Process each service item
        results = []
        for item in eob.item:
            
            procedure_code = extractor.get_code(item.productOrService, SYSTEMS['pr']) if item.productOrService else None
            
            ndc = extractor.get_code(item.productOrService, SYSTEMS['ndc']) if item.productOrService else None
            if ndc is None and item.productOrService and 'extension' in item.productOrService:
                 ndc = extractor.find_extension_code(item.productOrService.get('extension', []),
                                              SYSTEMS['ndc'])

            if not procedure_code and not ndc:
                continue

            results.append({
                **common_data,
                'procedure_code': extractor.get_code(item.productOrService, SYSTEMS['pr']) if item.productOrService else None,
                'ndc': extractor.get_code(item.productOrService, SYSTEMS['ndc']) if item.productOrService else None,
                'quantity': item.quantity.value if item.quantity else None,
                'quantity_unit': item.quantity.unit if item.quantity else None,
                'linked_diagnosis_codes': [dx_lookup[seq] for seq in (item.diagnosisSequence or []) 
                                    if seq in dx_lookup],
                'claim_diagnosis_codes': list(dx_lookup.values()),
                'service_date': (extractor.get_date(item.servicedPeriod) or 
                                extractor.get_date(eob.billablePeriod)),
                'place_of_service': extractor.get_code(item.locationCodeableConcept, 
                                                        SYSTEMS['place_of_service']),
                'modifiers': [extractor.get_code(m, SYSTEMS['pr']) 
                            for m in (item.modifier or []) if m],
                    'allowed_amount': extractor.get_allowed_amount(item)
                })
        
        if len(results) == 0:
            results.append({
                **common_data,
                'linked_diagnosis_codes': [],
                'claim_diagnosis_codes': list(dx_lookup.values()),
                'service_date': extractor.get_date(eob.billablePeriod),
                'procedure_code': None,
                'ndc': None,
                'quantity': None,
                'quantity_unit': None,
                'place_of_service': None,
                'modifiers': [],
                'allowed_amount': None
            })
        
        return [ServiceLevelData.model_validate(r) for r in results]

    except ValueError as e:
        raise ValueError(f"Error processing EOB: {str(e)}")


