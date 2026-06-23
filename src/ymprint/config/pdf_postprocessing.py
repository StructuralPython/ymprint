import io
import pathlib
from typing import Optional

import pymupdf as mu

def overlay_pdf_background(
    document_path: pathlib.Path | io.BytesIO,
    pdf_background_streams: dict[str, io.BytesIO | None],
    destination_path: pathlib.Path | io.BytesIO,
    context: dict,
):
    """
    Overlays the pages from document_path onto the pages from 
    pdf_background_path and saves the new file to destination_path.
    If first_page_background_path is provided, then that background
    will be used for the first page and all other pages will be overlayed
    onto pdf_background_path.

    If pdf_background_path is a PDF file with multiple pages, each page
    in 'document_path' will be overlayed onto each page of 'pdf_background_path'
    in sequence. If 'document_path' has more pages than 'pdf_background_path',
    then the remaining pages of 'document_path' will not have a pdf background
    applied. If 'pdf_background_path' has more pages than 'document_path', then
    the final document will have the same number of pages as 'document_path' and
    the remaining un-overlayed pages from 'pdf_background_path' will remain
    unused in the final document.
    """
    first_data = pdf_background_streams['first']
    remaining_data = pdf_background_streams['remaining']
    page_dims = context['doctemplate']['ymprint'].page_dims
    page_width, page_height = page_dims
    first_bg = None
    if first_data is not None:
        first_bg = mu.open(stream=pdf_background_streams['first'])
    remaining_bg = None
    if remaining_data is not None:
        remaining_bg = mu.open(stream=pdf_background_streams['remaining'])
    document = mu.open(stream=document_path)
    output = mu.open()
    for i in range(document.page_count):
        document_page = document.load_page(i)
        document_page.wrap_contents()
        out_page = output.new_page(width=page_width, height=page_height)
        if i == 0 and first_bg is not None:
            first_bg_page = first_bg.load_page(0)
            first_bg_page.wrap_contents()
            out_page.show_pdf_page(first_bg_page.rect, first_bg, pno=0)
            out_page.show_pdf_page(document_page.rect, document, pno=i)
            continue
        if remaining_bg is not None:
            if remaining_bg.page_count == 1:
                background_page = remaining_bg.load_page(0)
                background_page.wrap_contents()
                background_page_num = 0
            else:
                try:
                    background_page = remaining_bg.load_page(i)
                    background_page.wrap_contents()
                    background_page_num = i
                except IndexError:
                    background_page = None
            out_page.show_pdf_page(background_page.rect, remaining_bg, pno=background_page_num)
        else:
            out_page.show_pdf_page(document_page.rect, document, pno=i)
    output.save(destination_path)

        

def fill_forms_and_bake(vars: dict, pdf_backgrounds: dict[str, io.BytesIO | None]) -> dict[str, io.BytesIO]:
    first_data = pdf_backgrounds['first']
    remaining_data = pdf_backgrounds['remaining']
    first_bg = remaining_bg = None
    if first_data is not None:
        first_bg = mu.open(stream=first_data)
    if remaining_bg is not None:
        remaining_bg = mu.open(stream=remaining_data)

    if first_bg is None and remaining_bg is None:
        return pdf_backgrounds
    docs = [first_bg, remaining_bg]
    out_docs = {}

    indexes = ['first', 'remaining']
    for idx, doc in enumerate(docs):
        if doc is None:

            out_docs[indexes[idx]] = None
            continue

        for page in doc:
            widget = page.first_widget
            while widget is not None:
                name = widget.field_name
                if name == "report_number":
                    widget.text_fontsize = 32
                widget_value = vars.get(name, None)
                # THIS IS TRICKY
                if widget_value is not None:
                    widget.field_value = str(widget_value)
                    widget.update()
                widget = widget.next


        doc.bake()
        doc_data = io.BytesIO()
        doc.save(filename=doc_data)
        doc_data.seek(0)
        out_docs[indexes[idx]] = doc_data
    return out_docs


def load_pdf_backgrounds(context: dict) -> dict[str, io.BytesIO | None]:
    source_path = pathlib.Path(context['source_path'])
    source_parent = source_path.parent
    first_page = context['doctemplate']['yaml']['_doc'].get('first-page')
    if isinstance(first_page, dict):
        first_page_background = first_page.get("background")
        if first_page_background is not None:
            first_page_background = source_parent / first_page_background
    else:
        first_page_background = None

    remaining = context['doctemplate']['yaml']['_doc'].get('background')
    first_page_pdf = remaining_pdf = None
    first_page_data = remaining_page_data = None
    if first_page_background is not None:
        first_page_pdf = mu.open(first_page_background)
        first_page_data = io.BytesIO()
        first_page_pdf.save(first_page_data)
        first_page_data.seek(0)
    if remaining is not None:
        remaining_page_background = source_parent / remaining
        remaining_pdf = mu.open(remaining_page_background)
        remaining_page_data = io.BytesIO()
        remaining_pdf.save(remaining_page_data)
        remaining_page_data.seek(0)

    backgrounds = {
        "first": first_page_data,
        "remaining": remaining_page_data
    }
    return backgrounds