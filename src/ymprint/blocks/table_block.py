from collections import ChainMap
from collections.abc import Mapping

from reportlab.platypus import Paragraph, Table, TableStyle

from . import blockstyles
from ..config.helpers import convert_color
from ..content_converters import format_cell, is_table_data, render_template, table_columns
from ..errors import BlockError

OPTIONS = {"data", "columns", "headers", "format", "sort", "row_style", "caption"}


def convert_table_block(block_key: str, block_value: dict, context: dict) -> list:
    """
    Renders tabular data (a list of mappings) as a table, with options for
    which columns to show, their headers and number formats, the row order, and
    per-row styles. Cells are values, not Jinja templates.
    """
    if not isinstance(block_value, Mapping) or "data" not in block_value:
        raise BlockError(block_key, f"Block {block_key!r} needs a 'data:' field: a $var or a data source name.")
    unknown = set(block_value) - OPTIONS
    if unknown:
        raise BlockError(
            block_key,
            f"Block {block_key!r} has unknown option(s) {sorted(unknown)}. Choose from: {sorted(OPTIONS)}.",
        )
    rows = table_rows(block_key, block_value["data"], context)
    columns = block_value.get("columns") or table_columns(rows)
    headers = block_value.get("headers") or {}
    formats = block_value.get("format") or {}
    for option, names in (("format", formats), ("headers", headers)):
        missing = [name for name in names if name not in columns]
        if missing:
            raise BlockError(block_key, f"Block {block_key!r}: {option} names unknown column(s) {missing}.")
    rows = sort_rows(block_key, rows, block_value.get("sort") or [])

    table_data = [[str(headers.get(column, column)) for column in columns]]
    for row in rows:
        table_data.append([format_cell(row.get(column), formats.get(column)) for column in columns])
    table = Table(table_data, style=context["tablestyles"]["rl"]["_tablestyle"], repeatRows=1)

    row_style = block_value.get("row_style")
    if row_style:
        table.setStyle(TableStyle(row_style_commands(block_key, rows, row_style, context)))

    flowables = [table]
    caption = block_value.get("caption")
    if caption:
        caption_style = blockstyles.get_text_styles(blockstyles.block_scale(context)).get("image_caption")
        caption = render_template(str(caption), context["vars"])
        flowables.append(Paragraph(caption, style=caption_style))
    return flowables


def table_rows(block_key: str, data, context: dict) -> list:
    """Returns the rows of 'data': a list of mappings, or the name of a variable holding one."""
    if isinstance(data, str):
        name = data.lstrip("$")
        if name not in context["vars"]:
            raise BlockError(block_key, f"Block {block_key!r}: no variable or data source named {name!r}.")
        data = context["vars"][name]
    if not is_table_data(data):
        raise BlockError(
            block_key,
            f"Block {block_key!r}: 'data' must be a list of mappings (one per row), "
            f"not {type(data).__name__}.",
        )
    return data


def sort_rows(block_key: str, rows: list, keys: list) -> list:
    """
    Returns 'rows' sorted by the columns in 'keys', in priority order. A key
    starting with '-' sorts that column in descending order.
    """
    if isinstance(keys, str):
        keys = [keys]
    rows = list(rows)
    # Python's sort is stable, so sorting by the lowest-priority key first leaves
    # the rows ordered by every key.
    for key in reversed(keys):
        descending = key.startswith("-")
        column = key.lstrip("-")
        try:
            rows.sort(key=lambda row: row[column], reverse=descending)
        except KeyError:
            raise BlockError(block_key, f"Block {block_key!r}: cannot sort by {column!r}; not every row has it.") from None
    return rows


def row_style_commands(block_key: str, rows: list, row_style: str, context: dict) -> list:
    """
    Returns the TableStyle commands that colour each row by its style: the name
    'row_style' (a Jinja template, with `row` the row's mapping) renders to.
    """
    styles = context["tablestyles"]["ymprint"].body.rows.styles
    commands = []
    for index, row in enumerate(rows, start=1):
        name = render_template(row_style, ChainMap({"row": row}, context["vars"])).strip()
        if not name:
            continue
        if name not in styles:
            raise BlockError(
                block_key,
                f"Block {block_key!r}: row style {name!r} is not defined. "
                f"Defined row styles (_tablestyle.body.rows.styles): {sorted(styles)}.",
            )
        commands.append(("BACKGROUND", (0, index), (-1, index), convert_color(styles[name])))
    return commands
