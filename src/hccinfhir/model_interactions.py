from hccinfhir.datamodels import Demographics, ModelName
from typing import Optional

def has_any_hcc(hcc_list: list[str], hcc_set: set[str]) -> int:
    """Returns 1 if any HCC in the list is present, 0 otherwise"""
    return int(bool(set(hcc_list) & hcc_set))

def create_demographic_interactions(demographics: Demographics) -> dict:
    """Creates common demographic-based interactions"""
    interactions = {}
    is_female = demographics.category.startswith('F')
    is_male = demographics.category.startswith('M')
    is_aged = not demographics.non_aged
    
    # Original Disability interactions
    if is_aged:
        interactions['OriginallyDisabled_Female'] = int(demographics.orig_disabled) * int(is_female)
        interactions['OriginallyDisabled_Male'] = int(demographics.orig_disabled) * int(is_male)
    else:
        interactions['OriginallyDisabled_Female'] = 0
        interactions['OriginallyDisabled_Male'] = 0

    # LTI interactions - used for ESRD models
    if demographics.lti:
        interactions['LTI_Aged'] = int(is_aged)
        interactions['LTI_NonAged'] = int(not is_aged)
    else:
        interactions['LTI_Aged'] = 0
        interactions['LTI_NonAged'] = 0
        
    nemcaid = False
    if demographics.new_enrollee and demographics.dual_elgbl_cd in {'01', '02', '03', '04', '05', '06', '08'}:
        nemcaid = True
    ne_origds = int(demographics.age >= 65 and (demographics.orec is not None and demographics.orec == "1"))
    
    # Four mutually exclusive groups
    interactions.update({
        f'NMCAID_NORIGDIS_{demographics.category}': int(not nemcaid and not ne_origds),
        f'MCAID_NORIGDIS_{demographics.category}': int(nemcaid and not ne_origds),
        f'NMCAID_ORIGDIS_{demographics.category}': int(not nemcaid and ne_origds),
        f'MCAID_ORIGDIS_{demographics.category}': int(nemcaid and ne_origds)
    })

    return interactions

def create_dual_interactions(demographics: Demographics) -> dict:
    """Creates dual status interactions"""
    interactions = {}
    ## TB 8/8/25: i commented out the 2 lines below because they fail with new enrollees
    ##  new_enrollees demographics.category are start with NEF, NEM
    # is_female = demographics.category.startswith('F')
    # is_male = demographics.category.startswith('M')
    is_female = demographics.sex == '2'
    is_male = not is_female

    is_aged = not demographics.non_aged

    
    if demographics.fbd:
        interactions.update({
            'FBDual_Female_Aged': int(is_female) * int(is_aged),
            'FBDual_Female_NonAged': int(is_female) * int(not is_aged),
            'FBDual_Male_Aged': int(is_male) * int(is_aged),
            'FBDual_Male_NonAged': int(is_male) * int(not is_aged),
            ## TB 8/8/2025: added 2 lines below to handle ESRD Model V24 new enrollees
            f'FBD_NORIGDIS_{demographics.category}': int(demographics.fbd) * int(not demographics.orig_disabled),
            f'FBD_ORIGDIS_{demographics.category}': int(demographics.fbd) * int(demographics.orig_disabled)
        })
    
    if demographics.pbd:
        interactions.update({
            'PBDual_Female_Aged': int(is_female) * int(is_aged),
            'PBDual_Female_NonAged': int(is_female) * int(not is_aged),
            'PBDual_Male_Aged': int(is_male) * int(is_aged),
            'PBDual_Male_NonAged': int(is_male) * int(not is_aged),
            ## TB 8/8/2025: added 2 lines below to handle ESRD Model V24 new enrollees
            f'ND_PBD_NORIGDIS_{demographics.category}': int(not demographics.fbd) * int(not demographics.orig_disabled),
            f'ND_PBD_ORIGDIS_{demographics.category}': int(not demographics.fbd) * int(demographics.orig_disabled)
        })
        
    return interactions

def create_hcc_counts(hcc_set: set[str]) -> dict:
    """Creates HCC count variables"""
    counts = {}
    hcc_count = len(hcc_set)
    
    for i in range(1, 10):
        counts[f'D{i}'] = int(hcc_count == i)
    counts['D10P'] = int(hcc_count >= 10)
    
    return counts

