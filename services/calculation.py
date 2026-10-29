from decimal import Decimal, ROUND_HALF_UP

class CalculationService:
    @staticmethod
    def format_marks(value):
        """Formats marks to exactly two decimal places as a string."""
        if value is None:
            return "0.00"
        return "{:.2f}".format(Decimal(str(value)).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP))

    @staticmethod
    def calculate_percentage(obtained, total_max):
        """Calculates percentage given obtained and max marks."""
        if not total_max or total_max == 0:
            return Decimal("0.00")
        percentage = (Decimal(str(obtained)) / Decimal(str(total_max))) * 100
        return percentage.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

    @staticmethod
    def get_grade(percentage):
        """Returns the grade based on the percentage."""
        p = float(percentage)
        if p >= 91: return "A1"
        if p >= 81: return "A2"
        if p >= 71: return "B1"
        if p >= 61: return "B2"
        if p >= 51: return "C1"
        if p >= 41: return "C2"
        if p >= 33: return "D"
        return "E"

    @staticmethod
    def derive_pt_marks(obtained, original_max):
        """Derives PT marks out of 5 (e.g. for Half Yearly/Annual)."""
        if not original_max or original_max == 0:
            return Decimal("0.00")
        derived = (Decimal(str(obtained)) / Decimal(str(original_max))) * 5
        return derived.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
