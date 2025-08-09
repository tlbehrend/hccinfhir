from typing import Dict, Tuple
import importlib.resources
from hccinfhir.datamodels import ModelName, Demographics

# Load default mappings from csv file
coefficients_file_default = 'ra_coefficients_2026.csv'
coefficients_default: Dict[Tuple[str, ModelName], float] = {}  # (diagnosis_code, model_name) -> value

try:
    with importlib.resources.open_text('hccinfhir.data', coefficients_file_default) as f:
        for line in f.readlines()[1:]:  # Skip header
            try:
                coefficient, value, model_domain, model_version = line.strip().split(',')
                if model_domain == 'ESRD':  
                    model_name = f"CMS-HCC {model_domain} Model V{model_version[-2:]}"
                else:
                    model_name = f"{model_domain} Model V{model_version[-2:]}"
                
                key = (coefficient.lower(), model_name)
                if key not in coefficients_default:
                    coefficients_default[key] = float(value)
                else:
                    coefficients_default[key] = float(value)
            except ValueError:
                continue  # Skip malformed lines
except Exception as e:
    print(f"Error loading mapping file: {e}")
    coefficients_default = {}

def get_coefficent_prefix(demographics: Demographics, 
                          model_name: ModelName = "CMS-HCC Model V28") -> str:

    """
    Get the coefficient prefix based on beneficiary demographics.
    
    Args:
        demographics: Demographics object containing beneficiary information
        
    Returns:
        String prefix used to look up coefficients for this beneficiary type
    """
    # Get base prefix based on model type
    if 'ESRD' in model_name:
        # if demographics.esrd:
        #     if demographics.graft_months is not None:
        #         # Functioning graft case
        #         if demographics.lti:
        #             return 'GI_'
        #         if demographics.new_enrollee:
        #             return 'GNE_'
                    
        #         # Community functioning graft
        #         prefix = 'G'
        #         prefix += 'F' if demographics.fbd else 'NP'
        #         prefix += 'A' if demographics.age >= 65 else 'N'
        #         return prefix + '_'
                
        #     # Dialysis case
        #     return 'DNE_' if demographics.new_enrollee else 'DI_'
            
        # Transplant case
        if demographics.graft_months in [1, 2, 3]:
            return f'TRANSPLANT_KIDNEY_ONLY_{demographics.graft_months}M'

        ## TB 8/9/2025: replace above code block with belo for ESRD model
        ##  - skip the if demographics.esrd statement, as we have plenty of esrd patients who have both orec and crec = 0
        ##      - logic from model_demographics.categorize_demographics at line 84 (not sure how we could change that logic to be correct, not sure it's even needed)
        ##  - I don't think the transplant logic is correct, but we don't use that so I haven't tried to address
                
        # Dialysis case
        return 'DNE_' if demographics.new_enrollee else 'DI_'
            
    elif 'RxHCC' in model_name:
        if demographics.lti:
            return 'Rx_NE_LTI_' if demographics.new_enrollee else 'Rx_CE_LTI_'
            
        if demographics.new_enrollee:
            return 'Rx_NE_Lo_' if demographics.low_income else 'Rx_NE_NoLo_'
            
        # Community case
        prefix = 'Rx_CE_'
        prefix += 'Low' if demographics.low_income else 'NoLow'
        prefix += 'Aged' if demographics.age >= 65 else 'NoAged'
        return prefix + '_'
        
    # Default CMS-HCC Model
    if demographics.lti:
        return 'INS_'
        
    if demographics.new_enrollee:

        return 'SNPNE_' if demographics.snp else 'NE_'
        
    # Community case
    prefix = 'C'
    prefix += 'F' if demographics.fbd else ('P' if demographics.pbd else 'N')
    prefix += 'A' if demographics.age >= 65 else 'D'
    return prefix + '_'


def apply_coefficients(demographics: Demographics, 
                      hcc_set: set[str], 
                      interactions: dict,
                      model_name: ModelName = "CMS-HCC Model V28",
                      coefficients: Dict[Tuple[str, ModelName], float] = coefficients_default) -> dict:
    """Apply risk adjustment coefficients to HCCs and interactions.

    This function takes demographic information, HCC codes, and interaction variables and returns
    a dictionary mapping each variable to its corresponding coefficient value based on the 
    specified model.

    Args:
        demographics: Demographics object containing patient characteristics
        hcc_set: Set of HCC codes present for the patient
        interactions: Dictionary of interaction variables and their values (0 or 1)
        model_name: Name of the risk adjustment model to use (default: "CMS-HCC Model V28")
        coefficients: Dictionary mapping (variable, model) tuples to coefficient values
            (default: coefficients_default)

    Returns:
        Dictionary mapping HCC codes and interaction variables to their coefficient values
        for variables that are present (HCC in hcc_set or interaction value = 1)
    """
    # Get the coefficient prefix
    prefix = get_coefficent_prefix(demographics, model_name)
    
    output = {}

    demographics_key = (f"{prefix}{demographics.category}".lower(), model_name)
    if demographics_key in coefficients:
        output[demographics.category] = coefficients[demographics_key]

    # Apply the coefficients
    for hcc in hcc_set:
        key = (f"{prefix}HCC{hcc}".lower(), model_name)

        if key in coefficients:
            value = coefficients[key]
            output[hcc] = value

    # Add interactions
    for interaction_key, interaction_value in interactions.items():
        if interaction_value < 1:
            continue

        key = (f"{prefix}{interaction_key}".lower(), model_name)
        if key in coefficients:
            value = coefficients[key]
            output[interaction_key] = value


    return output

