import pytest
from hccinfhir.model_dx_to_cc import apply_mapping
from hccinfhir.model_hierarchies import apply_hierarchies

def test_diabetes_hierarchy_chain():
    """Test complete chain from diagnosis codes to final hierarchical CCs for diabetes"""
    # Type 1 diabetes with complications maps to HCC 17
    # Type 2 diabetes with complications maps to HCC 18
    # Diabetes without complications maps to HCC 19
    diagnoses = [
        "E1100",  # type 2 diabetes mellitus with hyperosmolarity without nonketotic hyperglycemic-hyperosmolar coma (NKHHC)
        "E1022",  # Type 1 diabetes with kidney complications
        "E1165",  # Type 2 diabetes with circulatory complications
        "E119"    # Type 2 diabetes without complications
    ]
    
    # First map dx to CCs
    cc_to_dx = apply_mapping(diagnoses, model_name="CMS-HCC Model V24")
    ccs = set(cc_to_dx.keys())

    # Then apply hierarchies
    final_ccs = apply_hierarchies(ccs, model_name="CMS-HCC Model V24")

    # Should only keep the highest severity CC (17)
    assert final_ccs == {"17"}
