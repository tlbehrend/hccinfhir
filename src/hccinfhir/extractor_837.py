from typing import List, Optional, Tuple, Dict
from .models import ServiceLevelData
import re

class X12Parser:
    """Parser for X12 837 Professional and Institutional claims"""
    
    VERSION_MAP = {
        "005010X222A1": "professional",     # 837P
        "005010X223A2": "institutional"     # 837I
    }
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[str]:
        """Convert 8-digit date string to ISO format YYYY-MM-DD"""
        if not re.match(r'^\d{8}$', date_str):
            return None
            
        try:
            year, month, day = date_str[:4], date_str[4:6], date_str[6:8]
            return f"{year}-{month}-{day}"
        except:
            return None

    @staticmethod
    def parse_amount(amount_str: str) -> Optional[float]:
        """Convert string to float, return None if invalid"""
        try:
            return float(amount_str)
        except:
            return None

class ClaimData:
    """Container for claim-level data"""
    def __init__(self, claim_type: str):
        self.patient_id = None
        self.performing_provider_npi = None
        self.billing_provider_npi = None
        self.provider_specialty = None
        self.facility_type = None
        self.service_type = None
        self.claim_type = claim_type
        self.dx_lookup: Dict[str, str] = {}

def get_segment_value(segment: List[str], index: int) -> Optional[str]:
    """Safely get value from segment at given index"""
    return segment[index] if len(segment) > index else None

def parse_diagnosis_codes(segment: List[str]) -> Dict[str, str]:
    """Extract diagnosis codes from HI segment"""
    dx_lookup = {}
    for pos, element in enumerate(segment[1:], 1):
        if ':' not in element:
            continue
        qualifier, code = element.split(':')[:2]
        if qualifier in ['ABK', 'ABF']:  # ICD-10 qualifiers
            dx_lookup[str(pos)] = code
    return dx_lookup

def process_service_line(segments: List[List[str]], start_index: int) -> Tuple[Optional[str], Optional[str]]:
    """Extract NDC and service date from service line segments"""
    ndc = None
    service_date = None
    for seg in segments[start_index:]:
        if seg[0] in ['LX', 'CLM', 'SE']:
            break
        if seg[0] == 'LIN' and len(seg) > 3 and seg[2] == 'N4':
            ndc = seg[3]
        elif seg[0] == 'DTP' and seg[1] == '472':
            service_date = X12Parser.parse_date(seg[3])
        elif ndc and service_date:
            break
    return ndc, service_date

def extract_sld_837(content: str) -> List[ServiceLevelData]:
    """Extract MDEs from 837 Professional or Institutional claims"""
    if not content:
        raise ValueError("Input X12 data cannot be empty")
    
    # Split content into segments
    segments = [seg.strip().split('*') for seg in content.split('~') if seg.strip()]
    
    # Detect claim type from GS segment
    claim_type = None
    for segment in segments:
        if segment[0] == 'GS' and len(segment) > 8:
            claim_type = X12Parser.VERSION_MAP.get(segment[8])
            break
    
    if not claim_type:
        raise ValueError("Invalid or unsupported 837 format")
    
    encounters = []
    current_data = ClaimData(claim_type)
    in_claim_loop = False
    in_rendering_provider_loop = False
    
    for i, segment in enumerate(segments):
        if len(segment) < 2:
            continue
            
        seg_id = segment[0]
        
        # Handle different loops and segments
        if seg_id == 'NM1':
            if segment[1] == 'IL':  # Subscriber
                current_data.patient_id = get_segment_value(segment, 9)
                in_claim_loop = False
                in_rendering_provider_loop = False
            elif segment[1] == '82' and len(segment) > 8 and segment[8] == 'XX':  # Rendering Provider
                current_data.performing_provider_npi = get_segment_value(segment, 9)
                in_rendering_provider_loop = True
            elif segment[1] == '85' and len(segment) > 8 and segment[8] == 'XX':  # Billing Provider NPI
                current_data.billing_provider_npi = get_segment_value(segment, 9)
                
        elif seg_id == 'PRV' and segment[1] == 'PE' and in_rendering_provider_loop:
            current_data.provider_specialty = get_segment_value(segment, 3)
            
        elif seg_id == 'CLM':
            in_claim_loop = True
            in_rendering_provider_loop = False
            if claim_type == "institutional" and len(segment) > 5 and ':' in segment[5]:
                current_data.facility_type = segment[5][0]
                if len(segment[5]) > 0:
                    current_data.service_type = segment[5][1]

        elif seg_id == 'HI' and in_claim_loop:  # Diagnosis
            current_data.dx_lookup = parse_diagnosis_codes(segment)
            
        elif seg_id in ['SV1', 'SV2'] and in_claim_loop:  # Service
            # Parse procedure info
            proc_info = segment[1].split(':')
            procedure_code = proc_info[1] if len(proc_info) > 1 else None
            modifiers = proc_info[2:] if len(proc_info) > 2 else []
            
            # Get diagnosis pointers
            dx_pointer_pos = 7 if seg_id == 'SV1' else 11
            dx_pointers = get_segment_value(segment, dx_pointer_pos)
            linked_diagnoses = [
                current_data.dx_lookup[pointer]
                for pointer in (dx_pointers.split(',') if dx_pointers else [])
                if pointer in current_data.dx_lookup
            ]
            
            # Get service details
            ndc, service_date = process_service_line(segments, i)
            
            # Create encounter record
            mde = ServiceLevelData(
                procedure_code=procedure_code,
                linked_diagnosis_codes=linked_diagnoses,
                claim_diagnosis_codes=current_data.dx_lookup.values(),
                claim_type=current_data.claim_type,
                provider_specialty=current_data.provider_specialty,
                performing_provider_npi=current_data.performing_provider_npi,
                billing_provider_npi=current_data.billing_provider_npi,
                patient_id=current_data.patient_id,
                facility_type=current_data.facility_type,
                service_type=current_data.service_type,
                service_date=service_date,
                place_of_service=get_segment_value(segment, 6) if seg_id == 'SV1' else None,
                quantity=X12Parser.parse_amount(get_segment_value(segment, 4)),
                quantity_unit=get_segment_value(segment, 5),
                modifiers=modifiers,
                ndc=ndc,
                allowed_amount=None
            )
            encounters.append(mde)
    
    return encounters