from pydantic import BaseModel, ConfigDict, Field, AliasChoices
from typing import List, Optional, Literal, TypedDict
from datetime import date
from .models import ServiceLevelData

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

class BaseCodeModel(BaseModel):
    coding: Optional[List['Coding']] = []
    extension: Optional[List[dict]] = None

class Coding(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None

class Identifier(BaseModel):
    type: Optional[BaseCodeModel] = None
    value: Optional[str] = None

class Provider(BaseModel):
    identifier: Optional[Identifier] = None

class Period(BaseModel):
    start: Optional[date] = None
    end: Optional[date] = None

class Amount(BaseModel):
    value: Optional[float] = None
    currency: Optional[str] = None

class EoBItem(BaseModel):
    productOrService: Optional[BaseCodeModel] = Field(None, validation_alias=AliasChoices('service', 'productOrService'))
    quantity: Optional[dict] = None  # Simplified from SimpleQuantity
    diagnosisSequence: Optional[List[int]] = None
    servicedPeriod: Optional[Period] = None
    locationCodeableConcept: Optional[BaseCodeModel] = None
    modifier: Optional[List[BaseCodeModel]] = None
    adjudication: Optional[List[dict]] = None  # Simplified from Adjudication

class ExplanationOfBenefit(BaseModel):
    model_config = ConfigDict(frozen=True)
    resourceType: Literal["ExplanationOfBenefit"] = "ExplanationOfBenefit"
    id: Optional[str] = None
    type: Optional[BaseCodeModel] = None
    diagnosis: Optional[List[dict]] = []  # Simplified from Diagnosis
    item: Optional[List[EoBItem]] = []
    careTeam: Optional[List[dict]] = []  # Simplified from CareTeamMember
    billablePeriod: Optional[Period] = None
    patient: Optional[dict] = None
    facility: Optional[dict] = None
    extension: Optional[List[dict]] = None
    contained: Optional[List[dict]] = None


def get_code(concept: Optional[BaseCodeModel], system: str) -> Optional[str]:
    if not concept or not concept.coding:
        return None
    return next((c.code for c in concept.coding if c and c.system == system and c.code), None)

def get_date(period: Optional[Period]) -> Optional[str]:
    if not period:
        return None
    return period.end.isoformat() if period.end else period.start.isoformat() if period.start else None

def find_extension_code(extensions: List[dict], system_url: str) -> Optional[str]:
    for ext in extensions:
        if ext.get('url') == system_url:
            return ext.get('valueCoding', {}).get('code')
    return None

def extract_sld_fhir(eob_data: dict) -> List[ServiceLevelData]:
    try:
        eob = ExplanationOfBenefit.model_validate(eob_data)
        
        dx_lookup = {
            d['sequence']: (get_code(BaseCodeModel(coding=d.get('diagnosisCodeableConcept', {}).get('coding', [])), 
                                             SYSTEMS['icd10cm']) or
                          get_code(BaseCodeModel(coding=d.get('diagnosisCodeableConcept', {}).get('coding', [])), 
                                           SYSTEMS['icd10']))
            for d in (eob.diagnosis or [])
            if d.get('sequence') is not None
        }

        rendering_provider = next((
            m for m in eob.careTeam or []
            if m.get('role') and get_code(BaseCodeModel(coding=m['role'].get('coding', [])), 
                                                   SYSTEMS['role']) in {'performing', 'rendering'}
        ), None)

        common_data = {
            'claim_id': eob.id,
            'claim_type': get_code(eob.type, SYSTEMS['claim_type']),
            'provider_specialty': (get_code(BaseCodeModel(coding=rendering_provider['qualification'].get('coding', [])), 
                                                    SYSTEMS['specialty']) if rendering_provider else None),
            'performing_provider_npi': (rendering_provider.get('provider', {}).get('identifier', {}).get('value') 
                                      if rendering_provider else None),
            'patient_id': eob.patient.get('reference', '').split('/')[-1] if eob.patient else None,
            'facility_type': (find_extension_code(eob.facility.get('extension', []), SYSTEMS['facility_type']) 
                            if eob.facility else None),
            'service_type': (find_extension_code(eob_data.get('extension', []), SYSTEMS['service_type']) or
                           get_code(eob.type, SYSTEMS['service_type'])),
            'billing_provider_npi': next((i.get('value') 
                                        for c in (eob.contained or [])
                                        for i in c.get('identifier', [])
                                        if i.get('system') == 'http://hl7.org/fhir/sid/us-npi'), None)
        }

        results = []
        for item in eob.item or []:
            if not item.productOrService:
                continue

            service_data = {
                **common_data,
                'procedure_code': get_code(item.productOrService, SYSTEMS['pr']),
                'ndc': (get_code(item.productOrService, SYSTEMS['ndc']) or
                       find_extension_code(item.productOrService.extension or [], SYSTEMS['ndc'])),
                'quantity': item.quantity.get('value') if item.quantity else None,
                'quantity_unit': item.quantity.get('unit') if item.quantity else None,
                'linked_diagnosis_codes': [dx_lookup[seq] for seq in (item.diagnosisSequence or []) if seq in dx_lookup],
                'claim_diagnosis_codes': list(dx_lookup.values()),
                'service_date': get_date(item.servicedPeriod) or get_date(eob.billablePeriod),
                'place_of_service': get_code(item.locationCodeableConcept, SYSTEMS['place_of_service']),
                'modifiers': [get_code(m, SYSTEMS['pr']) for m in (item.modifier or []) if m],
                'allowed_amount': next((adj.get('amount', {}).get('value') 
                                      for adj in (item.adjudication or [])
                                      if any(c.get('code') == 'eligible' 
                                           for c in adj.get('category', {}).get('coding', []))), None)
            }

            if service_data['procedure_code'] or service_data['ndc']:
                results.append(service_data)

        if not results:
            results.append({
                **common_data,
                'linked_diagnosis_codes': [],
                'claim_diagnosis_codes': list(dx_lookup.values()),
                'service_date': get_date(eob.billablePeriod),
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