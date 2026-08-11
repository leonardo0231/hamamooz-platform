from .academic_drop import AcademicDropRule
from .attendance_risk import HighUnexcusedAbsenceRule
from .discipline_repeat import DisciplineRepeatRule
from .missing_teacher_scores import MissingTeacherScoresRule
from .multi_subject_drop import MultiSubjectDropRule
from .peer_performance_drop import PeerPerformanceDropRule
from .performance_volatility import PerformanceVolatilityRule

RULES = (
    AcademicDropRule(),
    MultiSubjectDropRule(),
    HighUnexcusedAbsenceRule(),
    DisciplineRepeatRule(),
    PerformanceVolatilityRule(),
    PeerPerformanceDropRule(),
    MissingTeacherScoresRule(),
)

RULE_BY_KEY = {(rule.code, rule.version): rule for rule in RULES}
