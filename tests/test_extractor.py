import pytest
import importlib.resources
from hccinfhir.extractor import extract_mde, extract_mde_list
import json

def load_sample_eob(casenum=2):
   with importlib.resources.open_text('hccinfhir.data', 
                                      f'sample_eob_{casenum}.json') as f:
       return json.load(f)

def test_extract_mde_basic():

    eob_data = load_sample_eob(1)
    mde = extract_mde(eob_data)
    
    assert len(mde) == 2
    for mde_item in mde:
        assert mde_item["diagnosis_codes"] == ["F411"]
    
    eob_data = load_sample_eob(2)
    mde = extract_mde(eob_data)

    assert len(mde) == 1
    mde_item = mde[0]
    assert mde_item["procedure_code"] == "99213"
    assert mde_item["diagnosis_codes"] == ["E11.9"]
    assert mde_item["claim_type"] == "40"
    assert mde_item["provider_specialty"] == "01"
    assert mde_item["service_date"] == "2023-01-01"

    eob_data = load_sample_eob(3)
    mde = extract_mde(eob_data)
    assert len(mde) == 1
    for mde_item in mde:
        assert len(mde_item["diagnosis_codes"]) == 2
    

def test_extract_mde_missing_diagnosis_sequence():  
    eob_data = load_sample_eob()
    eob_data["item"][0].pop("diagnosisSequence")
    
    mde = extract_mde(eob_data)
    assert mde[0]["diagnosis_codes"] == []

def test_extract_mde_missing_serviced_period():
    eob_data = load_sample_eob()
    eob_data["item"][0].pop("servicedPeriod")
    
    mde = extract_mde(eob_data)
    assert mde[0]["service_date"] == "2023-01-01"  # Should fall back to billablePeriod

def test_extract_mde_invalid_data():
    with pytest.raises(ValueError):
        extract_mde({"resourceType": "Invalid"})

def test_extract_mde_non_hcpcs_item():
    eob_data = load_sample_eob()
    eob_data["item"][0]["productOrService"]["coding"][0]["system"] = "https://some-other-system.com"
    
    mde = extract_mde(eob_data)
    assert len(mde) == 0 

def test_extract_mde_list():
    eob_data_list = [load_sample_eob(1), load_sample_eob(2)]
    mde_list = extract_mde_list(eob_data_list)
    assert len(mde_list) == 3
