from decimal import Decimal, ROUND_HALF_UP

class CalculationService:
    GRADE_ONLY_SUBJECT_CODES = frozenset({"GK"})
    GRADE_ONLY_SUBJECT_NAMES = frozenset({"GENERAL KNOWLEDGE", "GUIDANCE", "CIVICS"})

    GRADE_BOUNDARIES = (
        (Decimal("91"), "A1"),
        (Decimal("81"), "A2"),
        (Decimal("71"), "B1"),
        (Decimal("61"), "B2"),
        (Decimal("51"), "C1"),
        (Decimal("41"), "C2"),
        (Decimal("33"), "D"),
    )

    @staticmethod
    def format_marks(value):
        """Formats marks to exactly two decimal places as a string."""
        if value is None:
            return "0.00"
        return "{:.2f}".format(Decimal(str(value)).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP))

    @staticmethod
    def calculate_percentage(obtained, total_max):
        """Return the unrounded percentage; round only when formatting for display."""
        maximum = Decimal(str(total_max))
        if maximum <= 0:
            return Decimal("0")
        return (Decimal(str(obtained)) / maximum) * 100

    @staticmethod
    def get_grade(percentage):
        """Return a grade using the unrounded percentage."""
        value = Decimal(str(percentage))
        for boundary, grade in CalculationService.GRADE_BOUNDARIES:
            if value >= boundary:
                return grade
        return "E"

    @staticmethod
    def derive_pt_marks(obtained, original_max):
        """Derives PT marks out of 5 (e.g. for Half Yearly/Annual)."""
        if not original_max or original_max == 0:
            return Decimal("0.00")
        derived = (Decimal(str(obtained)) / Decimal(str(original_max))) * 5
        return derived.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

    @staticmethod
    def is_grade_only_subject(subject):
        """Identify configured grade-only subjects without fuzzy name matching."""
        code = (subject.code or "").strip().upper()
        name = (subject.name or "").strip().upper()
        return (
            code in CalculationService.GRADE_ONLY_SUBJECT_CODES
            or name in CalculationService.GRADE_ONLY_SUBJECT_NAMES
        )