def get_diagnostic_categories(model_name: ModelName, hcc_set: set[str]) -> dict:
    """Creates disease categories based on model version"""
    if model_name == "CMS-HCC Model V28":
        return {
            'CANCER_V28': has_any_hcc(['17', '18', '19', '20', '21', '22', '23'], hcc_set),
            'DIABETES_V28': has_any_hcc(['35', '36', '37', '38'], hcc_set),
            'CARD_RESP_FAIL_V28': has_any_hcc(['211', '212', '213'], hcc_set),
            'HF_V28': has_any_hcc(['221', '222', '223', '224', '225', '226'], hcc_set),
            'CHR_LUNG_V28': has_any_hcc(['276', '277', '278', '279', '280'], hcc_set),
            'KIDNEY_V28': has_any_hcc(['326', '327', '328', '329'], hcc_set),
            'SEPSIS_V28': int('2' in hcc_set),
            'gSubUseDisorder_V28': has_any_hcc(['135', '136', '137', '138', '139'], hcc_set),
            'gPsychiatric_V28': has_any_hcc(['151', '152', '153', '154', '155'], hcc_set),
            'NEURO_V28': has_any_hcc(['180', '181', '182', '190', '191', '192', '195', '196', '198', '199'], hcc_set),
            'ULCER_V28': has_any_hcc(['379', '380', '381', '382'], hcc_set)
        }
    elif model_name == "CMS-HCC Model V24":
        return {
            'CANCER': has_any_hcc(['8', '9', '10', '11', '12'], hcc_set),
            'DIABETES': has_any_hcc(['17', '18', '19'], hcc_set),
            'CARD_RESP_FAIL': has_any_hcc(['82', '83', '84'], hcc_set),
            'CHF': int('85' in hcc_set),
            'gCopdCF': has_any_hcc(['110', '111', '112'], hcc_set),
            'RENAL_V24': has_any_hcc(['134', '135', '136', '137', '138'], hcc_set), 
            'SEPSIS': int('2' in hcc_set),
            'gSubstanceUseDisorder_V24': has_any_hcc(['54', '55', '56'], hcc_set),
            'gPsychiatric_V24': has_any_hcc(['57', '58', '59', '60'], hcc_set),
            'PRESSURE_ULCER': has_any_hcc(['157', '158', '159'],  hcc_set) # added in 2018-11-20
        }
    elif model_name == "CMS-HCC Model V22":
        return {
            'CANCER': has_any_hcc(['8', '9', '10', '11', '12'], hcc_set),
            'DIABETES': has_any_hcc(['17', '18', '19'], hcc_set),
            'CARD_RESP_FAIL': has_any_hcc(['82', '83', '84'], hcc_set),
            'CHF': int('85' in hcc_set),
            'gCopdCF': has_any_hcc(['110', '111', '112'], hcc_set),
            'RENAL': has_any_hcc(['134', '135', '136', '137'], hcc_set), 
            'SEPSIS': int('2' in hcc_set),
            'gSubstanceUseDisorder': has_any_hcc(['54', '55'], hcc_set),
            'gPsychiatric': has_any_hcc(['57', '58'], hcc_set),
            'PRESSURE_ULCER': has_any_hcc(['157', '158'],  hcc_set) # added in 2012-10-19
        }
    elif model_name == "CMS-HCC ESRD Model V24":
        return {
            'CANCER': has_any_hcc(['8', '9', '10', '11', '12'], hcc_set),
            'DIABETES': has_any_hcc(['17', '18', '19'], hcc_set),
            'CARD_RESP_FAIL': has_any_hcc(['82', '83', '84'], hcc_set),
            'CHF': int('85' in hcc_set),            
            'gCopdCF': has_any_hcc(['110', '111', '112'], hcc_set),
            'RENAL_V24': has_any_hcc(['134', '135', '136', '137', '138'], hcc_set),
            'SEPSIS': int('2' in hcc_set),
            'PRESSURE_ULCER': has_any_hcc(['157', '158', '159', '160'], hcc_set), # added in 2018-11-20
            'gSubstanceUseDisorder_V24': has_any_hcc(['54', '55', '56'], hcc_set),
            'gPsychiatric_V24': has_any_hcc(['57', '58', '59', '60'], hcc_set)
        }
    elif model_name == "CMS-HCC ESRD Model V21":
        return {
            'CANCER': has_any_hcc(['8', '9', '10', '11', '12'], hcc_set),
            'DIABETES': has_any_hcc(['17', '18', '19'], hcc_set),
            'IMMUNE': int('47' in hcc_set),
            'CARD_RESP_FAIL': has_any_hcc(['82', '83', '84'], hcc_set),
            'CHF': int('85' in hcc_set),
            'COPD': has_any_hcc(['110', '111'], hcc_set),
            'RENAL': has_any_hcc(['134', '135', '136', '137', '138', '139', '140', '141'], hcc_set),
            'COMPL': int('176' in hcc_set),
            'SEPSIS': int('2' in hcc_set), 
            'PRESSURE_ULCER': has_any_hcc(['157', '158', '159', '160'], hcc_set)
        }
    elif model_name == "RxHCC Model V08":
        # RxModel doesn't seem to have any diagnostic category interactions
        return {}
    return {}

