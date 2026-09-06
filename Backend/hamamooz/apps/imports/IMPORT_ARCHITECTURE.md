# Flexible Import Architecture

## Goals

- Accept school Excel files with different ordering and optional sheets.
- Detect fields by semantic headers instead of fixed column positions.
- Store assessment periods dynamically.
- Link student photos by national code.

## Import flow

Upload Excel/ZIP

-> Analyze workbook structure

-> Validate entities and indicators

-> Preview warnings/errors

-> Confirm import

-> Persist data

## Assessment periods

Periods are data, not code. A workbook can contain:

- monthly periods
- summer periods
- exam periods
- custom school periods

## Photos

Photo filename without extension is the national code.
