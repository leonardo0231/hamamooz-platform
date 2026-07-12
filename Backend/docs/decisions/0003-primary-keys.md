# ADR 0003: Primary-Key Strategy

- Status: accepted
- Decision: use `BigAutoField` internally by default. Add opaque public identifiers only to aggregates that are exposed externally or need offline merge semantics.
- Rationale: avoids blanket UUID cost and complexity while preserving a path to non-enumerable public IDs.
