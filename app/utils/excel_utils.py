# app/utils/excel_utils.py
import openpyxl

MEMBER_COLUMNS = [
    "member_number",
    "organization_name",
    "organization_kana",
    "representative_name",
    "representative_kana",
    "postal_code",
    "address",
    "phone",
    "email",
]


def parse_tsv_text(text: str) -> list[dict]:
    """ExcelからコピーしたTSVテキストを会員データのリストに変換する"""
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        cells = line.split("\t")
        while len(cells) < len(MEMBER_COLUMNS):
            cells.append("")
        row = {col: cells[i].strip() for i, col in enumerate(MEMBER_COLUMNS)}
        if not row["organization_name"] and not row["representative_name"]:
            continue
        rows.append(row)
    return rows


def parse_excel_file(file_path: str, sheet_name: str | None = None,
                     header_row: int = 1) -> list[dict]:
    """Excelファイルを読み込んで会員データのリストに変換する"""
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active
    rows = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < header_row:
            continue
        cells = [str(c).strip() if c is not None else "" for c in row]
        while len(cells) < len(MEMBER_COLUMNS):
            cells.append("")
        data = {col: cells[j] for j, col in enumerate(MEMBER_COLUMNS)}
        if not data["organization_name"] and not data["representative_name"]:
            continue
        rows.append(data)
    wb.close()
    return rows
