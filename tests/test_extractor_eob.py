import pytest
import importlib.resources
from hccinfhir.extractor import extract_sld, extract_sld_list
import json

def load_sample_eob(casenum=2):
   with importlib.resources.open_text('hccinfhir.samples', 
                                      f'sample_eob_{casenum}.json') as f:
       return json.load(f)

def load_sample_eob_list():
   output = []
   with importlib.resources.open_text('hccinfhir.samples', 
                                      f'sample_eob_200.ndjson') as f:
        for line in f:
            eob_data = json.loads(line)
            output.append(eob_data)
   return output

def test_extract_sld_basic():

    eob_data = load_sample_eob(1)
    sld = extract_sld(eob_data)
    
    assert len(sld) == 2
    for sld_item in sld:
        assert sld_item.linked_diagnosis_codes == ["F411"]
    
    eob_data = load_sample_eob(2)
    sld = extract_sld(eob_data)

    assert len(sld) == 1
    sld_item = sld[0]
    assert sld_item.procedure_code == "99213"
    assert sld_item.linked_diagnosis_codes == ["E11.9"]
    assert sld_item.claim_type == "40"
    assert sld_item.provider_specialty == "01"
    assert sld_item.service_date == "2023-01-01"
    assert sld_item.performing_provider_npi == "1234567890"
    eob_data = load_sample_eob(3)
    sld = extract_sld(eob_data)
    assert len(sld) == 1
    for sld_item in sld:
        assert len(sld_item.linked_diagnosis_codes) == 2
    

def test_extract_sld_missing_diagnosis_sequence():  
    eob_data = load_sample_eob()
    eob_data["item"][0].pop("diagnosisSequence")
    
    sld = extract_sld(eob_data)
    assert sld[0].linked_diagnosis_codes == []

def test_extract_sld_missing_serviced_period():
    eob_data = load_sample_eob()
    eob_data["item"][0].pop("servicedPeriod")
    
    sld = extract_sld(eob_data)
    assert sld[0].service_date == "2023-01-01"  # Should fall back to billablePeriod

def test_extract_sld_invalid_data():
    with pytest.raises(ValueError):
        extract_sld({"resourceType": "Invalid"})

def test_extract_sld_non_hcpcs_item():
    eob_data = load_sample_eob()
    eob_data["item"][0]["productOrService"]["coding"][0]["system"] = "https://some-other-system.com"
    
    sld = extract_sld(eob_data)
    assert len(sld) == 1
    assert sld[0].procedure_code is None

def test_extract_sld_list():
    eob_data_list = load_sample_eob_list()
    sld_list = extract_sld_list(eob_data_list)
    assert len(sld_list) == 200

def test_extract_sld_invalid_data():
    # Test various invalid data scenarios
    with pytest.raises(TypeError):
        extract_sld(None)
    with pytest.raises(TypeError):
        extract_sld([])  # Wrong type
    with pytest.raises(TypeError):
        extract_sld({})  # Empty dict
    with pytest.raises(ValueError):
        extract_sld({"resourceType": "Patient"})  # Wrong resource type

def test_extract_sld_list_empty():
    assert extract_sld_list([]) == []

def test_extract_sld_list_mixed_validity():
    # Test handling of mixed valid/invalid data
    data = [
        load_sample_eob(1),  # valid
        {"resourceType": "Invalid"},  # invalid
        load_sample_eob(2)   # valid
    ]
    sld_list = extract_sld_list(data)
    assert len(sld_list) == 3  # Should only include valid entries

