from pydantic import BaseModel
from typing import List, Optional, Dict, Tuple
from datetime import date, datetime
from models import MinimalDataElement

class X12Parser:
    """Helper class to parse X12 segments"""
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[str]:
        """Convert X12 date format to ISO format"""
        if not date_str or len(date_str) != 8:
            return None
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            return None

    @staticmethod
    def parse_amount(amount_str: str) -> Optional[float]:
        """Convert X12 amount string to float"""
        try:
            return float(amount_str)
        except:
            return None

class LoopTracker:
    """Helper class to track X12 837 loops"""
    def __init__(self):
        self.current_2000B = False  # Subscriber Loop
        self.current_2300 = False   # Claim Loop
        self.current_2310B = False  # Rendering Provider Loop
        self.current_2400 = False   # Service Line Loop
        
    def enter_loop(self, segment: List[str]) -> None:
        """Track entry into loops based on segment triggers"""
        seg_id = segment[0]
        
        if seg_id == 'NM1':
            if segment[1] == 'IL':  # Subscriber Loop
                self.current_2000B = True
                self.reset_claim_loops()
            elif segment[1] == '82':  # Rendering Provider
                self.current_2310B = True
        elif seg_id == 'CLM':  # Claim Information
            self.current_2300 = True
            self.current_2310B = False
            self.current_2400 = False
        elif seg_id == 'SV1':  # Service Line
            self.current_2400 = True
            
    def reset_claim_loops(self):
        """Reset claim-related loops"""
        self.current_2300 = False
        self.current_2310B = False
        self.current_2400 = False
        
    def exit_loop(self, segment: List[str]) -> None:
        """Track exit from loops based on segment triggers"""
        seg_id = segment[0]
        
        if seg_id == 'SE':  # End of Transaction
            self.__init__()
        elif self.current_2400 and seg_id in ['LX', 'CLM']:
            self.current_2400 = False
        elif self.current_2310B and seg_id in ['SV1', 'CLM']:
            self.current_2310B = False
        elif self.current_2300 and seg_id == 'NM1' and segment[1] == 'IL':
            self.reset_claim_loops()

def process_service_line(segments: List[List[str]], start_index: int) -> Tuple[str, str]:
    """Process NDC and service date from service line segments"""
    ndc = None
    service_date = None
    
    for seg in segments[start_index:]:
        if seg[0] in ['LX', 'CLM', 'SE']:
            break
        elif seg[0] == 'LIN' and len(seg) > 3 and seg[2] == 'N4':
            ndc = seg[3]
        elif seg[0] == 'DTP' and seg[1] == '472':
            service_date = X12Parser.parse_date(seg[3])
            
    return ndc, service_date

def extract_mde_837(content: str) -> List[MinimalDataElement]:
    """Extract MDEs from 837 format"""
    segments = [[el.strip() for el in seg.split('*')] for seg in content.split('~') if seg]
    encounters = []
    parser = X12Parser()
    loop_tracker = LoopTracker()
    
    # Claim-level data
    current_data = {
        'patient_id': None,
        'rendering_provider_npi': None,
        'provider_specialty': None,
        'facility_type': None,
        'claim_type': None,
        'dx_lookup': {}
    }
    
    for i, segment in enumerate(segments):
        if not segment or len(segment) < 2:
            continue
            
        seg_id = segment[0]
        loop_tracker.enter_loop(segment)
        
        # Subscriber/Patient ID (2000B loop)
        if seg_id == 'NM1' and segment[1] == 'IL' and loop_tracker.current_2000B:
            current_data['patient_id'] = segment[9] if len(segment) > 9 else None
            
        # Rendering Provider NPI (2310B loop)
        elif seg_id == 'NM1' and segment[1] == '82' and loop_tracker.current_2310B:
            current_data['rendering_provider_npi'] = segment[9] if len(segment) > 9 else None
            
        # Rendering Provider Specialty (2310B loop)
        elif seg_id == 'PRV' and segment[1] == 'PE' and loop_tracker.current_2310B:
            current_data['provider_specialty'] = segment[3] if len(segment) > 3 else None
            
        # Claim Type and Facility (2300 loop)
        elif seg_id == 'CLM' and loop_tracker.current_2300:
            if len(segment) > 5 and ':' in segment[5]:
                claim_info = segment[5].split(':')
                current_data['claim_type'] = claim_info[1] if len(claim_info) > 1 else None
                current_data['facility_type'] = claim_info[2] if len(claim_info) > 2 else None
                
        # Diagnosis Codes (2300 loop)
        elif seg_id == 'HI' and loop_tracker.current_2300:
            current_data['dx_lookup'] = {}
            for pos, element in enumerate(segment[1:], 1):
                if ':' in element:
                    qualifier, code = element.split(':')[:2]
                    if qualifier in ['ABK', 'ABF']:  # ICD-10 qualifiers
                        current_data['dx_lookup'][str(pos)] = code
                        
        # Service Line (2400 loop)
        elif seg_id == 'SV1' and loop_tracker.current_2400:
            # Parse procedure code and modifiers
            proc_info = segment[1].split(':')
            procedure_code = proc_info[1] if len(proc_info) > 1 else None
            modifiers = proc_info[2:] if len(proc_info) > 2 else []
            
            # Parse diagnosis pointers
            dx_pointers = segment[7].split(',') if len(segment) > 7 else []
            linked_diagnoses = [
                current_data['dx_lookup'][pointer]
                for pointer in dx_pointers
                if pointer in current_data['dx_lookup']
            ]
            
            # Process service line details
            ndc, service_date = process_service_line(segments, i)
            
            # Create MDE
            mde = MinimalDataElement(
                procedure_code=procedure_code,
                diagnosis_codes=linked_diagnoses,
                claim_type=current_data['claim_type'],
                provider_specialty=current_data['provider_specialty'],
                provider_npi=current_data['rendering_provider_npi'],
                patient_id=current_data['patient_id'],
                facility_type=current_data['facility_type'],
                service_date=service_date,
                place_of_service=segment[6] if len(segment) > 6 else None,
                quantity=parser.parse_amount(segment[4]) if len(segment) > 4 else None,
                quantity_unit=segment[5] if len(segment) > 5 else None,
                modifiers=modifiers,
                ndc=ndc,
                allowed_amount=None
            )
            encounters.append(mde)
            
        loop_tracker.exit_loop(segment)
    
    return encounters