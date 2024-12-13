from typing import Union
from hccinfhir.models import AgeSexCategory
    
def categorize_age_sex(age: Union[int, float], sex: str, orec: str = None, version: str = 'V2') -> AgeSexCategory:
    """
    Categorize age and sex based on different version logics (V2, V4, V6)
    
    Parameters:
    ----------
    age : Union[int, float]
        Age of the person (will be floored if float)
    sex : str
        Sex of the person ('M', 'F', '1', '2')
    orec : str, optional
        Original reason for entitlement, required for V2/V4
    version : str, default='V2'
        Version of categorization logic to use:
        - V2: CMS-HCC for Medicare
        - V4: RxHCC
        - V6: ACA-HCC
        
    Returns:
    -------
    AgeSexCategory
        Pydantic model containing:
        - category: str (age-sex category code)
        - version: str (V2/V4/V6)
        - non_aged: bool (True if age <= 64)
        - orig_disabled: bool (True if originally disabled)
        - disabled: bool (True if currently disabled)
        
    Raises:
    ------
    ValueError
        If age is negative or non-numeric
        If sex is not in ('M', 'F', '1', '2')
        If version is not in ('V2', 'V4', 'V6')
        If orec is missing for V2/V4
    """
    
    if not isinstance(age, (int, float)):
        raise ValueError("Age must be a number")
    if age < 0:
        raise ValueError("Age must be non-negative")
        
    # Convert to integer using floor
    age = int(age)
    non_aged = age <= 64

    # Standardize sex input
    if sex in ('M', '1'):
        std_sex = '1'  # For V2/V4
        v6_sex = 'M'   # For V6
    elif sex in ('F', '2'):
        std_sex = '2'  # For V2/V4
        v6_sex = 'F'   # For V6
    else:
        raise ValueError("Sex must be 'M', 'F', '1', or '2'")
    
    # Determine if person is disabled or originally disabled
    disabled = age < 65 and orec is not None and orec != "0"
    orig_disabled = orec is not None and orec == '1' and not disabled

    result_dict = {
        'version': version,
        'non_aged': non_aged,
        'orig_disabled': orig_disabled,
        'disabled': disabled
    }

    # V6 Logic (ACA Population)
    if version == 'V6':
        age_ranges = [
            (0, 0, '0_0'),
            (1, 1, '1_1'),
            (2, 4, '2_4'),
            (5, 9, '5_9'),
            (10, 14, '10_14'),
            (15, 20, '15_20'),
            (21, 24, '21_24'),
            (25, 29, '25_29'),
            (30, 34, '30_34'),
            (35, 39, '35_39'),
            (40, 44, '40_44'),
            (45, 49, '45_49'),
            (50, 54, '50_54'),
            (55, 59, '55_59'),
            (60, float('inf'), '60_GT')
        ]
        
        for low, high, label in age_ranges:
            if low <= age <= high:
                result_dict['category'] = f"{v6_sex}AGE_LAST_{label}"
                return AgeSexCategory(**result_dict)
    
    # V2/V4 Logic (Medicare Population)
    elif version in ('V2', 'V4'):
        if orec is None:
            raise ValueError("OREC is required for V2/V4 categorization")
        
        # New enrollee logic
        is_new_enrollee = False  # Define based on business rules
        
        if is_new_enrollee:
            prefix = 'NEF' if std_sex == '2' else 'NEM'
            
            if age <= 34:
                category = f'{prefix}0_34'
            elif 34 < age <= 44:
                category = f'{prefix}35_44'
            elif 44 < age <= 54:
                category = f'{prefix}45_54'
            elif 54 < age <= 59:
                category = f'{prefix}55_59'
            elif (59 < age <= 63) or (age == 64 and orec != '0'):
                category = f'{prefix}60_64'
            elif (age == 64 and orec == '0') or age == 65:
                category = f'{prefix}65'
            elif age == 66:
                category = f'{prefix}66'
            elif age == 67:
                category = f'{prefix}67'
            elif age == 68:
                category = f'{prefix}68'
            elif age == 69:
                category = f'{prefix}69'
            elif 69 < age <= 74:
                category = f'{prefix}70_74'
            elif 74 < age <= 79:
                category = f'{prefix}75_79'
            elif 79 < age <= 84:
                category = f'{prefix}80_84'
            elif 84 < age <= 89:
                category = f'{prefix}85_89'
            elif 89 < age <= 94:
                category = f'{prefix}90_94'
            else:
                category = f'{prefix}95_GT'
        
        else:
            prefix = 'F' if std_sex == '2' else 'M'
            age_ranges = [
                (0, 34, '0_34'),
                (34, 44, '35_44'),
                (44, 54, '45_54'),
                (54, 59, '55_59'),
                (59, 64, '60_64'),
                (64, 69, '65_69'),
                (69, 74, '70_74'),
                (74, 79, '75_79'),
                (79, 84, '80_84'),
                (84, 89, '85_89'),
                (89, 94, '90_94'),
                (94, float('inf'), '95_GT')
            ]
            
            for low, high, suffix in age_ranges:
                if low < age <= high:
                    category = f'{prefix}{suffix}'
                    break
            else:
                raise ValueError(f"Unable to categorize age: {age}")
        
        result_dict['category'] = category
        return AgeSexCategory(**result_dict)
    
    else:
        raise ValueError("Version must be 'V2', 'V4', or 'V6'")