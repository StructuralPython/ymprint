from .errors import YmprintAuthoringError


class YMPrintSyntaxException(YmprintAuthoringError):
    """A structural/syntax mistake in the author's document.

    Subclasses :class:`YmprintAuthoringError` so the CLI (convert and live) shows
    it as a compact authoring error instead of crashing with a raw traceback.
    """
    pass
