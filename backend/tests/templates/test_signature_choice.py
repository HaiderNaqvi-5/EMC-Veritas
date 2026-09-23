import pytest

from app.services.templates.signature_choice import require_signature_choice


@pytest.mark.parametrize("choice", [None, "", "keep", "RETAIN"])
def test_signature_choice_requires_an_explicit_valid_value(choice: str | None) -> None:
    with pytest.raises(ValueError, match="Choose whether to retain or replace"):
        require_signature_choice(choice)


@pytest.mark.parametrize("choice", ["retain", "replace"])
def test_signature_choice_accepts_the_two_prd_values(choice: str) -> None:
    assert require_signature_choice(choice) == choice
