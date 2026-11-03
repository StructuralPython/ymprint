import collections
import re
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.nodes import MappingNode, ScalarNode, SequenceNode
import pathlib

from .errors import YamlSyntaxError

yaml = YAML(typ='rt')

STR_TAG = "tag:yaml.org,2002:str"
SEQ_TAG = "tag:yaml.org,2002:seq"
# Keys whose sequence values are bulleted / numbered lists: `_ul`, `_ol` and their
# `_ul_<id>` / `_ol_<id>` forms.
LIST_KEY_PATTERN = re.compile(r"^_(ul|ol)(_.*)?$")


def load_yaml(filepath: str | pathlib.Path) -> dict:
    """
    Reads the Yaml document and returns the dict
    """
    with open(filepath, encoding='utf-8') as file:
        source = file.read()
    try:
        node = yaml.compose(source)
        if node is None:
            return None
        _unfold_list_items(node, source.splitlines())
        data = yaml.constructor.construct_document(node)
    except YAMLError as e:
        # Re-raise as an authoring error so the CLI can report *which* file
        # and *where* the syntax problem is, instead of crashing.
        raise YamlSyntaxError(filepath, e) from e
    return data


def _unfold_list_items(node, lines: list[str], in_list: bool = False) -> None:
    """
    Recovers nested list items that YAML folded into their parent's text.

    In YAML, a plain scalar continues onto more-indented lines, so

        _ul:
          - one
            - nested

    loads as the single item 'one - nested'. Under `_ul` / `_ol` that is never
    what was meant, so such an item is split back into 'one' followed by a nested
    list ['nested']. Only sequences under list keys are touched.
    """
    if isinstance(node, MappingNode):
        for key_node, value_node in node.value:
            is_list_key = (
                isinstance(key_node, ScalarNode)
                and LIST_KEY_PATTERN.match(str(key_node.value)) is not None
            )
            _unfold_list_items(value_node, lines, in_list=is_list_key or in_list)
    elif isinstance(node, SequenceNode):
        new_items = []
        for item in node.value:
            if in_list and _is_folded_plain_scalar(item):
                new_items.extend(_split_folded_item(item, lines))
            else:
                _unfold_list_items(item, lines, in_list=in_list)
                new_items.append(item)
        node.value = new_items


def _is_folded_plain_scalar(node) -> bool:
    return (
        isinstance(node, ScalarNode)
        and node.style is None
        and node.tag == STR_TAG
        and node.end_mark.line > node.start_mark.line
    )


def _split_folded_item(node: ScalarNode, lines: list[str]) -> list:
    """
    Returns the nodes that replace the folded scalar 'node': the head item, then a
    nested sequence if any continuation line started with '- '. Returns [node]
    unchanged when there is nothing to unfold.
    """
    start, end = node.start_mark, node.end_mark
    head = lines[start.line][start.column:].strip()
    entries = []  # (indent, text) for each nested '- ' line
    for line_no in range(start.line + 1, end.line + 1):
        line = lines[line_no]
        if line_no == end.line:
            line = line[:end.column]
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        if stripped == "-" or stripped.startswith("- "):
            entries.append((indent, stripped[1:].strip()))
        elif entries:
            # A continuation of the previous nested item's text.
            prev_indent, prev_text = entries[-1]
            entries[-1] = (prev_indent, f"{prev_text} {stripped}".strip())
        else:
            head = f"{head} {stripped}"
    if not entries:
        return [node]
    head_node = ScalarNode(STR_TAG, head, start, start, style=None)
    return [head_node, _build_sequence(entries, start)]


def _build_sequence(entries: list[tuple[int, str]], mark) -> SequenceNode:
    """Builds a (possibly nested) sequence node from (indent, text) entries."""
    base_indent = entries[0][0]
    items = []
    i = 0
    while i < len(entries):
        indent, text = entries[i]
        if indent > base_indent and items:
            # Deeper lines belong to a sub-list under the previous item.
            j = i
            while j < len(entries) and entries[j][0] > base_indent:
                j += 1
            items.append(_build_sequence(entries[i:j], mark))
            i = j
            continue
        items.append(_scalar_or_null(text, mark))
        i += 1
    return SequenceNode(SEQ_TAG, items, mark, mark, flow_style=False)


def _scalar_or_null(text: str, mark) -> ScalarNode:
    if text == "":
        return ScalarNode("tag:yaml.org,2002:null", "", mark, mark, style=None)
    return ScalarNode(STR_TAG, text, mark, mark, style=None)
