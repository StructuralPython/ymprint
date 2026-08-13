import io
import pathlib

import pymupdf as mu

def overlay_pdf_background(
    document_path: pathlib.Path | io.BytesIO,
    pdf_background_streams: dict[str, io.BytesIO | None],
    destination_path: pathlib.Path | io.BytesIO,
    context: dict,
    page_template_map: dict[int, str],
):
    """
    Overlays the rendered document pages onto their page template backgrounds and
    saves the result to 'destination_path'.

    'pdf_background_streams' maps a page template name to its (form-filled) PDF
    background stream, or None when that template has no background.

    'page_template_map' maps a 0-based page index to the name of the page template
    that rendered it, so each page is overlaid onto the correct template background.

    If a template's background PDF has multiple pages, each document page rendered
    with that template is overlaid onto the background page at the same absolute
    document index; document pages beyond the background's page count receive no
    background.
    """
    page_dims = context['doctemplate']['ymprint'].page_dims
    page_width, page_height = page_dims

    background_docs = {
        name: (mu.open(stream=data) if data is not None else None)
        for name, data in pdf_background_streams.items()
    }

    document = mu.open(stream=document_path)
    output = mu.open()
    for i in range(document.page_count):
        document_page = document.load_page(i)
        document_page.wrap_contents()
        out_page = output.new_page(width=page_width, height=page_height)

        template_name = page_template_map.get(i)
        background = background_docs.get(template_name)
        if background is not None:
            if background.page_count == 1:
                background_page_num = 0
            elif i < background.page_count:
                background_page_num = i
            else:
                background_page_num = None
            if background_page_num is not None:
                background_page = background.load_page(background_page_num)
                background_page.wrap_contents()
                out_page.show_pdf_page(background_page.rect, background, pno=background_page_num)

        out_page.show_pdf_page(document_page.rect, document, pno=i)
    output.save(destination_path)


def fill_forms_and_bake(vars: dict, pdf_backgrounds: dict[str, io.BytesIO | None]) -> dict[str, io.BytesIO | None]:
    """
    For each background stream, populates any PDF form fields whose name matches a
    document variable, then flattens ("bakes") the fields into the page content.
    Returns a dict with the same keys, mapping to the baked stream (or None).
    """
    out_docs: dict[str, io.BytesIO | None] = {}
    for name, data in pdf_backgrounds.items():
        if data is None:
            out_docs[name] = None
            continue

        doc = mu.open(stream=data)
        for page in doc.pages():
            widget = page.first_widget
            while widget is not None:
                field_name = widget.field_name
                widget_value = vars.get(field_name, None)
                if widget_value is not None:
                    widget.field_value = str(widget_value)
                    widget.update()
                widget = widget.next

        doc.bake()
        doc_data = io.BytesIO()
        doc.save(filename=doc_data)
        doc_data.seek(0)
        out_docs[name] = doc_data
    return out_docs


def load_pdf_backgrounds(context: dict) -> dict[str, io.BytesIO | None]:
    """
    Returns a dict mapping each page template name to its background PDF as a
    BytesIO stream (or None when the template has no background). Relative
    background paths are resolved against the source or config directory according
    to each background's 'relative-to' setting.
    """
    source_path = pathlib.Path(context['source_path'])
    source_parent = source_path.parent

    if context['config_path'] is not None:
        config_parent = pathlib.Path(context['config_path']).parent
    else:
        config_parent = source_parent

    doctemplate = context['doctemplate']['ymprint']
    backgrounds: dict[str, io.BytesIO | None] = {}
    for name, template in doctemplate.templates.items():
        background = template.background
        if background is None:
            backgrounds[name] = None
            continue

        relative_to = background.relative_to
        if relative_to == 'source':
            background_path = source_parent / background.filepath
        elif relative_to == 'config':
            background_path = config_parent / background.filepath
        else:
            background_path = background.filepath

        pdf = mu.open(background_path)
        data = io.BytesIO()
        pdf.save(data)
        data.seek(0)
        backgrounds[name] = data

    return backgrounds
