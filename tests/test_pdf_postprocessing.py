from ymprint.config.pdf_postprocessing import fill_forms_and_bake
import pytest
import pymupdf
import pathlib
import io

TEST_DATA = pathlib.Path(__file__).parent / "test-data"

def test_fill_forms_and_bake():
    vars = {
        "report_number": "123",
        "project_number": 1234,
        "project_name": "Current Project",
        "engineer": "Structural Python",
        "date": "2026-06-15",
        "time": "13:00",
        "region": "Level 1 slab"
    }
    bg = pymupdf.open(TEST_DATA / "background_first_page.pdf")
    bg_data = io.BytesIO()
    bg.save(bg_data)
    bg_data.seek(0)
    filled_data = fill_forms_and_bake(vars, {"first": bg_data, "remaining": None})
    filled = pymupdf.open(stream=filled_data['first'])
    filled.save(TEST_DATA / "filled_forms.pdf")
    assert False
