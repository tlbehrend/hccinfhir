from typing import List, Union
from hccinfhir.datamodels import ModelName
from hccinfhir.model_demographics import categorize_demographics
from hccinfhir.model_dx_to_cc import apply_mapping
from hccinfhir.model_hierarchies import apply_hierarchies
from hccinfhir.model_coefficients import apply_coefficients
from hccinfhir.model_interactions import apply_interactions

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
                  graft_months: int = None):

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
                                           new_enrollee, 
                                           snp, 
                                           low_income, 
                                           graft_months)
    
    cc_to_dx = apply_mapping(diagnosis_codes, model_name)
    hcc_set = set(cc_to_dx.keys())
    hcc_set = apply_hierarchies(hcc_set, model_name)
    interactions = apply_interactions(demographics, hcc_set, model_name)
    coefficients = apply_coefficients(demographics, hcc_set, interactions, model_name)
    
    raf = sum(coefficients.values())


    return {'raf': raf, 'coefficients': coefficients}



