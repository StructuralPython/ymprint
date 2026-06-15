import io
import pathlib
from typing import Optional

import pymupdf as mu

def overlay_pdf_background(
    document_path: pathlib.Path | io.BytesIO,
    pdf_background_path: pathlib.Path,
    destination_path: pathlib.Path | io.BytesIO,
    first_page_background_path: Optional[pathlib.Path],
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

    document = mu.open(stream=document_path)
    background = mu.open(pdf_background_path)
    output = mu.open()
    first_background = None
    if first_page_background_path is not None:
        first_background = mu.open(first_page_background_path)
        first_background_page = first_background.load_page(0)

    for i in range(document.page_count):
        document_page = document.load_page(i)
        out_page = output.new_page(width=document_page.rect[0], height=document_page.rect[1])
        if i == 0 and first_background is not None:
            out_page.show_pdf_page(first_background_page.rect, first_background, pno=0)
            out_page.show_pdf_page(document_page.rect, document, pno=i)
            continue
        print(f"{background.page_count=}")
        if background.page_count == 1:
            background_page = background.load_page(0)
            background_page_num = 0
            print(f"HERE")
        else:
            try:
                background_page = background.load_page(i)
                background_page_num = i
            except IndexError:
                background_page = None
        if background_page is not None:
            out_page.show_pdf_page(background_page.rect, background, pno=background_page_num)
        out_page.show_pdf_page(document_page.rect, document, pno=i)
    output.save(destination_path)

        

