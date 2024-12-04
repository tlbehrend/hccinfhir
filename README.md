# `hccfhir`
HCC (Hierarchical Condition Category) Algorithm Implementation for FHIR Resources

## Overview
`hccfhir` implements the CMS-HCC Risk Adjustment model using FHIR (Fast Healthcare Interoperability Resources) data. It processes Blue Button 2.0 API (BCDA) data to calculate Hierarchical Condition Category (HCC) Risk Adjustment Factors (RAF).

## Why FHIR-Based HCC Processing?
Risk Adjustment calculations traditionally rely on processed claims data, leading to information loss and reconciliation challenges. `hccfhir` processes FHIR resources directly because:
- FHIR represents the source of truth with complete clinical and administrative data
- Risk Adjustment requires multiple data elements beyond diagnosis codes
- Direct processing eliminates data transformation errors and simplifies reconciliation

## Data Flexibility
While built for native FHIR processing, `hccfhir` works with any data source that can be transformed into the MDE format:

```python
mde = [{
    "procedure_code": "99214",
    "diagnosis_codes": ["E11.9", "I10"],
    "claim_type": "71",
    "provider_specialty": "01", 
    "service_date": "2024-01-15"
}, ...]
```

## Components

### 1. Extractor Module
Processes FHIR ExplanationOfBenefit resources to extract Minimum Data Elements (MDE):
```python
from hccfhir.extractor import extract_mde
mde = extract_mde(eob_data)  # Process single EOB

from hccfhir import HCCFHIR
processor = HCCFHIR()
mde_list = processor.extract_mde_list([eob1, eob2])  # Process multiple EOBs
```

### 2. Logic Module (In Development)
Implements core HCC calculation logic:
- Maps diagnosis codes to HCC categories
- Applies hierarchical rules and interactions
- Calculates final RAF scores
- Integrates with standard CMS data files

### 3. Filter Module (In Development)
Implements claim filtering rules:
- Inpatient/outpatient criteria
- Professional service requirements
- Provider validation
- Date range filtering

## Installation
```bash
pip install hccfhir
```

## Usage
```python
from hccfhir import HCCFHIR

hcc_processor = HCCFHIR()
mde_list = hcc_processor.extract_mde_list(eob_list)
filtered_mde = hcc_processor.apply_filters(mde_list)  # future
raf_score = hcc_processor.calculate_raf(filtered_mde, demographic_data)  # future
```

## Dependencies
- Pydantic
- Standard Python libraries

## Contributing
Join us at [mimilabs](https://mimilabs.ai/signup). Reference data available in MIMILabs data lakehouse.

## License
Apache License 2.0