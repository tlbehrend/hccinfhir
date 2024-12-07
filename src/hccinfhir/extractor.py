from typing import Union, List, Literal
from models import MinimalDataElement
from extractor_837 import extract_mde_837
from extractor_fhir import extract_mde_fhir

def extract_mde(
    data: Union[str, dict, List[dict]], 
    format: Literal["837", "fhir"]
) -> List[MinimalDataElement]:
    """
    Unified entry point for MDE extraction with explicit format specification
    
    Args:
        data: Input data - string for 837, dict/List[dict] for FHIR
        format: Data format - either "837" or "fhir"
        
    Returns:
        List of MinimalDataElement
        
    Raises:
        ValueError: If format and data type don't match or format is invalid
    """
    if format == "837":
        if not isinstance(data, str):
            raise ValueError("837 format requires string input")
        return extract_mde_837(data)
        
    elif format == "fhir":
        if isinstance(data, dict):
            return extract_mde_fhir(data)
        elif isinstance(data, list):
            results = []
            for item in data:
                if not isinstance(item, dict):
                    raise ValueError("FHIR format requires dict or list of dicts")
                try:
                    results.extend(extract_mde_fhir(item))
                except ValueError as e:
                    print(f"Warning: Skipping invalid EOB: {str(e)}")
            return results
        else:
            raise ValueError("FHIR format requires dict or list of dicts")
            
    else:
        raise ValueError('Format must be either "837" or "fhir"')

# Example usage
if __name__ == "__main__":
    # Example 837 data
    x12_data = """NM1*QC*1*DOE*JOHN****MI*12345~..."""
    with open('data/sample_837_11.txt', 'r') as file:
        x12_data = file.read()
        x12_mdes = extract_mde(x12_data, format="837")
        from pprint import pprint
        pprint(x12_mdes)
    
    # Example FHIR data
    fhir_data = {"resourceType": "ExplanationOfBenefit"}
    fhir_mdes = extract_mde(fhir_data, format="fhir")
    #print(fhir_mdes)
    import json
    with open('data/sample_eob_200.ndjson', 'r') as file:
        for line in file:
            eob_data = json.loads(line)
            mde = extract_mde(eob_data, format="fhir")
            #print(mde)
