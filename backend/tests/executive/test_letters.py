from types import SimpleNamespace

from app.services.executive.letters import leadership_fields_for_rendering


def test_leadership_recipient_field_moves_above_its_underline_and_grows() -> None:
    source = SimpleNamespace(field_name="student_name", x=200, y=168, width=280, height=18)

    rendered = leadership_fields_for_rendering([source])[0]

    assert rendered is not source
    assert rendered.y == 150
    assert rendered.height == 32
    assert rendered.font_size == 24
    assert source.y == 168
    assert source.height == 18
