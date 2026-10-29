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


def test_replace_destination_retries_while_locked(tmp_path, monkeypatch):
    from ymprint.config import pdf_postprocessing as pp
    staged, dest = tmp_path / "a.tmp.pdf", tmp_path / "a.pdf"
    staged.write_bytes(b"new")
    failures = [PermissionError(13, "locked")] * 2
    real_replace = pp.os.replace

    def flaky_replace(src, dst):
        if failures:
            raise failures.pop()
        real_replace(src, dst)

    def locked(src, dst):
        raise PermissionError(13, "locked")

    monkeypatch.setattr(pp.os, "replace", flaky_replace)
    monkeypatch.setattr(pp.shutil, "copyfile", locked)
    monkeypatch.setattr(pp, "LOCK_RETRY_DELAY", 0)
    pp.replace_destination(staged, dest, timeout=5)
    assert dest.read_bytes() == b"new" and not staged.exists()


def test_replace_destination_gives_up_and_cleans_up(tmp_path, monkeypatch):
    from ymprint.config import pdf_postprocessing as pp
    staged, dest = tmp_path / "a.tmp.pdf", tmp_path / "a.pdf"
    staged.write_bytes(b"new")
    dest.write_bytes(b"old")

    def locked(src, dst):
        raise PermissionError(13, "locked")

    monkeypatch.setattr(pp.os, "replace", locked)
    monkeypatch.setattr(pp.shutil, "copyfile", locked)
    with pytest.raises(pp.DestinationLockedError) as info:
        pp.replace_destination(staged, dest, timeout=0)
    assert info.value.path == dest
    assert dest.read_bytes() == b"old" and not staged.exists()


def test_replace_destination_overwrites_in_place_when_replace_is_refused(tmp_path, monkeypatch):
    # Okular on Windows: the open PDF can be written but not deleted or replaced.
    from ymprint.config import pdf_postprocessing as pp
    staged, dest = tmp_path / "a.tmp.pdf", tmp_path / "a.pdf"
    staged.write_bytes(b"new")
    dest.write_bytes(b"old")

    def locked(src, dst):
        raise PermissionError(13, "locked")

    monkeypatch.setattr(pp.os, "replace", locked)
    pp.replace_destination(staged, dest, timeout=0)
    assert dest.read_bytes() == b"new" and not staged.exists()
