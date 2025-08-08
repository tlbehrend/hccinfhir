from typing import List, Union, Dict, Tuple, Set
from hccinfhir.datamodels import ModelName, RAFResult
from hccinfhir.model_demographics import categorize_demographics
from hccinfhir.model_dx_to_cc import apply_mapping
from hccinfhir.model_hierarchies import apply_hierarchies
from hccinfhir.model_coefficients import apply_coefficients
from hccinfhir.model_interactions import apply_interactions
from hccinfhir.utils import load_dx_to_cc_mapping, load_is_chronic

# Load default mappings from csv file
mapping_file_default = 'ra_dx_to_cc_2026.csv'
dx_to_cc_default = load_dx_to_cc_mapping(mapping_file_default)

# Load default mappings from csv file
mapping_file_default = 'hcc_is_chronic.csv'
is_chronic_default = load_is_chronic(mapping_file_default)

def calculate_raf(diagnosis_codes: List[str],
                  model_name: ModelName = "CMS-HCC Model V28",
                  age: Union[int, float] = 65, 
                  sex: str = 'F', 
                  dual_elgbl_cd: str = 'NA',
                  orec: str = '0', 
                  crec: str = '0',
                  new_enrollee: bool = False,   
                  snp: bool = False,
                  low_income: bool = False,
                  graft_months: int =  None,
                  dx_to_cc_mapping: Dict[Tuple[str, ModelName], Set[str]] = dx_to_cc_default,
                  is_chronic_mapping: Dict[Tuple[str, ModelName], bool] = is_chronic_default) -> RAFResult:
    """
    Calculate Risk Adjustment Factor (RAF) based on diagnosis codes and demographic information.

    Args:
        diagnosis_codes: List of ICD-10 diagnosis codes
        model_name: Name of the HCC model to use
        age: Patient's age
        sex: Patient's sex ('M' or 'F')
        dual_elgbl_cd: Dual eligibility code
        orec: Original reason for entitlement code
        crec: Current reason for entitlement code
        new_enrollee: Whether the patient is a new enrollee
        snp: Special Needs Plan indicator
        low_income: Low income subsidy indicator
        graft_months: Number of months since transplant

    Returns:
        Dictionary containing RAF score and coefficients used in calculation

    Raises:
        ValueError: If input parameters are invalid
    """
    # Input validation
    if not isinstance(age, (int, float)) or age < 0:
        raise ValueError("Age must be a non-negative number")
    
    if sex not in ['M', 'F', '1', '2']:
        raise ValueError("Sex must be 'M' or 'F' or '1' or '2'")

    version = 'V2'
    if 'RxHCC' in model_name:
        version = 'V4'
    elif 'HHS-HCC' in model_name: # not implemented yet
        version = 'V6'
    
    demographics = categorize_demographics(age, 
                                           sex, 
                                           dual_elgbl_cd, 
                                           orec, 
                                           crec, 
                                           version,
                                           model_name,      ## TB added 8/8/2025 to distinguish different age groups for Dialysis model (DNE and DI differ from V28)
                                           new_enrollee, 
                                           snp, 
                                           low_income, 
                                           graft_months)
    
    cc_to_dx = apply_mapping(diagnosis_codes, 
                             model_name, 
                             dx_to_cc_mapping=dx_to_cc_mapping)
    hcc_set = set(cc_to_dx.keys())
    hcc_set = apply_hierarchies(hcc_set, model_name)
    interactions = apply_interactions(demographics, hcc_set, model_name)
    coefficients = apply_coefficients(demographics, hcc_set, interactions, model_name)

    hcc_chronic = set()
    for hcc in hcc_set:
        if is_chronic_mapping.get((hcc, model_name), False):
            hcc_chronic.add(hcc)

    demographic_interactions = {}
    for key, value in interactions.items():
        if key.startswith('NMCAID_'):
            demographic_interactions[key] = value
        elif key.startswith('MCAID_'):
            demographic_interactions[key] = value
        elif key.startswith('LTI_'):
            demographic_interactions[key] = value
        elif key.startswith('OriginallyDisabled_'):
            demographic_interactions[key] = value

    coefficients_demographics = apply_coefficients(demographics, 
                                                   set(), 
                                                   demographic_interactions, 
                                                   model_name)
    coefficients_chronic_only = apply_coefficients(demographics, 
                                                   hcc_chronic, 
                                                   demographic_interactions, 
                                                   model_name)
    
    # Calculate risk scores
    risk_score = sum(coefficients.values())
    risk_score_demographics = sum(coefficients_demographics.values())
    risk_score_chronic_only = sum(coefficients_chronic_only.values()) - risk_score_demographics
    risk_score_hcc = risk_score - risk_score_demographics

    return {
        'risk_score': risk_score, 
        'risk_score_demographics': risk_score_demographics,
        'risk_score_chronic_only': risk_score_chronic_only,
        'risk_score_hcc': risk_score_hcc,
        'hcc_list': list(hcc_set),
        'cc_to_dx': cc_to_dx,
        'coefficients': coefficients,
        'interactions': interactions,
        'demographics': demographics,
        'model_name': model_name,
        'version': version,
        'diagnosis_codes': diagnosis_codes,
    }



