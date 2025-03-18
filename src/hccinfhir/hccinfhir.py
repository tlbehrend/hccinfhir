from typing import List, Dict, Any, Union
from hccinfhir.extractor import extract_sld_list
from hccinfhir.filter import apply_filter
from hccinfhir.model_calculate import calculate_raf
from hccinfhir.datamodels import Demographics, ServiceLevelData, RAFResult, ModelName


class HCCInFHIR:
    """
    Main class for processing FHIR EOB resources into HCC risk scores.
    
    This class integrates the extraction, filtering, and calculation components
    of the hccinfhir library.
    """
    
    def __init__(self, 
                 filter_claims: bool = True, 
                 model_name: ModelName = "CMS-HCC Model V28"):
        """
        Initialize the HCCInFHIR processor.
        
        Args:
            filter_claims: Whether to apply filtering rules to claims. Default is True.
            model_name: The name of the model to use for the calculation. Default is "CMS-HCC Model V28".
        """
        self.filter_claims = filter_claims
        self.model_name = model_name
        
    def _ensure_demographics(self, demographics: Union[Demographics, Dict[str, Any]]) -> Demographics:
        """Convert demographics dict to Demographics object if needed."""
        if not isinstance(demographics, Demographics):
            return Demographics(**demographics)
        return demographics
    
    def _calculate_raf_from_demographics(self, diagnosis_codes: List[str], 
                                       demographics: Demographics) -> Dict[str, Any]:
        """Calculate RAF score using demographics data."""
        return calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name=self.model_name,
            age=demographics.age,
            sex=demographics.sex,
            dual_elgbl_cd=demographics.dual_elgbl_cd,
            orec=demographics.orec,
            crec=demographics.crec,
            new_enrollee=demographics.new_enrollee,
            snp=demographics.snp,
            low_income=demographics.low_income,
            graft_months=demographics.graft_months
        )

    def _get_unique_diagnosis_codes(self, service_data: List[ServiceLevelData]) -> List[str]:
        """Extract unique diagnosis codes from service level data."""
        all_dx_codes = []
        for sld in service_data:
            all_dx_codes.extend(sld.claim_diagnosis_codes)
        return list(set(all_dx_codes))

    def _format_result(self, 
                  raf_result: Union[Dict[str, Any], RAFResult], 
                  service_data: List[ServiceLevelData]) -> RAFResult:
        """
        Format RAF calculation results into a standardized RAFResult format.
        
        Returns a dictionary conforming to the RAFResult TypedDict structure.
        """
        
        # Check if raf_result already has the expected RAFResult structure
        if all(key in raf_result for key in ['risk_score', 'hcc_list', 'details']):
            # Already in RAFResult format, just ensure service data is set
            result = dict(raf_result)  # Create a copy to avoid modifying the original
            result['service_level_data'] = service_data
            return result
        
        # Handle result from calculate_raf function
        if 'raf' in raf_result and 'coefficients' in raf_result:
            return {
                'risk_score': raf_result['raf'],
                'hcc_list': list(raf_result['coefficients'].keys()),
                'details': raf_result['coefficients'],
                'service_level_data': service_data
            }
        
        # Unrecognized format
        raise ValueError(f"Unrecognized RAF result format: {list(raf_result.keys())}")

    def run(self, eob_list: List[Dict[str, Any]], 
            demographics: Union[Demographics, Dict[str, Any]]) -> RAFResult:
        demographics = self._ensure_demographics(demographics)
        
        # Extract and filter service level data
        sld_list = extract_sld_list(eob_list)
        if self.filter_claims:
            sld_list = apply_filter(sld_list)
            
        # Calculate RAF score
        unique_dx_codes = self._get_unique_diagnosis_codes(sld_list)
        raf_result = self._calculate_raf_from_demographics(unique_dx_codes, demographics)
        
        return self._format_result(raf_result, sld_list)
    
    def run_from_service_data(self, service_data: List[Union[ServiceLevelData, Dict[str, Any]]], 
                             demographics: Union[Demographics, Dict[str, Any]]) -> RAFResult:
        demographics = self._ensure_demographics(demographics)
        
        if not isinstance(service_data, list):
            raise ValueError("Service data must be a list of service records")
        
        if not service_data:
            raise ValueError("Service data list cannot be empty")
        
        # Standardize service data with better error handling
        standardized_data = []
        for idx, item in enumerate(service_data):
            try:
                if isinstance(item, dict):
                    standardized_data.append(ServiceLevelData(**item))
                elif isinstance(item, ServiceLevelData):
                    standardized_data.append(item)
                else:
                    raise TypeError(f"Service data item must be a dictionary or ServiceLevelData object")
            except (KeyError, TypeError, ValueError) as e:
                raise ValueError(
                    f"Invalid service data at index {idx}: {str(e)}. "
                    "Required fields: claim_type, claim_diagnosis_codes, procedure_code, service_date"
                )
        
        if self.filter_claims:
            standardized_data = apply_filter(standardized_data)
        
        # Calculate RAF score
        unique_dx_codes = self._get_unique_diagnosis_codes(standardized_data)
        raf_result = self._calculate_raf_from_demographics(unique_dx_codes, demographics)
        
        return self._format_result(raf_result, standardized_data)
        
    def calculate_from_diagnosis(self, diagnosis_codes: List[str],
                               demographics: Union[Demographics, Dict[str, Any]]) -> RAFResult:
        demographics = self._ensure_demographics(demographics)
        raf_result = self._calculate_raf_from_demographics(diagnosis_codes, demographics)
        # Create an empty service level data list since we're calculating directly from diagnosis codes
        return self._format_result(raf_result, []) 