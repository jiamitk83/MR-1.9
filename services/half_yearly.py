from dataclasses import dataclass
from decimal import Decimal

from services.calculation import CalculationService
from services.derived_calculations import DerivedCalculationService


@dataclass(frozen=True)
class ComponentTemplate:
    name: str
    code: str
    maximum: Decimal
    is_derived: bool = False
    entry_maximum: Decimal | None = None


CORE_COMPONENTS = (
    ComponentTemplate("Periodic Test 1", "PT1", Decimal("5"), True),
    ComponentTemplate("Multiple Assessment", "MA", Decimal("5")),
    ComponentTemplate("Subject Enrichment", "ENR", Decimal("5")),
    ComponentTemplate("Portfolio", "PF", Decimal("5")),
    ComponentTemplate("Written Examination", "WE", Decimal("80")),
)
COMPUTER_COMPONENTS = (
    ComponentTemplate("Periodic Test 1", "PT1", Decimal("5"), True),
    ComponentTemplate("Practical", "PRAC", Decimal("30")),
    ComponentTemplate("Theory", "THEORY", Decimal("50")),
    ComponentTemplate("Multiple Assessment", "MA", Decimal("5")),
    ComponentTemplate("Subject Enrichment", "ENR", Decimal("5")),
    ComponentTemplate("Portfolio", "PF", Decimal("5")),
)
FRENCH_COMPONENTS = (
    ComponentTemplate("Periodic Test 1", "PT1", Decimal("5"), True),
    ComponentTemplate("Written Examination", "WE", Decimal("80"), entry_maximum=Decimal("40")),
    ComponentTemplate("Multiple Assessment", "MA", Decimal("5")),
    ComponentTemplate("Subject Enrichment", "ENR", Decimal("5")),
    ComponentTemplate("Portfolio", "PF", Decimal("5")),
)
CORE_SUBJECTS = frozenset({"ENGLISH", "MATHEMATICS", "MATH", "HINDI", "SCIENCE", "SOCIAL SCIENCE", "SOCIAL STUDY", "SST"})
GRADE_SUBJECTS = frozenset({"GK", "GENERAL KNOWLEDGE"})
LEGACY_COMPONENT_LABELS = {
    "MA": {"MA", "MULTIPLE ASSESSMENT"},
    "ENR": {"ENR", "SE", "SUBJECT ENRICHMENT", "SUBJECT ENRICHMENT SE"},
    "PF": {"PF", "PORTFOLIO"},
    "WE": {"WE", "WRITTEN", "WRITTEN 80", "WRITTEN EXAMINATION"},
    "PRAC": {"PRAC", "PRACTICAL"},
    "THEORY": {"THEORY"},
}


