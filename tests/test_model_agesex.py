import pytest
from hccinfhir.model_agesex import categorize_age_sex, AgeSexCategory

def test_basic_v6_categorization():
    """Test basic V6 (ACA) categorization"""
    result = categorize_age_sex(35, 'M', version='V6')
    assert isinstance(result, AgeSexCategory)
    assert result.category == 'MAGE_LAST_35_39'
    assert result.version == 'V6'
    assert result.non_aged is True
    assert result.disabled is False
    assert result.orig_disabled is False

def test_basic_v2_categorization():
    """Test basic V2 (Medicare) categorization"""
    result = categorize_age_sex(75, 'F', orec='0', version='V2')
    assert result.category == 'F75_79'
    assert result.version == 'V2'
    assert result.non_aged is False
    assert result.disabled is False
    assert result.orig_disabled is False

def test_input_validation():
    """Test input validation"""
    with pytest.raises(ValueError, match="Age must be a number"):
        categorize_age_sex("35", 'M', version='V6')
    
    with pytest.raises(ValueError, match="Age must be non-negative"):
        categorize_age_sex(-5, 'M', version='V6')
    
    with pytest.raises(ValueError, match="Sex must be"):
        categorize_age_sex(35, 'X', version='V6')
    
    with pytest.raises(ValueError, match="Version must be"):
        categorize_age_sex(35, 'M', version='V3')
    
    with pytest.raises(ValueError, match="OREC is required"):
        categorize_age_sex(35, 'M', version='V2')

def test_sex_normalization():
    """Test that different sex formats are normalized correctly"""
    v6_male = categorize_age_sex(35, 'M', version='V6')
    v6_male_num = categorize_age_sex(35, '1', version='V6')
    assert v6_male.category == v6_male_num.category

    v6_female = categorize_age_sex(35, 'F', version='V6')
    v6_female_num = categorize_age_sex(35, '2', version='V6')
    assert v6_female.category == v6_female_num.category

def test_disability_flags():
    """Test disability and original disability flags"""
    # Currently disabled
    result = categorize_age_sex(45, 'M', orec='1', version='V2')
    assert result.disabled is True
    assert result.orig_disabled is False

    # Originally disabled, now aged
    result = categorize_age_sex(70, 'M', orec='1', version='V2')
    assert result.disabled is False
    assert result.orig_disabled is True

    # Neither disabled
    result = categorize_age_sex(70, 'M', orec='0', version='V2')
    assert result.disabled is False
    assert result.orig_disabled is False

def test_age_boundaries():
    """Test edge cases for age ranges"""
    # Test V6 boundaries
    assert categorize_age_sex(0, 'M', version='V6').category == 'MAGE_LAST_0_0'
    assert categorize_age_sex(1, 'M', version='V6').category == 'MAGE_LAST_1_1'
    assert categorize_age_sex(60, 'M', version='V6').category == 'MAGE_LAST_60_GT'
    assert categorize_age_sex(99, 'M', version='V6').category == 'MAGE_LAST_60_GT'

    # Test V2 boundaries
    assert categorize_age_sex(34, 'M', orec='0', version='V2').category == 'M0_34'
    assert categorize_age_sex(35, 'M', orec='0', version='V2').category == 'M35_44'
    assert categorize_age_sex(95, 'M', orec='0', version='V2').category == 'M95_GT' 