def create_disease_interactions(model_name: ModelName, 
                              diagnostic_cats: dict, 
                              demographics: Optional[Demographics],
                              hcc_set: Optional[set[str]]) -> dict:
    """Creates disease interaction variables based on model version.
    
    Args:
        model_name: The HCC model version being used
        diagnostic_cats: Dictionary of diagnostic categories
        demographics: Optional demographic information for age/sex/disability interactions
        hcc_set: Optional set of HCCs for direct HCC checks
        
    Returns:
        Dictionary containing all disease interaction variables
    """
    interactions = {}
    
    if model_name == "CMS-HCC Model V28":
        # Base V28 disease interactions
        interactions.update({
            'DIABETES_HF_V28': diagnostic_cats['DIABETES_V28'] * diagnostic_cats['HF_V28'],
            'HF_CHR_LUNG_V28': diagnostic_cats['HF_V28'] * diagnostic_cats['CHR_LUNG_V28'],
            'HF_KIDNEY_V28': diagnostic_cats['HF_V28'] * diagnostic_cats['KIDNEY_V28'],
            'CHR_LUNG_CARD_RESP_FAIL_V28': diagnostic_cats['CHR_LUNG_V28'] * diagnostic_cats['CARD_RESP_FAIL_V28'],
            'gSubUseDisorder_gPsych_V28': diagnostic_cats['gSubUseDisorder_V28'] * diagnostic_cats['gPsychiatric_V28'],
            'DISABLED_CANCER_V28': demographics.disabled * diagnostic_cats['CANCER_V28'],
            'DISABLED_NEURO_V28': demographics.disabled * diagnostic_cats['NEURO_V28'],
            'DISABLED_HF_V28': demographics.disabled * diagnostic_cats['HF_V28'],
            'DISABLED_CHR_LUNG_V28': demographics.disabled * diagnostic_cats['CHR_LUNG_V28'],
            'DISABLED_ULCER_V28': demographics.disabled * diagnostic_cats['ULCER_V28']
        })
            
    elif model_name == "CMS-HCC Model V24":
        # Base V24/V22 disease interactions
        interactions.update({
            'HCC47_gCancer': int('47' in hcc_set) * diagnostic_cats['CANCER'],
            'DIABETES_CHF': diagnostic_cats['DIABETES'] * diagnostic_cats['CHF'],
            'CHF_gCopdCF': diagnostic_cats['CHF'] * diagnostic_cats['gCopdCF'],
            'HCC85_gRenal_V24': diagnostic_cats['CHF'] * diagnostic_cats['RENAL_V24'],
            'gCopdCF_CARD_RESP_FAIL': diagnostic_cats['gCopdCF'] * diagnostic_cats['CARD_RESP_FAIL'],
            'HCC85_HCC96': int('85' in hcc_set) * int('96' in hcc_set),
            'gSubstanceAbuse_gPsych': diagnostic_cats['gSubstanceUseDisorder_V24'] * diagnostic_cats['gPsychiatric_V24'],
            'SEPSIS_PRESSURE_ULCER': diagnostic_cats['SEPSIS'] * diagnostic_cats['PRESSURE_ULCER'],
            'SEPSIS_ARTIF_OPENINGS': diagnostic_cats['SEPSIS'] * int('188' in hcc_set),
            'ART_OPENINGS_PRESS_ULCER': int('188' in hcc_set) * diagnostic_cats['PRESSURE_ULCER'],
            'gCopdCF_ASP_SPEC_B_PNEUM': diagnostic_cats['gCopdCF'] * int('114' in hcc_set),
            'ASP_SPEC_B_PNEUM_PRES_ULC': int('114' in hcc_set) * diagnostic_cats['PRESSURE_ULCER'],
            'SEPSIS_ASP_SPEC_BACT_PNEUM': diagnostic_cats['SEPSIS'] * int('114' in hcc_set),
            'SCHIZOPHRENIA_gCopdCF': int('57' in hcc_set) * diagnostic_cats['gCopdCF'],
            'SCHIZOPHRENIA_CHF': int('57' in hcc_set) * diagnostic_cats['CHF'],
            'SCHIZOPHRENIA_SEIZURES': int('57' in hcc_set) * int('79' in hcc_set),
            'DISABLED_HCC85': demographics.disabled * int('85' in hcc_set),
            'DISABLED_PRESSURE_ULCER': demographics.disabled * diagnostic_cats['PRESSURE_ULCER'],
            'DISABLED_HCC161': demographics.disabled * int('161' in hcc_set),
            'DISABLED_HCC39': demographics.disabled * int('39' in hcc_set),
            'DISABLED_HCC77': demographics.disabled * int('77' in hcc_set),
            'DISABLED_HCC6': demographics.disabled * int('6' in hcc_set)
        })
    elif model_name == "CMS-HCC Model V22":
        # Base V24/V22 disease interactions
        interactions.update({
            'HCC47_gCancer': int('47' in hcc_set) * diagnostic_cats['CANCER'],
            'HCC85_gDiabetesMellitus': int('85' in hcc_set) * diagnostic_cats['DIABETES'],
            'HCC85_gCopdCF': int('85' in hcc_set) * diagnostic_cats['gCopdCF'],
            'HCC85_gRenal': int('85' in hcc_set) * diagnostic_cats['RENAL'],
            'gRespDepandArre_gCopdCF': diagnostic_cats['CARD_RESP_FAIL'] * diagnostic_cats['gCopdCF'],
            'HCC85_HCC96': int('85' in hcc_set) * int('96' in hcc_set),
            'gSubstanceAbuse_gPsychiatric': diagnostic_cats['gSubstanceUseDisorder'] * diagnostic_cats['gPsychiatric'],
            'DIABETES_CHF': diagnostic_cats['DIABETES'] * diagnostic_cats['CHF'],
            'CHF_gCopdCF': diagnostic_cats['CHF'] * diagnostic_cats['gCopdCF'],
            'gCopdCF_CARD_RESP_FAIL': diagnostic_cats['gCopdCF'] * diagnostic_cats['CARD_RESP_FAIL'],
            'SEPSIS_PRESSURE_ULCER': diagnostic_cats['SEPSIS'] * diagnostic_cats['PRESSURE_ULCER'],
            'SEPSIS_ARTIF_OPENINGS': diagnostic_cats['SEPSIS'] * int('188' in hcc_set),
            'ART_OPENINGS_PRESSURE_ULCER': int('188' in hcc_set) * diagnostic_cats['PRESSURE_ULCER'],
            'DIABETES_CHF': diagnostic_cats['DIABETES'] * diagnostic_cats['CHF'],
            'gCopdCF_ASP_SPEC_BACT_PNEUM': diagnostic_cats['gCopdCF'] * int('114' in hcc_set),
            'ASP_SPEC_BACT_PNEUM_PRES_ULC': int('114' in hcc_set) * diagnostic_cats['PRESSURE_ULCER'],
            'SEPSIS_ASP_SPEC_BACT_PNEUM': diagnostic_cats['SEPSIS'] * int('114' in hcc_set),
            'SCHIZOPHRENIA_gCopdCF': int('57' in hcc_set) * diagnostic_cats['gCopdCF'],
            'SCHIZOPHRENIA_CHF': int('57' in hcc_set) * diagnostic_cats['CHF'],
            'SCHIZOPHRENIA_SEIZURES': int('57' in hcc_set) * int('79' in hcc_set),
            'DISABLED_HCC85': demographics.disabled * int('85' in hcc_set),
            'DISABLED_PRESSURE_ULCER': demographics.disabled * diagnostic_cats['PRESSURE_ULCER'],
            'DISABLED_HCC161': demographics.disabled * int('161' in hcc_set),
            'DISABLED_HCC39': demographics.disabled * int('39' in hcc_set),
            'DISABLED_HCC77': demographics.disabled * int('77' in hcc_set),
            'DISABLED_HCC6': demographics.disabled * int('6' in hcc_set)
        })
    elif model_name == "CMS-HCC ESRD Model V24":
        # Base ESRD V24 disease interactions
        interactions.update({
            'HCC47_gCancer': int('47' in hcc_set) * diagnostic_cats['CANCER'],
            'DIABETES_CHF': diagnostic_cats['DIABETES'] * diagnostic_cats['CHF'],
            'CHF_gCopdCF': diagnostic_cats['CHF'] * diagnostic_cats['gCopdCF'],
            'HCC85_gRenal_V24': int('85' in hcc_set) * diagnostic_cats['RENAL_V24'],
            'gCopdCF_CARD_RESP_FAIL': diagnostic_cats['gCopdCF'] * diagnostic_cats['CARD_RESP_FAIL'],
            'HCC85_HCC96': int('85' in hcc_set) * int('96' in hcc_set),
            'gSubUseDs_gPsych_V24': diagnostic_cats['gSubstanceUseDisorder_V24'] * diagnostic_cats['gPsychiatric_V24'],
            'NONAGED_gSubUseDs_gPsych': demographics.non_aged * (diagnostic_cats['gSubstanceUseDisorder_V24'] * diagnostic_cats['gPsychiatric_V24']),
            'NONAGED_HCC6': demographics.non_aged * int('6' in hcc_set),
            'NONAGED_HCC34': demographics.non_aged * int('34' in hcc_set),
            'NONAGED_HCC46': demographics.non_aged * int('46' in hcc_set),
            'NONAGED_HCC110': demographics.non_aged * int('110' in hcc_set),
            'NONAGED_HCC176': demographics.non_aged * int('176' in hcc_set),
            'SEPSIS_PRESSURE_ULCER_V24': diagnostic_cats['SEPSIS'] * diagnostic_cats['PRESSURE_ULCER'],
            'SEPSIS_ARTIF_OPENINGS': diagnostic_cats['SEPSIS'] * int('188' in hcc_set),
            'ART_OPENINGS_PRESS_ULCER_V24': int('188' in hcc_set) * diagnostic_cats['PRESSURE_ULCER'],
            'gCopdCF_ASP_SPEC_B_PNEUM': diagnostic_cats['gCopdCF'] * int('114' in hcc_set),
            'ASP_SPEC_B_PNEUM_PRES_ULC_V24': int('114' in hcc_set) * diagnostic_cats['PRESSURE_ULCER'],
            'SEPSIS_ASP_SPEC_BACT_PNEUM': diagnostic_cats['SEPSIS'] * int('114' in hcc_set),
            'SCHIZOPHRENIA_gCopdCF': int('57' in hcc_set) * diagnostic_cats['gCopdCF'],
            'SCHIZOPHRENIA_CHF': int('57' in hcc_set) * diagnostic_cats['CHF'],
            'SCHIZOPHRENIA_SEIZURES': int('57' in hcc_set) * int('79' in hcc_set),
            'NONAGED_HCC85': demographics.non_aged * int('85' in hcc_set),
            'NONAGED_PRESSURE_ULCER_V24': demographics.non_aged * diagnostic_cats['PRESSURE_ULCER'],
            'NONAGED_HCC161': demographics.non_aged * int('161' in hcc_set),
            'NONAGED_HCC39': demographics.non_aged * int('39' in hcc_set),
            'NONAGED_HCC77': demographics.non_aged * int('77' in hcc_set)
        })
    
    elif model_name == 'CMS-HCC ESRD Model V21':
        # ESRD Community model interactions
        interactions.update({
            'SEPSIS_CARD_RESP_FAIL': diagnostic_cats['SEPSIS'] * diagnostic_cats['CARD_RESP_FAIL'],
            'CANCER_IMMUNE': diagnostic_cats['CANCER'] * diagnostic_cats['IMMUNE'],
            'DIABETES_CHF': diagnostic_cats['DIABETES'] * diagnostic_cats['CHF'],
            'CHF_COPD': diagnostic_cats['CHF'] * diagnostic_cats['COPD'],
            'CHF_RENAL': diagnostic_cats['CHF'] * diagnostic_cats['RENAL'],
            'COPD_CARD_RESP_FAIL': diagnostic_cats['COPD'] * diagnostic_cats['CARD_RESP_FAIL'],
            'NONAGED_HCC6': demographics.non_aged * int('6' in hcc_set),
            'NONAGED_HCC34': demographics.non_aged * int('34' in hcc_set),
            'NONAGED_HCC46': demographics.non_aged * int('46' in hcc_set),
            'NONAGED_HCC54': demographics.non_aged * int('54' in hcc_set),
            'NONAGED_HCC55': demographics.non_aged * int('55' in hcc_set),
            'NONAGED_HCC110': demographics.non_aged * int('110' in hcc_set),
            'NONAGED_HCC176': demographics.non_aged * int('176' in hcc_set),
            'SEPSIS_PRESSURE_ULCER': diagnostic_cats['SEPSIS'] * diagnostic_cats['PRESSURE_ULCER'],
            'SEPSIS_ARTIF_OPENINGS': diagnostic_cats['SEPSIS'] * int('188' in hcc_set),
            'ART_OPENINGS_PRESSURE_ULCER': int('188' in hcc_set) * diagnostic_cats['PRESSURE_ULCER'],
            'DIABETES_CHF': diagnostic_cats['DIABETES'] * diagnostic_cats['CHF'],
            'COPD_ASP_SPEC_BACT_PNEUM': diagnostic_cats['COPD'] * int('114' in hcc_set),
            'ASP_SPEC_BACT_PNEUM_PRES_ULC': int('114' in hcc_set) * diagnostic_cats['PRESSURE_ULCER'],
            'SEPSIS_ASP_SPEC_BACT_PNEUM': diagnostic_cats['SEPSIS'] * int('114' in hcc_set),
            'SCHIZOPHRENIA_COPD': int('57' in hcc_set) * diagnostic_cats['COPD'],
            'SCHIZOPHRENIA_CHF': int('57' in hcc_set) * diagnostic_cats['CHF'],
            'SCHIZOPHRENIA_SEIZURES': int('57' in hcc_set) * int('79' in hcc_set),
            'NONAGED_HCC85': demographics.non_aged * int('85' in hcc_set),
            'NONAGED_PRESSURE_ULCER': demographics.non_aged * diagnostic_cats['PRESSURE_ULCER'],
            'NONAGED_HCC161': demographics.non_aged * int('161' in hcc_set),
            'NONAGED_HCC39': demographics.non_aged * int('39' in hcc_set),
            'NONAGED_HCC77': demographics.non_aged * int('77' in hcc_set)
        })
            
    elif model_name == "RxHCC Model V08":
        # RxHCC NonAged interactions
        interactions.update({
            'NonAged_RXHCC1': demographics.non_aged * int('1' in hcc_set),
            'NonAged_RXHCC130': demographics.non_aged * int('130' in hcc_set),
            'NonAged_RXHCC131': demographics.non_aged * int('131' in hcc_set),
            'NonAged_RXHCC132': demographics.non_aged * int('132' in hcc_set),
            'NonAged_RXHCC133': demographics.non_aged * int('133' in hcc_set),
            'NonAged_RXHCC159': demographics.non_aged * int('159' in hcc_set),
            'NonAged_RXHCC163': demographics.non_aged * int('163' in hcc_set)
        })
    
    return interactions

def apply_interactions(demographics: Demographics, 
                      hcc_set: set[str], 
                      model_name: ModelName = "CMS-HCC Model V28") -> dict:
    """
    Calculate HCC interactions across CMS models. Handles CMS-HCC, ESRD, and RxHCC models.
    """
    # Start with demographic interactions
    interactions = create_demographic_interactions(demographics)
    
    # Add dual status interactions
    interactions.update(create_dual_interactions(demographics))
    
    # Get diagnostic categories for the model
    diagnostic_cats = get_diagnostic_categories(model_name, hcc_set)
    
    interactions.update(create_disease_interactions(model_name, diagnostic_cats, demographics, hcc_set))
        
    # Add HCC counts
    interactions.update(create_hcc_counts(hcc_set))
    
    return interactions