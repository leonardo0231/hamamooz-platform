from dataclasses import dataclass

from openpyxl import load_workbook


@dataclass
class WorkbookSchema:
    sheets: list[str]
    columns: dict[str, list[str]]


def analyze_workbook(file_object):
    workbook = load_workbook(file_object, read_only=True, data_only=True)
    try:
        sheets = list(workbook.sheetnames)
        columns = {}

        for sheet_name in sheets:
            sheet = workbook[sheet_name]
            first_row = next(sheet.iter_rows(values_only=True), ())
            columns[sheet_name] = [str(x).strip() for x in first_row if x is not None]

        return WorkbookSchema(sheets=sheets, columns=columns)
    finally:
        workbook.close()
