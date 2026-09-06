# Dynamic Import Refactor - Phase 0 Baseline Report

## Branch

`feature/dynamic-import-system`

## Scope

Baseline analysis before implementation of the dynamic import, assessment period, student photo and report export refactor.

## Repository baseline

Repository structure currently contains:

- Backend
- Frontend
- contracts
- docs
- scripts
- output/report related folders

The backend is a Django based application with Django REST components. Existing dependencies include Excel/PDF related tooling such as openpyxl, xlrd, WeasyPrint and docxtpl.

## Current architecture findings

### Backend

- Django modular application structure.
- Import related functionality already exists under imports module.
- Existing Excel processing uses openpyxl based workflows.
- Existing evaluation/report functionality is separated into dedicated modules.

### Frontend

- Separate frontend application exists.
- Import workflow UI requires later replacement with a multi-step Import Center.

## Baseline risks identified

1. Existing import behavior may depend on current workbook structure.
2. Evaluation data model must be separated from fixed monthly assumptions.
3. Indicator discovery must become data driven.
4. Existing reports must be preserved during migration.

## Phase 0 completion

Completed:

- Created refactor branch.
- Recorded baseline architecture.
- Prepared migration direction.

Next phase:

Phase 1 - introduce dynamic import engine architecture without breaking current import flow.
