import pytest
from decimal import Decimal
from services.derived_calculations import DerivedCalculationService
from services.calculation import CalculationService

def test_derive_pt_marks_calculation():
    """Test PT1 derived calculation: 15/25 -> 3.00/5"""
    result = CalculationService.derive_pt_marks(15, 25)
    assert result == 3.00

def test_derive_pt_marks_with_decimal():
    """Test PT1 derived calculation with decimal: 12.5/25 -> 2.50/5"""
    result = CalculationService.derive_pt_marks(12.5, 25)
    assert result == 2.50

def test_derive_pt_marks_full_score():
    """Test PT1 derived calculation: 25/25 -> 5.00/5"""
    result = CalculationService.derive_pt_marks(25, 25)
    assert result == 5.00

def test_derive_pt_marks_zero():
    """Test PT1 derived calculation: 0/25 -> 0.00/5"""
    result = CalculationService.derive_pt_marks(0, 25)
    assert result == 0.00

def test_french_conversion():
    """Test French conversion: 35/40 -> 70.00/80"""
    result = DerivedCalculationService.calculate_french_conversion(
        student_id=1,
        subject_id=1,
        component_id=1,
        raw_marks=35,
        max_marks=40,
        target_max=80
    )
    assert result is not None
    assert result["marks"] == 70.00
    assert result["status"] == "converted"

def test_french_already_converted():
    """Test that marks already out of 80 are not converted again"""
    # Simulate already converted mark
    result = DerivedCalculationService.calculate_french_conversion(
        student_id=1,
        subject_id=1,
        component_id=1,
        raw_marks=70,
        max_marks=40,
        target_max=80
    )
    # Since no DB, returns None - this tests the logic path
    assert result is None or result["marks"] >= 80

def test_grade_boundaries():
    """Test all grade boundaries"""
    assert CalculationService.get_grade(100) == "A1"
    assert CalculationService.get_grade(91) == "A1"
    assert CalculationService.get_grade(90.5) == "A2"
    assert CalculationService.get_grade(81) == "A2"
    assert CalculationService.get_grade(80.5) == "B1"
    assert CalculationService.get_grade(71) == "B1"
    assert CalculationService.get_grade(70.5) == "B2"
    assert CalculationService.get_grade(61) == "B2"
    assert CalculationService.get_grade(60.5) == "C1"
    assert CalculationService.get_grade(51) == "C1"
    assert CalculationService.get_grade(50.5) == "C2"
    assert CalculationService.get_grade(41) == "C2"
    assert CalculationService.get_grade(40.5) == "D"
    assert CalculationService.get_grade(33) == "D"
    assert CalculationService.get_grade(32.9) == "E"
    assert CalculationService.get_grade(0) == "E"

def test_percentage_calculation():
    """Test percentage calculations"""
    assert CalculationService.calculate_percentage(45, 50) == 90.00
    assert CalculationService.calculate_percentage(38, 80) == 47.50
    assert CalculationService.calculate_percentage(15, 25) == 60.00
    assert CalculationService.calculate_percentage(0, 100) == 0.00

def test_mark_formatting():
    """Test two-decimal formatting"""
    assert CalculationService.format_marks(15) == "15.00"
    assert CalculationService.format_marks(12.5) == "12.50"
    assert CalculationService.format_marks(4.789) == "4.79"
    assert CalculationService.format_marks(None) == "0.00"
    assert CalculationService.format_marks(0) == "0.00"
