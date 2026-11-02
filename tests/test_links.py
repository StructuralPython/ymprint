"""Links survive the background overlay, and `_img` can be a link."""
import pathlib
import textwrap

import pymupdf
import pytest

from ymprint import report_reader  # noqa: F401  (registers blocks)
from ymprint.blocks import convert_blocks
from ymprint.blocks.image_block import LinkedImage, resolve_link
from ymprint.config.config_loaders import load_report_config
from ymprint.config.pdf_postprocessing import copy_links
from ymprint.context_builder import build_context
from ymprint.errors import BlockError
from ymprint.report_reader import load_report

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
IMAGE = REPO_ROOT / "ymprintlogosmall.png"


def render(tmp_path: pathlib.Path, source: str) -> pymupdf.Document:
    src = tmp_path / "doc.yml"
    src.write_text(textwrap.dedent(source))
    dest = tmp_path / "doc.pdf"
    load_report(src, dest, None)
    return pymupdf.open(dest)


def make_background(path: pathlib.Path, size=(960, 540)) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=size[0], height=size[1])
    page.draw_rect(page.rect, fill=(0.9, 0.9, 1), color=None)
    doc.save(path)


@pytest.fixture
def ctx():
    styles, tbl, doc = load_report_config()
    return build_context(
        {}, styles, doc, tbl, {},
        REPO_ROOT / "report.yml", REPO_ROOT / "report.pdf", None,
    )


# --- resolve_link ---------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "https://structuralpython.com",
    "http://example.com/a?b=c",
    "mailto:connor@structuralpython.com",
    "file:///C:/Users/me/video.mp4",
])
def test_urls_are_kept_as_they_are(url, tmp_path):
    assert resolve_link(url, tmp_path) == url


def test_relative_path_resolves_against_the_document_folder(tmp_path):
    assert resolve_link("videos/clip.mp4", tmp_path) == (tmp_path / "videos" / "clip.mp4").resolve().as_uri()


def test_absolute_path_becomes_a_file_url(tmp_path):
    video = tmp_path / "elsewhere" / "clip.mp4"
    assert resolve_link(str(video), REPO_ROOT) == video.resolve().as_uri()


def test_link_target_need_not_exist(tmp_path):
    assert resolve_link("not-here.mp4", tmp_path).startswith("file:")


def test_windows_drive_letter_is_a_path_not_a_url_scheme(tmp_path):
    assert resolve_link("C:/Videos/clip.mp4", tmp_path).startswith("file:")


# --- the _img block ---------------------------------------------------------------

def test_img_without_link_is_a_plain_image(ctx):
    table = convert_blocks("_img", {"source": str(IMAGE)}, ctx)[0]
    assert not isinstance(table._cellvalues[0][0], LinkedImage)


def test_img_with_link_is_a_linked_image(ctx):
    table = convert_blocks("_img", {"source": str(IMAGE), "link": "https://example.com"}, ctx)[0]
    image = table._cellvalues[0][0]
    assert isinstance(image, LinkedImage)
    assert image.link == "https://example.com"


@pytest.mark.parametrize("bad", ["", "   ", 42, ["a.mp4"], {"url": "x"}])
def test_img_rejects_a_link_that_is_not_a_url_or_path(ctx, bad):
    with pytest.raises(BlockError, match="link"):
        convert_blocks("_img", {"source": str(IMAGE), "link": bad}, ctx)


# --- links in the rendered PDF ------------------------------------------------------

def _uri_links(page):
    return [l for l in page.get_links() if l["kind"] == pymupdf.LINK_URI]


def test_linked_image_is_clickable_over_the_image(tmp_path):
    pdf = render(tmp_path, f"""
        Report:
          - _img:
              source: {IMAGE}
              link: https://structuralpython.com
    """)
    page = pdf[0]
    (link,) = _uri_links(page)
    assert link["uri"] == "https://structuralpython.com"
    (image_rect,) = page.get_image_rects(page.get_images()[0][0])
    assert link["from"].intersect(image_rect).get_area() == pytest.approx(image_rect.get_area(), rel=0.01)


def test_markdown_links_in_text_survive(tmp_path):
    pdf = render(tmp_path, """
        Report:
          - "Read the [docs](https://ymprint.structuralpython.com) first."
    """)
    (link,) = _uri_links(pdf[0])
    assert link["uri"] == "https://ymprint.structuralpython.com"


def test_links_survive_a_background_template(tmp_path):
    make_background(tmp_path / "bg.pdf")
    pdf = render(tmp_path, f"""
        _doc:
          page-size: [960, 540]
          slides: true
          templates:
            slide:
              margins: {{top: 54, left: 72, right: 72, bottom: 54}}
              background: {{filepath: bg.pdf, relative-to: source}}
        Watch this:
          - _img:
              source: {IMAGE}
              link: https://example.com/video
          - "[Or read this](https://example.com/text)"
    """)
    uris = sorted(l["uri"] for l in _uri_links(pdf[0]))
    assert uris == ["https://example.com/text", "https://example.com/video"]


def test_local_video_link_opens_the_file(tmp_path):
    pdf = render(tmp_path, f"""
        _doc:
          page-size: [960, 540]
          slides: true
        The video:
          - _img:
              source: {IMAGE}
              link: videos/clip.mp4
    """)
    (link,) = pdf[0].get_links()
    target = link.get("file") or link.get("uri")
    assert pathlib.Path(target.removeprefix("file://")).as_posix().endswith("videos/clip.mp4")
    assert str(tmp_path.resolve().as_posix()) in pathlib.Path(target.removeprefix("file://")).as_posix()


def test_links_are_kept_on_every_slide(tmp_path):
    pdf = render(tmp_path, f"""
        _doc:
          page-size: [960, 540]
          slides: true
        One:
          - "[a](https://example.com/1)"
        Two:
          - "[b](https://example.com/2)"
    """)
    assert [[l["uri"] for l in _uri_links(p)] for p in pdf] == [
        ["https://example.com/1"], ["https://example.com/2"],
    ]


# --- copy_links -------------------------------------------------------------------

def test_copy_links_keeps_a_link_to_a_later_page():
    source = pymupdf.open()
    for _ in range(3):
        source.new_page(width=200, height=200)
    source[0].insert_link({"kind": pymupdf.LINK_GOTO, "from": pymupdf.Rect(10, 10, 50, 30),
                           "page": 2, "to": pymupdf.Point(0, 0)})
    output = pymupdf.open()
    for _ in range(3):
        output.new_page(width=200, height=200)
    copy_links(source, output)
    (link,) = output[0].get_links()
    assert link["kind"] == pymupdf.LINK_GOTO and link["page"] == 2
    assert link["from"] == pymupdf.Rect(10, 10, 50, 30)
