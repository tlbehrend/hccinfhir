import pytest
from hccinfhir.hccinfhir import HCCInFHIR
from hccinfhir.datamodels import Demographics, ServiceLevelData, RAFResult
import importlib.resources
import json
from pydantic_core import ValidationError

@pytest.fixture
def sample_demographics():
    return {
        "age": 70,
        "sex": "M",
        "dual_elgbl_cd": "00",
        "orig_disabled": False,
        "new_enrollee": False,
        "esrd": False,
        "snp": False,
        "low_income": False,
        "graft_months": None,
        "category": "CNA"
    }

@pytest.fixture
def sample_eob():
    output = []
    with importlib.resources.open_text('hccinfhir.samples', 
                                      f'sample_eob_200.ndjson') as f:
        for line in f:
            eob_data = json.loads(line)
            output.append(eob_data)
    return output

@pytest.fixture
def sample_service_data():
    return [
        {
            "claim_id": "1",
            "claim_type": "professional",
            "claim_diagnosis_codes": ["E119"],
            "procedure_code": "99213",
            "service_date": "2023-01-01"
        },
        {
            "claim_id": "2",
            "claim_type": "professional",
            "claim_diagnosis_codes": ["E119"],
            "procedure_code": "0398T",
            "service_date": "2023-01-02"
        }
    ]

class TestHCCInFHIR:
    def test_initialization(self):
        processor = HCCInFHIR()
        assert processor.filter_claims is True
        
        processor = HCCInFHIR(filter_claims=False)
        assert processor.filter_claims is False

    def test_ensure_demographics(self):
        processor = HCCInFHIR()
        demo_dict = {
            "age": 70,
            "sex": "M",
            "dual_elgbl_cd": "00",
            "orig_disabled": False,
            "new_enrollee": False,
            "esrd": False,
            "category": "CNA"
        }
        
        # Test with dictionary
        result = processor._ensure_demographics(demo_dict)
        assert isinstance(result, Demographics)
        assert result.age == 70
        assert result.sex == "M"
        assert result.dual_elgbl_cd == "00"
        assert result.category == "CNA"
        assert result.non_aged == False
        assert result.orig_disabled == False
        assert result.disabled == False
        assert result.esrd == False
        assert result.snp == False
        assert result.low_income == False
        
        # Test with Demographics object
        demo_obj = Demographics(**demo_dict)
        result = processor._ensure_demographics(demo_obj)
        assert isinstance(result, Demographics)

    def test_run_with_eob(self, sample_demographics, sample_eob):
        processor = HCCInFHIR()
        result = processor.run(sample_eob, sample_demographics)
        assert isinstance(result, dict)
        assert 'risk_score' in result
        assert 'hcc_list' in result
        assert 'service_level_data' in result
        assert isinstance(result['service_level_data'], list)
        
        # Verify service level data processing
        sld = result['service_level_data'][0]
        assert isinstance(sld, ServiceLevelData)


    def test_run_from_service_data(self, sample_demographics, sample_service_data):
        processor = HCCInFHIR()
        result = processor.run_from_service_data(sample_service_data, sample_demographics)
        
        assert isinstance(result, dict)
        assert 'risk_score' in result
        assert 'hcc_list' in result
        assert 'service_level_data' in result
        # Verify service data processing
        sld = result['service_level_data'][0]
        assert isinstance(sld, ServiceLevelData)
        assert "E119" in sld.claim_diagnosis_codes

    def test_calculate_from_diagnosis(self, sample_demographics):
        processor = HCCInFHIR()
        diagnosis_codes = ["E119"]  # Type 2 diabetes without complications
        
        result = processor.calculate_from_diagnosis(diagnosis_codes, sample_demographics)
        
        assert isinstance(result, dict)
        assert 'risk_score' in result
        assert 'hcc_list' in result
        assert 'demographics' in result

    def test_filtering_behavior(self, sample_demographics, sample_service_data):
        # Test with filtering enabled
        processor_with_filter = HCCInFHIR(filter_claims=True)
        result_filtered = processor_with_filter.run_from_service_data(
            sample_service_data, sample_demographics
        )
        
        # Test with filtering disabled
        processor_without_filter = HCCInFHIR(filter_claims=False)
        result_unfiltered = processor_without_filter.run_from_service_data(
            sample_service_data, sample_demographics
        )
        
        # Results might be the same in this case, but verify they're dictionaries
        assert isinstance(result_filtered, dict)
        assert isinstance(result_unfiltered, dict)

    def test_filtering_behavior_with_custom_files(self, sample_demographics, sample_service_data):
        
        processor = HCCInFHIR(filter_claims=True, 
                             proc_filtering_filename='ra_eligible_cpt_hcpcs_2025.csv',
                             dx_cc_mapping_filename='ra_dx_to_cc_2025.csv')
        result = processor.run_from_service_data(sample_service_data, sample_demographics)
        print(result['service_level_data'])
        assert len(result['service_level_data']) == 1

        processor = HCCInFHIR(filter_claims=False, 
                             proc_filtering_filename='ra_eligible_cpt_hcpcs_2023.csv',
                             dx_cc_mapping_filename='ra_dx_to_cc_2025.csv')
        result = processor.run_from_service_data(sample_service_data, sample_demographics)
        print(result)
        assert len(result['service_level_data']) == 2



    def test_error_handling(self):
        processor = HCCInFHIR()
        
        # Test with invalid demographics
        with pytest.raises(ValidationError, match="3 validation errors for Demographics"):
            processor.run([], {"invalid": "data"})
        
        # Test with empty service data
        with pytest.raises(ValueError, match="Service data list cannot be empty"):
            processor.run_from_service_data([], {
                "age": 70,
                "sex": "M",
                "dual_elgbl_cd": "00",
                "orig_disabled": False,
                "new_enrollee": False,
                "esrd": False,
                "category": "CNA"
            })
        
        # Test with non-list service data
        with pytest.raises(ValueError, match="Service data must be a list"):
            processor.run_from_service_data("not a list", {
                "age": 70,
                "sex": "M",
                "dual_elgbl_cd": "00",
                "orig_disabled": False,
                "new_enrollee": False,
                "esrd": False,
                "category": "CNA"
            })
