# `hccinfhir` (HCC in FHIR)
A Python library for extracting standardized service-level data from FHIR ExplanationOfBenefit resources, with a focus on supporting HCC (Hierarchical Condition Category) risk adjustment calculations.

## Features
- Extract diagnosis codes, procedures, providers, and other key data elements from FHIR EOBs
- Support for both BCDA (Blue Button 2.0) and standard FHIR R4 formats
- Pydantic models for type safety and data validation
- Standardized Service Level Data (SLD) output format
- Multiple HCC model support (V22, V24, V28, ESRD V21, ESRD V24, RxHCC V08)
- Flexible input options: FHIR EOBs, service data, or direct diagnosis codes


## Installation
```bash
pip install hccinfhir
```

## Why FHIR-Based HCC Processing?
Risk Adjustment calculations traditionally rely on processed claims data, leading to information loss and reconciliation challenges. `hccinfhir` processes FHIR resources directly because:
- FHIR represents the source of truth with complete clinical and administrative data
- Risk Adjustment requires multiple data elements beyond diagnosis codes
- Direct processing eliminates data transformation errors and simplifies reconciliation

## Data Model & Flexibility
While built for native FHIR processing, `hccinfhir` works with any data source that can be transformed into the SLD (Service Level Data) format:

```python
sld = [{
    "procedure_code": "99214",
    "diagnosis_codes": ["E11.9", "I10"],
    "claim_type": "71",
    "provider_specialty": "01", 
    "service_date": "2024-01-15"
}, ...]
```

Or, for direct risk score calculation from a list of diagnosis codes, you only need the model name, diagnosis codes, and basic demographic factors:

```python
from hccinfhir.model_calculate import calculate_raf

diagnosis_codes = ['E119', 'I509']  # Diabetes without complications, Heart failure
age = 67
sex = 'F'
model_name = "CMS-HCC Model V24"

result = calculate_raf(
   diagnosis_codes=diagnosis_codes,
   model_name=model_name,
   age=age,
   sex=sex
)
```


For more details on the SLD format, see the `datamodels.py` file.

## Core Components

### 1. Extractor Module
Processes FHIR ExplanationOfBenefit resources to extract Minimum Data Elements (MDE):
```python
from hccinfhir.extractor import extract_sld, extract_sld_list

sld = extract_sld(eob_data)  # Process single EOB

sld_list = extract_sld_list([eob1, eob2])  # Process multiple EOBs
```

### 2. Filter Module
Implements claim filtering rules:
- Inpatient/outpatient criteria - Type of Bill + Eligible CPT/HCPCS
- Professional service requirements - Eligible CPT/HCPCS
- Provider validation (Not in scope for this release, applicable to RAPS)
```python
from hccinfhir.filter import apply_filter

filtered_sld = apply_filter(sld_list)
```


### 3. Logic Module 
Implements core HCC calculation logic:
- Maps diagnosis codes to HCC categories
- Applies hierarchical rules and interactions
- Calculates final RAF scores
- Integrates with standard CMS data files

```python
from hccinfhir.model_calculate import calculate_raf

diagnosis_codes = ['E119', 'I509']  # Diabetes without complications, Heart failure
result = calculate_raf(
   diagnosis_codes=diagnosis_codes,
   model_name="CMS-HCC Model V24",
   age=67,
   sex='F'
)
```

### 4. HCCInFHIR Class
The main processor class that integrates extraction, filtering, and calculation components:

```python
from hccinfhir.hccinfhir import HCCInFHIR
from hccinfhir.datamodels import Demographics

# Initialize with custom configuration
hcc_processor = HCCInFHIR(
    filter_claims=True,                                    # Enable claim filtering
    model_name="CMS-HCC Model V28",                       # Choose HCC model version
    proc_filtering_filename="ra_eligible_cpt_hcpcs_2025.csv",  # CPT/HCPCS filtering rules
    dx_cc_mapping_filename="ra_dx_to_cc_2025.csv"         # Diagnosis to CC mapping
)

# Define beneficiary demographics
demographics = {
    age=67,
    sex='F'
}

# Method 1: Process FHIR EOB resources
raf_result = hcc_processor.run(eob_list, demographics)

# Method 2: Process service level data
service_data = [{
    "procedure_code": "99214",
    "claim_diagnosis_codes": ["E11.9", "I10"],
    "claim_type": "71",
    "service_date": "2024-01-15"
}]
raf_result = hcc_processor.run_from_service_data(service_data, demographics)

# Method 3: Direct diagnosis processing
diagnosis_codes = ['E119', 'I509']
raf_result = hcc_processor.calculate_from_diagnosis(diagnosis_codes, demographics)

# RAF Result contains:
print(f"Risk Score: {raf_result['risk_score']}")
print(f"HCC List: {raf_result['hcc_list']}")
print(f"CC to Diagnosis Mapping: {raf_result['cc_to_dx']}")
print(f"Applied Coefficients: {raf_result['coefficients']}")
print(f"Applied Interactions: {raf_result['interactions']}")
```

The HCCInFHIR class provides three main processing methods:

1. `run(eob_list, demographics)`: Process FHIR ExplanationOfBenefit resources
   - Extracts service data from FHIR resources
   - Applies filtering rules if enabled
   - Calculates RAF scores using the specified model

2. `run_from_service_data(service_data, demographics)`: Process standardized service data
   - Accepts pre-formatted service level data
   - Validates data structure using Pydantic models
   - Applies filtering and calculates RAF scores

3. `calculate_from_diagnosis(diagnosis_codes, demographics)`: Direct diagnosis processing
   - Processes raw diagnosis codes without service context
   - Useful for quick RAF calculations or validation
   - Bypasses service-level filtering

