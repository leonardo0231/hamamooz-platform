# MVP ERD

The authoritative enrollment relationship is:

```mermaid
erDiagram
    ORGANIZATION ||--o{ SCHOOL : contains
    USER ||--o{ SCHOOL_MEMBERSHIP : has
    SCHOOL ||--o{ SCHOOL_MEMBERSHIP : grants
    SCHOOL_MEMBERSHIP ||--o{ ROLE_ASSIGNMENT : receives
    STUDENT ||--o{ ENROLLMENT : has_history
    SCHOOL ||--o{ ENROLLMENT : enrolls
    ACADEMIC_YEAR ||--o{ ENROLLMENT : groups
    GRADE_LEVEL ||--o{ ENROLLMENT : places
    CLASS_SECTION ||--o{ ENROLLMENT : assigns
    STUDENT ||--o{ STUDENT_GUARDIAN : links
    GUARDIAN ||--o{ STUDENT_GUARDIAN : links
    GRADE_LEVEL ||--o{ GRADE_SUBJECT : defines
    SUBJECT ||--o{ GRADE_SUBJECT : maps
    CLASS_SECTION ||--o{ COURSE_OFFERING : offers
    GRADE_SUBJECT ||--o{ COURSE_OFFERING : realizes
    COURSE_OFFERING ||--o{ TEACHER_ASSIGNMENT : staffed_by
    USER ||--o{ TEACHER_ASSIGNMENT : teaches
    COURSE_OFFERING ||--o{ ASSESSMENT : contains
    ASSESSMENT ||--o{ SCORE : records
    ENROLLMENT ||--o{ SCORE : receives
    SCORE ||--o{ SCORE_CHANGE_LOG : changes
    CALCULATION_FORMULA ||--o{ CALCULATION_RESULT : produces
    IMPORT_JOB ||--o{ IMPORT_ROW_ERROR : reports
    REPORT_TEMPLATE ||--o{ GENERATED_REPORT : renders
```

## Initial decisions

- Internal primary keys use `BigAutoField`; public opaque identifiers can be introduced per aggregate when API enumeration risk justifies them.
- `Student` has no permanent class or grade foreign key.
- Annual uniqueness and school consistency are enforced by database constraints and transactional services.
- Score values use `Decimal`, never binary floating point.
