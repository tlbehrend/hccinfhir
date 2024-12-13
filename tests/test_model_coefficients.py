import pytest
from hccinfhir.model_coefficients import get_coefficent_prefix, apply_coefficients
from hccinfhir.model_demographics import categorize_demographics

def test_get_coefficient_prefix_cms_hcc_community():
    demographics = categorize_demographics(
        age=70,
        sex='F',
        dual_elgbl_cd='00',
        orec='0',
        crec='0',
        version='V2',
        new_enrollee=False,
        snp=False,
        low_income=False
    )
    
    prefix = get_coefficent_prefix(demographics)
    assert prefix == "CNA_"

def test_get_coefficient_prefix_esrd_dialysis():
    demographics = categorize_demographics(
        age=45,
        sex='M',
        dual_elgbl_cd='00',
        orec='2',
        version='V2',
        new_enrollee=False,
        snp=False,
        low_income=False
    )
    
    prefix = get_coefficent_prefix(demographics, model_name="CMS-HCC ESRD Model V24")
    assert prefix == "DI_"

def test_apply_coefficients():
    demographics = categorize_demographics(
        age=70,
        sex='F',
        dual_elgbl_cd='00',
        orec='0',
        crec='0',
        version='V2',
        new_enrollee=False,
        snp=False,
        low_income=False
    )
    
    hcc_set = {"19", "47", "85"}
    interactions = {
        "D1": 1,
        "D2": 0,  # Should be excluded from result
    }
    
    # Create test coefficients
    test_coefficients = {
        ("cna_hcc19", "CMS-HCC Model V28"): 0.421,
        ("cna_hcc47", "CMS-HCC Model V28"): 0.368,
        ("cna_hcc85", "CMS-HCC Model V28"): 0.323,
        ("cna_d1", "CMS-HCC Model V28"): 0.118,
        ("cna_d2", "CMS-HCC Model V28"): 0.245,
    }
    
    result = apply_coefficients(
        demographics=demographics,
        hcc_set=hcc_set,
        interactions=interactions,
        coefficients=test_coefficients
    )

    expected = {
        "19": 0.421,
        "47": 0.368,
        "85": 0.323,
        "D1": 0.118
    }
    
    assert result == expected

def test_apply_coefficients_empty():
    demographics = categorize_demographics(
        age=70,
        sex='F',
        dual_elgbl_cd='00',
        orec='0',
        crec='0',
        version='V2',
        new_enrollee=False,
        snp=False,
        low_income=False
    )
    
    result = apply_coefficients(
        demographics=demographics,
        hcc_set=set(),
        interactions={},
    )
    
    assert result == {'F70_74': 0.395}
