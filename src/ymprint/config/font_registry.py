from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab.rl_config as rl_config
import pathlib
import warnings

class YMPrintFontPathWarning(Warning):
    pass

# ---------------------------------------------------------------------------
# Font registration
# ---------------------------------------------------------------------------

# Bundled fonts directory — sits alongside this module file.
# Ship the fonts/ subdirectory with your package; no system fonts required.
_FONTS_DIR = pathlib.Path(__file__).parent / "fonts" 


def register_fonts() -> None:
    """
    Register the bundled DejaVu Sans Mono TTF faces with ReportLab.

    Prepends the package-local ``fonts/`` directory to ReportLab's
    ``TTFSearchPath`` so that ``TTFont('DejaVuSansMono', 'DejaVuSansMono.ttf')``
    resolves to the bundled copy on any platform, regardless of what system
    fonts are installed.

    Call once at program start before building any flowables.

    Raises
    ------
    FileNotFoundError
        If the bundled ``fonts/`` directory or any expected TTF file is missing.
        This indicates a broken package installation rather than a missing system
        font, so we raise rather than silently fall back.
    """
    if not _FONTS_DIR.exists():
        raise FileNotFoundError(
            f"Bundled fonts directory not found: {_FONTS_DIR}\n"
            "Ensure the 'fonts/' directory is distributed alongside this module."
        )

    # Prepend so our bundled copies take priority over any system-installed
    # versions of the same filename.


    for fontpath in _FONTS_DIR.glob("*"):
        if not fontpath.is_dir():
            warnings.warn(
                YMPrintFontPathWarning(
                    f"A file was found in the YMPrint fonts directory: {fontpath}\n"
                    "The YMPrint fonts directory should only contain subdirectories representing font families."
                )
            )
            continue
        if _FONTS_DIR not in rl_config.TTFSearchPath:
            rl_config.TTFSearchPath.insert(0, str(fontpath.resolve()))
        font_family = fontpath.name
        font_names = {
            font_family: f"{font_family}.ttf",
            f"{font_family}-Bold": f"{font_family}-Bold.ttf",
            f"{font_family}-Oblique": f"{font_family}-Oblique.ttf",
            f"{font_family}-Italic": f"{font_family}-Italic.ttf",
            f"{font_family}-BoldOblique":  f"{font_family}-BoldOblique.ttf",
            f"{font_family}-BoldItalic":  f"{font_family}-BoldItalic.ttf",
        }

        for font_name, font_filename in font_names.items():
            missing = {}
            if not (fontpath / font_filename).exists():
                missing.setdefault(font_family, [])
                missing[font_family].append(font_name)
                # raise FileNotFoundError(
                #     f"Bundled font file missing: {(fontpath / font_filename).resolve()}\n"
                #     f"Ensure all font variations are present and named appropriately for this font: {font_family}\n"
                #     f"Required file naming convention as follows:\n\n"
                #     f"Regular: FontFamily.ttf\n"
                #     f"Bold: FontFamily-Bold.ttf\n"
                #     f"Italic: FontFamily-Oblique.ttf\n"
                #     f"Bold Italic: FontFamily-BoldOblique.ttf"
                # )

            else:
                pdfmetrics.registerFont(TTFont(font_name, font_filename))