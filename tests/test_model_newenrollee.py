# tests/test_model_interactions.py

import pytest
from hccinfhir.model_calculate import calculate_raf
from hccinfhir.model_demographics import categorize_demographics
from pprint import pprint

def test_new_enrollee_calculation():
    diagnosis_codes = ['E119', 'I509']  # Diabetes without complications, Heart failure
    result = calculate_raf(
        diagnosis_codes=diagnosis_codes,
        model_name="CMS-HCC Model V24",
        age=67,
        sex='F', 
        new_enrollee=True
    )

    assert result['risk_score_demographics'] > 0

def test_disability_logic():
    """
    Test the disability logic according to SAS code:
    DISABL = (&AGEF < 65 & &OREC ne "0");
    ORIGDS  = (&OREC = '1')*(DISABL = 0);
    """
    
    # Test cases for different age and OREC combinations
    test_cases = [
        # (age, orec, expected_disabled, expected_orig_disabled, description)
        (64, '0', False, False, "Age 64, OREC 0 - not disabled, not originally disabled"),
        (64, '1', True, False, "Age 64, OREC 1 - disabled, not originally disabled"),
        (64, '2', True, False, "Age 64, OREC 2 - disabled, not originally disabled"),
        (65, '0', False, False, "Age 65, OREC 0 - not disabled, not originally disabled"),
        (65, '1', False, True, "Age 65, OREC 1 - not disabled, originally disabled"),
        (65, '2', False, False, "Age 65, OREC 2 - not disabled, not originally disabled"),
        (66, '0', False, False, "Age 66, OREC 0 - not disabled, not originally disabled"),
        (66, '1', False, True, "Age 66, OREC 1 - not disabled, originally disabled"),
        (66, '2', False, False, "Age 66, OREC 2 - not disabled, not originally disabled"),
    ]
    
    for age, orec, expected_disabled, expected_orig_disabled, description in test_cases:
        demographics = categorize_demographics(
            age=age,
            sex='F',
            orec=orec,
            version='V2'
        )
        
        #print(f"\nTesting: {description}")
        #print(f"Age: {age}, OREC: {orec}")
        #print(f"Expected disabled: {expected_disabled}, got: {demographics.disabled}")
        #print(f"Expected orig_disabled: {expected_orig_disabled}, got: {demographics.orig_disabled}")
        
        assert demographics.disabled == expected_disabled, f"Failed for {description}"
        assert demographics.orig_disabled == expected_orig_disabled, f"Failed for {description}"

if __name__ == "__main__":
    test_new_enrollee_calculation()
    test_disability_logic()