class HalfYearlyService:
    """Subject-specific Half Yearly templates and authoritative result calculations."""

    def __init__(self, derived_service=None):
        self.derived_service = derived_service or DerivedCalculationService()

    @staticmethod
    def _identity(subject):
        code = (subject.code or "").strip().upper()
        name = (subject.name or "").strip().upper()
        return code, name

    @classmethod
    def is_grade_only(cls, subject):
        code, name = cls._identity(subject)
        return code in GRADE_SUBJECTS or name in GRADE_SUBJECTS

    @classmethod
    def template_for_subject(cls, subject, french_entry_maximum=Decimal("40")):
        code, name = cls._identity(subject)
        if code in GRADE_SUBJECTS or name in GRADE_SUBJECTS:
            return ()
        if code == "FRENCH" or name == "FRENCH":
            entry_maximum = Decimal(str(french_entry_maximum))
            if entry_maximum not in (Decimal("40"), Decimal("80")):
                raise ValueError("French written entry maximum must be either 40 or 80.")
            components = list(FRENCH_COMPONENTS)
            components[1] = ComponentTemplate(
                "Written Examination",
                "WE",
                Decimal("80"),
                entry_maximum=entry_maximum,
            )
            return tuple(components)
        if code == "COMPUTER" or name == "COMPUTER":
            return COMPUTER_COMPONENTS
        if code in CORE_SUBJECTS or name in CORE_SUBJECTS:
            return CORE_COMPONENTS
        return None

    @classmethod
    def validate_components(cls, subject, components):
        components = tuple(components)
        if cls.is_grade_only(subject):
            if components:
                raise ValueError("Grade-only subjects must not have numeric components.")
            return Decimal("0")
        if not components:
            raise ValueError("Configure Half Yearly components for this subject.")
        codes = [component.code.strip().upper() for component in components if component.code]
        if len(codes) != len(components):
            raise ValueError("Every numeric component must have a code.")
        if len(set(codes)) != len(codes):
            raise ValueError("Component codes must be unique within this subject.")
        maximum_for = lambda item: getattr(item, "max_marks", getattr(item, "maximum", None))
        entry_max_for = lambda item: getattr(item, "entry_max", getattr(item, "entry_maximum", None))
        if sum((Decimal(str(maximum_for(component))) for component in components), Decimal("0")) != Decimal("100"):
            raise ValueError("Numeric Half Yearly component maxima must total exactly 100.")
        pt1 = [component for component in components if component.code.strip().upper() == "PT1"]
        if len(pt1) != 1 or not pt1[0].is_derived or Decimal(str(maximum_for(pt1[0]))) != Decimal("5"):
            raise ValueError("PT1 / 5 must be configured exactly once as a derived component.")
        for component in components:
            maximum = Decimal(str(maximum_for(component)))
            if maximum <= 0:
                raise ValueError("Numeric component maxima must be positive.")
            entry_max_value = entry_max_for(component)
            if entry_max_value is not None:
                entry_max = Decimal(str(entry_max_value))
                if entry_max <= 0 or entry_max > maximum:
                    raise ValueError("A component entry maximum must be positive and no greater than its final maximum.")
        if any(component.code.strip().upper() == "WE" for component in components):
            written = next(component for component in components if component.code.strip().upper() == "WE")
            if Decimal(str(maximum_for(written))) != Decimal("80"):
                raise ValueError("Written Examination must have a final maximum of 80.")
            written_entry_max = entry_max_for(written)
            subject_code, subject_name = cls._identity(subject)
            if (
                subject_code == "FRENCH" or subject_name == "FRENCH"
            ) and written_entry_max not in (
                40, 80, Decimal("40"), Decimal("80")
            ):
                raise ValueError("French Written Examination entry maximum must be 40 or 80.")
        return Decimal("100")

    def calculate_pt1(self, student_id, subject_id, session_id):
        return self.derived_service.calculate_pt1_derived(
            student_id,
            subject_id,
            session_id,
        )

    @classmethod
    def map_legacy_component_marks(
        cls, subject_components, legacy_components, marks_by_component
    ):
        """Project unambiguous generic legacy marks without changing stored rows."""
        effective = {}
        for component in subject_components:
            mark = marks_by_component.get(component.id)
            if mark is not None or component.is_derived:
                effective[component.id] = mark
                continue
            code = (component.code or "").strip().upper()
            accepted_labels = LEGACY_COMPONENT_LABELS.get(code, set())
            matching_components = [
                legacy for legacy in legacy_components
                if not legacy.is_derived
                and (
                    (legacy.code or "").strip().upper() in accepted_labels
                    or (legacy.name or "").strip().upper() in accepted_labels
                )
            ]
            if len(matching_components) > 1:
                matching_marks = [
                    marks_by_component[legacy.id]
                    for legacy in matching_components
                    if legacy.id in marks_by_component
                ]
                if len(matching_marks) > 1:
                    raise ValueError(
                        f"Legacy marks for {component.name} are ambiguous; "
                        "review the generic examination components."
                    )
            else:
                matching_marks = [
                    marks_by_component[legacy.id]
                    for legacy in matching_components
                    if legacy.id in marks_by_component
                ]
            effective[component.id] = matching_marks[0] if matching_marks else None
        return effective

    def calculate_subject_result(self, student, subject, session_id, components, marks_by_component):
        if self.is_grade_only(subject):
            grade = marks_by_component.get("grade")
            return {
                "status": "Grade only" if grade else "Pending",
                "grade": grade,
                "grade_only": True,
                "total": None,
                "maximum": None,
                "percentage": None,
                "components": [],
                "missing_components": [],
            }

        if not components:
            return {
                "status": "Not Configured",
                "grade": None,
                "grade_only": False,
                "total": None,
                "maximum": None,
                "percentage": None,
                "components": [],
                "missing_components": [],
                "absent_components": [],
            }

        self.validate_components(subject, components)
        rows = []
        total = Decimal("0")
        missing = []
        absent = []
        for component in components:
            code = (component.code or "").strip().upper()
            maximum = Decimal(str(component.max_marks))
            if code == "PT1" and component.is_derived:
                source = self.calculate_pt1(student.id, subject.id, session_id)
                status = source["status"]
                obtained = source["marks"] if status == "calculated" else None
                if obtained is not None and (
                    not Decimal("0") <= Decimal(str(obtained)) <= maximum
                ):
                    raise ValueError("The derived PT1 mark is outside its configured maximum.")
            else:
                mark = marks_by_component.get(component.id)
                if mark is None or (mark.marks_obtained is None and not mark.is_absent):
                    status, obtained = "pending", None
                elif mark.is_absent:
                    status, obtained = "absent", None
                else:
                    status, obtained = "entered", Decimal(str(mark.marks_obtained))
                    entry_max = getattr(component, "entry_max", None)
                    entry_max = Decimal(str(entry_max or maximum))
                    if not obtained.is_finite() or obtained < 0 or obtained > entry_max:
                        raise ValueError(
                            f"Saved marks for {component.name} exceed the configured entry maximum."
                        )
                    if code == "WE" and entry_max is not None:
                        if entry_max != maximum:
                            conversion = self.derived_service.calculate_french_conversion(
                                raw_marks=obtained,
                                max_marks=entry_max,
                                target_max=maximum,
                            )
                            obtained = conversion["marks"]
            if status == "pending":
                missing.append(component.name)
            elif status == "absent":
                absent.append(component.name)
            elif obtained is not None:
                total += Decimal(str(obtained))
            rows.append({
                "component_id": component.id,
                "name": component.name,
                "code": code,
                "maximum": maximum,
                "entry_maximum": getattr(component, "entry_max", None) or maximum,
                "marks": obtained,
                "status": status,
                "is_derived": component.is_derived,
            })

        if missing:
            status, percentage, grade, final_total = "Pending", None, None, None
        elif absent:
            status, percentage, grade, final_total = "Absent", None, None, None
        else:
            status = "Complete"
            percentage = CalculationService.calculate_percentage(total, Decimal("100"))
            if percentage > 100:
                raise ValueError("A Half Yearly result cannot exceed 100 percent.")
            grade = CalculationService.get_grade(percentage)
            final_total = total.quantize(Decimal("0.01"))
        return {
            "status": status,
            "grade": grade,
            "grade_only": False,
            "total": final_total,
            "maximum": Decimal("100") if status == "Complete" else None,
            "percentage": percentage,
            "components": rows,
            "missing_components": missing,
            "absent_components": absent,
        }

    @staticmethod
    def format_marks(value):
        if value is None:
            return "—"
        return CalculationService.format_marks(value)
