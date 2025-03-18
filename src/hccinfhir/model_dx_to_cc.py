from typing import List, Dict, Set, Tuple, Optional
import importlib.resources
from hccinfhir.datamodels import ModelName

# Load default mappings from csv file
mapping_file_default = 'ra_dx_to_cc_2025.csv'
dx_to_cc_default: Dict[Tuple[str, ModelName], Set[str]] = {}  # (diagnosis_code, model_name) -> cc

try:
    with importlib.resources.open_text('hccinfhir.data', mapping_file_default) as f:
        for line in f.readlines()[1:]:  # Skip header
            try:
                diagnosis_code, cc, model_name = line.strip().split(',')
                key = (diagnosis_code, model_name)
                if key not in dx_to_cc_default:
                    dx_to_cc_default[key] = {cc}
                else:
                    dx_to_cc_default[key].add(cc)
            except ValueError:
                continue  # Skip malformed lines
except Exception as e:
    print(f"Error loading mapping file: {e}")
    dx_to_cc_default = {}

def get_cc(
    diagnosis_code: str,
    model_name: ModelName = "CMS-HCC Model V28",
    dx_to_cc: Dict[Tuple[str, str], Set[str]] = dx_to_cc_default
) -> Optional[Set[str]]:
    """
    Get CC for a single diagnosis code.

    Args:
        diagnosis_code: ICD-10 diagnosis code
        model_name: HCC model name to use for mapping
        dx_to_cc: Optional custom mapping dictionary

    Returns:
        CC code if found, None otherwise
    """
    return dx_to_cc.get((diagnosis_code, model_name))

def apply_mapping(
    diagnoses: List[str],
    model_name: ModelName = "CMS-HCC Model V28", 
    dx_to_cc: Dict[Tuple[str, str], Set[str]] = dx_to_cc_default
) -> Dict[str, Set[str]]:
    """
    Apply ICD-10 to CC mapping for a list of diagnosis codes.
    
    Args:
        diagnoses: List of ICD-10 diagnosis codes
        model_name: HCC model name to use for mapping
        dx_to_cc: Optional custom mapping dictionary
        
    Returns:
        Dictionary mapping CCs to lists of diagnosis codes that map to them
    """
    cc_to_dx: Dict[str, Set[str]] = {}
    
    for dx in set(diagnoses):
        dx = dx.upper().replace('.', '')
        ccs = get_cc(dx, model_name, dx_to_cc)
        if ccs is not None:
            for cc in ccs:
                if cc not in cc_to_dx:
                    cc_to_dx[cc] = set()
                cc_to_dx[cc].add(dx)
                
    return cc_to_dx
