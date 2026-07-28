# ADR 0001: Modular Monolith

- Status: accepted
- Context: the product has many related transactional domains but does not yet justify distributed operational complexity.
- Decision: use one Django deployment with bounded apps and explicit service-layer boundaries.
- Consequence: simpler transactions and deployment now; extraction remains possible where module dependencies stay directional.
