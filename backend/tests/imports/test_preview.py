from io import BytesIO

from openpyxl import Workbook

from app.services.imports import preview_students


class EmptyDatabase:
    def scalar(self, _query):
        return None


class ConflictingDatabase:
    class StudentRecord:
        full_name = "Different name"

    def scalar(self, _query):
        return self.StudentRecord()


def workbook(headers, rows):
    book = Workbook(); sheet = book.active; sheet.append(headers)
    for row in rows: sheet.append(row)
    output = BytesIO(); book.save(output); return output.getvalue()


def test_preview_recognizes_heading_aliases_and_duplicates():
    result = preview_students(EmptyDatabase(), workbook(["Roll No", "Student Name"], [["A1", "Ahmed"], ["A1", "Ahmed"]]))
    assert result["valid_rows"] == 1
    assert result["duplicate_rows"] == 1


def test_preview_requires_canonical_fields():
    try:
        preview_students(EmptyDatabase(), workbook(["Identifier"], [["A1"]]))
    except ValueError as error:
        assert "Roll Number" in str(error)
    else:
        raise AssertionError("Missing required headings should fail")


def test_preview_marks_existing_name_difference_as_conflict():
    result = preview_students(ConflictingDatabase(), workbook(["Roll Number", "Full Name"], [["A1", "Ahmed"]]))
    assert result["conflicting_rows"] == 1
    assert result["rows"][0]["outcome"] == "conflict"
