from datetime import date
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import fitz
from PIL import Image
from reportlab.pdfgen.canvas import Canvas

from app.models.domain import DocumentStatus, DocumentType, IssuedDocument
from app.services.documents.lifecycle import DocumentLifecycleError, generate_on_first_download
from app.services.documents.rendering import _insert_text, render_certificate


def _blank_template() -> bytes:
    output = BytesIO()
    canvas = Canvas(output, pagesize=(595, 842))
    canvas.drawString(40, 800, "EMC certificate template")
    canvas.save()
    return output.getvalue()


def _field(name: str, x: int, y: int, width: int = 280, height: int = 30) -> SimpleNamespace:
    return SimpleNamespace(field_name=name, page_number=1, x=x, y=y, width=width, height=height)


class _Storage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.uploads = 0

    def upload(self, key: str, content: bytes, content_type: str) -> None:
        assert content_type == "application/pdf"
        self.objects[key] = content
        self.uploads += 1

    def download(self, key: str) -> bytes:
        return self.objects[key]


class _Db:
    def __init__(self) -> None:
        self.events = []

    def add(self, item: object) -> None:
        self.events.append(item)


def _document(status: DocumentStatus = DocumentStatus.VALID) -> IssuedDocument:
    return IssuedDocument(
        id=uuid4(),
        student_id=uuid4(),
        document_type=DocumentType.ACTIVITY_CERTIFICATE,
        issue_date=date(2026, 9, 23),
        verification_id="EMC-TEST123",
        status=status,
        version=1,
    )


def test_first_download_generates_caches_and_audits_document() -> None:
    db = _Db()
    storage = _Storage()
    document = _document()
    fields = [
        _field("student_name", 150, 160),
        _field("roll_number", 150, 210),
        _field("activity_name", 150, 260),
        _field("activity_date", 150, 310),
        _field("qr_code", 450, 650, 90, 90),
    ]
    values = {
        "student_name": "Ayesha Khan",
        "roll_number": "FA21-BCS-001",
        "activity_name": "Welcome Week",
        "activity_date": date(2026, 9, 1),
    }

    first = generate_on_first_download(
        db,
        document=document,
        template_pdf=_blank_template(),
        template_fields=fields,
        values=values,
        storage=storage,
        public_base_url="https://portal.example.edu",
    )
    second = generate_on_first_download(
        db,
        document=document,
        template_pdf=b"not consulted after caching",
        template_fields=[],
        values={},
        storage=storage,
        public_base_url="https://portal.example.edu",
    )

    assert first.startswith(b"%PDF")
    assert second == first
    assert document.storage_key == f"issued-documents/{document.id}/v1.pdf"
    assert len(document.sha256 or "") == 64
    assert storage.uploads == 1
    assert [event.event_type for event in db.events] == ["DOCUMENT_GENERATED"]
    rendered = fitz.open(stream=first, filetype="pdf")
    assert "Ayesha Khan" in rendered[0].get_text()


def test_invalid_document_is_never_generated() -> None:
    with __import__("pytest").raises(DocumentLifecycleError, match="Only valid"):
        generate_on_first_download(
            _Db(),
            document=_document(DocumentStatus.REVOKED),
            template_pdf=_blank_template(),
            template_fields=[],
            values={},
            storage=_Storage(),
            public_base_url="https://portal.example.edu",
        )


def test_preview_watermark_is_rendered_without_creating_a_document_record() -> None:
    output = render_certificate(
        _blank_template(),
        [
            _field("student_name", 150, 160),
            _field("roll_number", 150, 210),
            _field("activity_name", 150, 260),
            _field("activity_date", 150, 310),
        ],
        {
            "student_name": "Ayesha Khan",
            "roll_number": "FA21-BCS-001",
            "activity_name": "Welcome Week",
            "activity_date": date(2026, 9, 1),
        },
        verification_url="https://portal.example.edu/verify/PREVIEW",
        watermark="PREVIEW",
    )
    rendered = fitz.open(stream=output, filetype="pdf")
    assert "PREVIEW" in rendered[0].get_text()


def test_renderer_places_configured_signature_image() -> None:
    signature = BytesIO()
    Image.new("RGBA", (80, 30), (0, 0, 0, 255)).save(signature, format="PNG")
    output = render_certificate(
        _blank_template(),
        [
            _field("student_name", 150, 160),
            _field("roll_number", 150, 210),
            _field("activity_name", 150, 260),
            _field("activity_date", 150, 310),
            _field("signature_president", 100, 500, 100, 40),
        ],
        {
            "student_name": "Ayesha Khan",
            "roll_number": "FA21-BCS-001",
            "activity_name": "Welcome Week",
            "activity_date": date(2026, 9, 1),
        },
        verification_url="https://portal.example.edu/verify/EMC-TEST123",
        image_values={"signature_president": signature.getvalue()},
    )
    rendered = fitz.open(stream=output, filetype="pdf")
    assert rendered[0].get_images(full=True)


def test_renderer_honors_configured_bundled_font_and_color() -> None:
    field = _field("student_name", 150, 160)
    field.font_family = "cour"
    field.font_size = 14
    field.text_color = "#1E3A8A"
    output = render_certificate(
        _blank_template(),
        [
            field,
            _field("roll_number", 150, 210),
            _field("activity_name", 150, 260),
            _field("activity_date", 150, 310),
        ],
        {
            "student_name": "Ayesha Khan",
            "roll_number": "FA21-BCS-001",
            "activity_name": "Welcome Week",
            "activity_date": date(2026, 9, 1),
        },
        verification_url="https://portal.example.edu/verify/EMC-TEST123",
    )
    rendered = fitz.open(stream=output, filetype="pdf")
    assert "Ayesha Khan" in rendered[0].get_text()


def test_renderer_registers_uploaded_ttf_font_without_host_font_dependency(monkeypatch) -> None:
    class _CustomFont:
        def __init__(self, *, fontbuffer: bytes) -> None:
            assert fontbuffer == b"test-font-bytes"

        def text_length(self, text: str, fontsize: float) -> float:
            return len(text) * fontsize

    class _Page:
        def __init__(self) -> None:
            self.registered_fonts: list[dict[str, object]] = []
            self.inserted_text: list[dict[str, object]] = []

        def insert_font(self, **kwargs: object) -> None:
            self.registered_fonts.append(kwargs)

        def insert_text(self, point: fitz.Point, value: str, **kwargs: object) -> None:
            self.inserted_text.append({"point": point, "value": value, **kwargs})

    monkeypatch.setattr("app.services.documents.rendering.fitz.Font", _CustomFont)
    custom_font_key = "templates/example/fonts/adwaita.ttf"
    field = _field("student_name", 150, 160)
    field.font_family = "custom"
    field.custom_font_storage_key = custom_font_key
    page = _Page()

    _insert_text(page, field, "Ayesha Khan", {custom_font_key: b"test-font-bytes"})

    assert page.registered_fonts[0]["fontbuffer"] == b"test-font-bytes"
    assert str(page.registered_fonts[0]["fontname"]).startswith("EMCF")
    assert page.inserted_text[0]["value"] == "Ayesha Khan"
    assert page.inserted_text[0]["fontname"] == page.registered_fonts[0]["fontname"]