Each method returns a RAFResult containing:
- Final risk score
- List of HCCs
- Mapping of condition categories to diagnosis codes
- Applied coefficients and interactions
- Processed service level data (when applicable)

## Testing
```bash
$ python3 -m hatch shell
$ python3 -m pip install -e .
$ python3 -m pytest tests/*
``` 

## Dependencies
- Pydantic >= 2.10.3
- Standard Python libraries

## Research: FHIR BCDA and 837 Field Mapping Analysis

### Core Identifiers
| Field | 837 Source | FHIR BCDA Source | Alignment Analysis |
|-------|------------|------------------|-------------------|
| claim_id | CLM01 segment | eob.id | ✓ Direct mapping |
| patient_id | NM109 when NM101='IL' | eob.patient.reference (last part after '/') | ✓ Aligned but different formats |

### Provider Information
| Field | 837 Source | FHIR BCDA Source | Alignment Analysis |
|-------|------------|-------------------|-------------------|
| performing_provider_npi | NM109 when NM101='82' and NM108='XX' | careTeam member with role 'performing'/'rendering' | ✓ Aligned |
| billing_provider_npi | NM109 when NM101='85' and NM108='XX' | contained resources with NPI system identifier | ✓ Conceptually aligned |
| provider_specialty | PRV03 when PRV01='PE' | careTeam member qualification with specialty system | ✓ Aligned but different code systems |

### Claim Type Information
| Field | 837 Source | FHIR BCDA Source | Alignment Analysis |
|-------|------------|-------------------|-------------------|
| claim_type | GS08 (mapped via CLAIM_TYPES) | eob.type with claim_type system | ✓ Aligned but different coding |
| facility_type | CLM05-1 (837I only) | facility.extension with facility_type system | ✓ Aligned for institutional claims |
| service_type | CLM05-2 (837I only) | extension or eob.type with service_type system | ✓ Aligned for institutional claims |

### Service Line Information
| Field | 837 Source | FHIR BCDA Source | Alignment Analysis |
|-------|------------|-------------------|-------------------|
| procedure_code | SV1/SV2 segment, element 2 | item.productOrService with pr system | ✓ Aligned |
| ndc | LIN segment after service line | item.productOrService with ndc system or extension | ✓ Aligned but different locations |
| quantity | SV1/SV2 element 4 | item.quantity.value | ✓ Direct mapping |
| quantity_unit | SV1/SV2 element 5 | item.quantity.unit | ✓ Direct mapping |
| service_date | DTP segment with qualifier 472 | item.servicedPeriod or eob.billablePeriod | ✓ Aligned |
| place_of_service | SV1 element 6 | item.locationCodeableConcept with place_of_service system | ✓ Aligned |
| modifiers | SV1/SV2 segment, additional qualifiers | item.modifier with pr system | ✓ Aligned |

### Diagnosis Information
| Field | 837 Source | FHIR BCDA Source | Alignment Analysis |
|-------|------------|-------------------|-------------------|
| linked_diagnosis_codes | SV1/SV2 diagnosis pointers + HI segment codes | item.diagnosisSequence + diagnosis lookup | ✓ Aligned but different structure |
| claim_diagnosis_codes | HI segment codes | diagnosis array with icd10cm/icd10 systems | ✓ Aligned |

### Additional Fields
| Field | 837 Source | FHIR BCDA Source | Alignment Analysis |
|-------|------------|-------------------|-------------------|
| allowed_amount | Not available in 837 | item.adjudication with 'eligible' category | ⚠️ Only in FHIR |

### Key Differences and Notes

1. **Structural Differences**:
   - 837 uses a segment-based approach with positional elements
   - FHIR uses a nested object structure with explicit systems and codes

2. **Code Systems**:
   - FHIR explicitly defines systems for each code (via SYSTEMS constant)
   - 837 uses implicit coding based on segment position and qualifiers

3. **Data Validation**:
   - FHIR implementation uses Pydantic models for validation
   - 837 implements manual validation and parsing

4. **Diagnosis Handling**:
   - 837: Direct parsing from HI segment with position-based lookup
   - FHIR: Uses sequence numbers and separate diagnosis array

5. **Provider Information**:
   - 837: Direct from NM1 segments with role qualifiers
   - FHIR: Through careTeam structure with role coding

### TODO: Enhancement Suggestions

1. Consider adding validation for code systems in 837 parser to match FHIR's explicitness
2. Standardize date handling between both implementations
3. Add support for allowed_amount in 837 if available in different segments
4. Consider adding more robust error handling in both implementations

## Data Files

`ra_dx_to_cc_mapping_2025.csv`
```sql
SELECT diagnosis_code, cc, model_name 
FROM ra_dx_to_cc_mapping 
WHERE year = 2025 and model_type = 'Initial';
```

`ra_hierarchies_2025.csv`
```sql
SELECT cc_parent, 
  cc_child, 
  model_domain, 
  model_version, 
  model_fullname
FROM ra_hierarchies
WHERE eff_last_date > '2025-01-01';
```

`ra_coefficients_2025.csv`
```sql
SELECT coefficient, value, model_domain, model_version 
FROM ra_coefficients 
WHERE eff_last_date > '2025-01-01';
```   

`ra_eligible_cpt_hcpcs_2025.csv`
```sql
SELECT DISTINCT cpt_hcpcs_code
FROM mimi_ws_1.cmspayment.ra_eligible_cpt_hcpcs
WHERE is_included = 'yes' AND YEAR(mimi_src_file_date) = 2024;
```

## Contributing
Join us at [mimilabs](https://mimilabs.ai/signup). Reference data available in MIMILabs data lakehouse.

## Publishing (only for those maintainers...)
```bash
$ python3 -m hatch build
$ python3 -m hatch publish
```

## License
Apache License 2.0