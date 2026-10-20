#!/usr/bin/env python3
"""Convert .pdf, .doc, .docx documents and scanned images (.jpg, .png, .tif) to Markdown.

PATH is a document or a directory of documents (not recursive), one or more of them; `<stem>.md` is
written next to each document.

  convert PATH... [--language L] [--overwrite]
                  convert text documents directly; read every scanned page (an image, or a PDF page
                  that is mostly an image or an image with no real text) with two OCR engines and list
                  the pages whose readings an agent has to merge into `page-NNN.md`
  assemble PATH... [--overwrite]
                  join the pages of every document with scanned pages into `<stem>.md`

L is the Tesseract language of the scans, e.g. `slk+eng` (default) or `ces+deu`.
--overwrite replaces an existing `<stem>.md`; without it the script stops before converting anything.
`convert` lists the skipped files of unsupported formats (given ones and those in a directory); a document that cannot be read is reported and
the others are converted, the exit status is then 1.

Python packages and system tools (Tesseract language data, LibreOffice for .doc) are installed on
first use, only those the given documents need.

Run from the project root. Work files go to tmp/convert-to-markdown-work/<path of the document>/;
`convert` starts every document from scratch.
"""

import argparse
import importlib
import importlib.metadata
import json
import os
import re
import shutil
import signal
import site
import subprocess
import sys
from itertools import groupby
from pathlib import Path

WORK_DIR = Path("tmp/convert-to-markdown-work")
MANIFEST_NAME = "merge-tasks.json"  # pending page merges, in the work directory of the input PATH

DOCUMENT_SUFFIXES = {".pdf", ".doc", ".docx"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

# Module -> (pip package, lowest supported version, lowest unsupported version).
# pymupdf 2.x ships the pymupdf4llm module; the pymupdf4llm 2.x package is an empty shim.
# The OCR passes use internal pymupdf4llm modules, hence the upper bound of pymupdf.
# python-docx 1.0 brings docx.text.hyperlink.
PIP_PACKAGES = {
    "pymupdf4llm": ("pymupdf", "2", "3"),
    "docx": ("python-docx", "1.0", None),
    "rapidocr": ("rapidocr", None, None),
}
LIBREOFFICE_PACKAGE = "libreoffice-writer-nogui"
LIBREOFFICE_TIMEOUT = 30  # seconds of a .doc conversion before LibreOffice is considered hung
# .docx elements whose content is document text: content controls, tracked insertions/moves, fields, smart tags
CONTENT_WRAPPERS = ("w:sdt", "w:sdtContent", "w:ins", "w:moveTo", "w:fldSimple", "w:smartTag", "w:customXml")
# `_` only where it can open or close emphasis - inside a word (snake_case) it is literal
INLINE_SPECIAL = re.compile(r"[\\`*~\[\]<]|(?<!\w)_|_(?!\w)")
# heading, bullet, quote, setext underline / thematic break, ordered list number (its `.`/`)` gets escaped)
BLOCK_START = re.compile(r"^( {0,3})(#{1,6}(?=\s|$)|[-+](?=\s|$)|>|[-=][-= \t]*$|\d{1,9}(?=[.)](?:\s|$)))", re.M)

OCR_ENGINES = ("tesseract", "rapidocr")
OCR_DPI = 300  # lowered for pages that would exceed the pixmap size limit of pymupdf4llm
PREVIEW_LONG_SIDE = 2000  # pixels of the page image the agent looks at when the OCR readings disagree
MIN_SCAN_COVERAGE = 0.5  # a page whose images cover at least this part of it is a scan, whatever its text
MIN_VISIBLE_CHARS = 20  # a page with an image and less visible text than this is a scan


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version)[:3])


def installed_version(module: str) -> str | None:
    """Version of the module's pip package when it is installed and supported, None otherwise."""
    package, lowest, unsupported = PIP_PACKAGES[module]
    try:
        version = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None
    if lowest and version_tuple(version) < version_tuple(lowest):
        return None
    if unsupported and version_tuple(version) >= version_tuple(unsupported):
        return None
    return version


def require(module: str):
    """Import a module, first installing its pip package when it is missing or of an unsupported version.

    The version is checked before the import - an imported module cannot be replaced in the running process.
    """
    if installed_version(module):
        return importlib.import_module(module)
    package, lowest, unsupported = PIP_PACKAGES[module]
    bounds = [f">={lowest}"] if lowest else []
    if unsupported:
        bounds.append(f"<{unsupported}")
    requirement = package + ",".join(bounds)
    try:
        print(f"installing {requirement} (found {importlib.metadata.version(package)})")
    except importlib.metadata.PackageNotFoundError:
        print(f"installing {requirement}")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--break-system-packages", requirement])
    if result.returncode != 0:
        raise SystemExit(f"cannot install {requirement} - install it manually and rerun")
    if site.ENABLE_USER_SITE:  # a --user install into a directory that did not exist at startup
        site.addsitedir(site.getusersitepackages())
    importlib.invalidate_caches()
    if not installed_version(module):  # a --user install shadowed by an older system-wide package until a restart
        raise SystemExit(f"{requirement} installed - rerun")
    return importlib.import_module(module)


def apt_install(packages: list[str]) -> None:
    sudo = [] if os.geteuid() == 0 else ["sudo", "-n"]
    env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
    print(f"installing {' '.join(packages)} (apt)")
    for command in (["apt-get", "update", "-qq"],
                    ["apt-get", "install", "-y", "-qq", "--no-install-recommends", *packages]):
        if not shutil.which("apt-get") or subprocess.run([*sudo, *command], env=env).returncode != 0:
            raise SystemExit(f"cannot install {' '.join(packages)} - install them manually and rerun")


def ensure_tessdata(language: str) -> None:
    """Make Tesseract language data available to pymupdf's built-in Tesseract."""
    require("pymupdf4llm")
    import pymupdf

    def missing_languages() -> list[str]:
        try:
            tessdata = Path(pymupdf.get_tessdata())
        except RuntimeError:
            return language.split("+")
        return [lang for lang in language.split("+") if not (tessdata / f"{lang}.traineddata").exists()]

    missing = missing_languages()
    if missing:
        apt_install(["tesseract-ocr", *(f"tesseract-ocr-{lang}" for lang in missing)])
        if missing_languages():
            raise SystemExit(f"Tesseract language data still missing: {', '.join(missing_languages())}")


SUPPORTED_SUFFIXES = DOCUMENT_SUFFIXES | IMAGE_SUFFIXES


def documents_in(path: Path) -> list[Path]:
    if not path.exists():
        raise SystemExit(f"{path} does not exist")
    files = [path] if path.is_file() else sorted(p for p in path.iterdir() if p.is_file())
    return [p for p in files if p.suffix.lower() in SUPPORTED_SUFFIXES]


def unsupported_in(path: Path) -> list[str]:
    """The skipped file itself, or the directory's skipped files - Markdown files (outputs) and hidden files aside."""
    if path.is_file():
        return [] if path.suffix.lower() in SUPPORTED_SUFFIXES else [str(path)]
    return sorted(
        str(p) for p in path.iterdir()
        if p.is_file() and p.suffix.lower() not in SUPPORTED_SUFFIXES | {".md"} and not p.name.startswith(".")
    )


def work_dir(path: Path) -> Path:
    """Mirrored path of a document or an input directory in WORK_DIR."""
    absolute = Path(os.path.abspath(path))
    try:
        relative = absolute.relative_to(Path.cwd())
    except ValueError:
        relative = absolute.relative_to(absolute.anchor)
    return WORK_DIR / relative


def output_path(document: Path) -> Path:
    return document.with_suffix(".md")


def check_outputs(documents: list[Path], overwrite: bool) -> None:
    outputs = [output_path(d) for d in documents]
    clashing = sorted({str(o) for o in outputs if outputs.count(o) > 1})
    if clashing:
        raise SystemExit(f"several documents would be converted to the same file: {', '.join(clashing)}")
    existing = [str(o) for o in outputs if o.exists()]
    if existing and not overwrite:
        raise SystemExit(f"output already exists: {', '.join(existing)} - rerun with --overwrite to replace it")


# --- .docx / .doc -------------------------------------------------------------------------------


def doc_to_docx(document: Path, work: Path) -> Path:
    if not shutil.which("soffice"):
        apt_install([LIBREOFFICE_PACKAGE])
    profile = (work / "libreoffice-profile").resolve()  # isolated from a running LibreOffice of the user
    command = ["soffice", f"-env:UserInstallation={profile.as_uri()}", "--headless", "--convert-to", "docx",
               "--outdir", str(work), str(document)]
    # own process group: soffice runs soffice.bin as a child that would outlive a killed soffice
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          start_new_session=True) as process:
        try:
            _, stderr = process.communicate(timeout=LIBREOFFICE_TIMEOUT)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise RuntimeError(f"LibreOffice did not finish within {LIBREOFFICE_TIMEOUT} s") from None
    converted = work / f"{document.stem}.docx"
    if process.returncode != 0 or not converted.exists():
        raise RuntimeError(f"LibreOffice conversion failed:\n{stderr[-2000:]}")
    return converted


def iter_content(element, parent, classes: dict):
    """python-docx objects of `classes` ({tag: class}) among the element's children, also inside CONTENT_WRAPPERS."""
    from docx.oxml.ns import qn

    wanted = {qn(tag): cls for tag, cls in classes.items()}
    wrappers = {qn(tag) for tag in CONTENT_WRAPPERS}

    def walk(node):
        for child in node:
            if child.tag in wanted:
                yield wanted[child.tag](child, parent)
            elif child.tag in wrappers:
                yield from walk(child)

    return walk(element)


def inline_items(paragraph):
    """Runs and hyperlinks of a paragraph."""
    from docx.text.hyperlink import Hyperlink
    from docx.text.run import Run

    return iter_content(paragraph._p, paragraph, {"w:r": Run, "w:hyperlink": Hyperlink})


def inherited(paragraph, path: str) -> str | None:
    """First value of `path` (relative to w:pPr) on the paragraph or along its style chain."""
    elements = [paragraph._p]
    style = paragraph.style
    while style is not None:
        elements.append(style.element)
        style = style.base_style
    for element in elements:
        values = element.xpath(f"./w:pPr/{path}")
        if values:
            return values[0]
    return None


def numbering_formats(document) -> dict[tuple[str, str], str]:
    """(numId, ilvl) -> numFmt (`bullet`, `decimal`, ...) of the document's list definitions."""
    from docx.oxml.ns import qn

    try:
        root = document.part.numbering_part.element
    except NotImplementedError:  # python-docx cannot create the part a document without lists lacks
        return {}
    abstracts = {a.get(qn("w:abstractNumId")): a for a in root.findall(qn("w:abstractNum"))}
    formats = {}
    for num in root.findall(qn("w:num")):
        abstract_id = num.find(qn("w:abstractNumId"))
        abstract = None if abstract_id is None else abstracts.get(abstract_id.get(qn("w:val")))
        if abstract is None:  # a broken list definition - its items get the default marker of list_marker()
            continue
        for level in abstract.findall(qn("w:lvl")):
            number_format = level.find(qn("w:numFmt"))
            formats[(num.get(qn("w:numId")), level.get(qn("w:ilvl")))] = (
                "decimal" if number_format is None else number_format.get(qn("w:val")))
    return formats


def escape_inline(text: str) -> str:
    """Escape characters Markdown would read as inline formatting, links, code, or HTML."""
    return INLINE_SPECIAL.sub(r"\\\g<0>", text)


def escape_block_starts(text: str) -> str:
    """Escape line starts Markdown would read as a heading, list item, quote, or underline."""
    def escape(match):
        indent, start = match.groups()
        return f"{indent}{start}\\" if start[0].isdigit() else f"{indent}\\{start}"

    return BLOCK_START.sub(escape, text)


def link_destination(url: str) -> str:
    """URL as a Markdown link destination - in angle brackets when whitespace, a parenthesis, or an angle
    bracket would end it early."""
    if not re.search(r"[\s()<>]", url):
        return url
    return "<" + re.sub(r"[<>]", r"\\\g<0>", url) + ">"


def wrap(text: str, marker: str) -> str:
    """Wrap text in an emphasis marker, keeping surrounding whitespace outside of it."""
    core = text.strip()
    if not marker or not core:
        return text
    start = len(text) - len(text.lstrip())
    return f"{text[:start]}{marker}{core}{marker}{text[start + len(core):]}"


def styled(runs) -> str:
    parts = []
    for (bold, italic), group in groupby(runs, key=lambda run: (bool(run.bold), bool(run.italic))):
        parts.append(wrap(escape_inline("".join(run.text for run in group)), "**" * bold + "*" * italic))
    return "".join(parts)


def inline_markdown(paragraph) -> str:
    """Paragraph text with emphasis and links; line breaks stay `\\n`."""
    from docx.text.hyperlink import Hyperlink

    parts = []
    for is_link, group in groupby(inline_items(paragraph), key=lambda item: isinstance(item, Hyperlink)):
        if not is_link:
            parts.append(styled(group))
            continue
        for link in group:
            text = styled(link.runs)
            parts.append(f"[{text}]({link_destination(link.url)})" if link.url and text.strip() else text)
    return "".join(parts).replace("\t", " ").strip()


def heading_level(paragraph) -> int | None:
    if paragraph.style is not None and paragraph.style.name == "Title":
        return 1
    outline = inherited(paragraph, "w:outlineLvl/@w:val")  # set by the built-in and custom heading styles
    return min(int(outline) + 1, 6) if outline is not None and int(outline) < 9 else None


def list_marker(paragraph, formats: dict[tuple[str, str], str]) -> str | None:
    num_id = inherited(paragraph, "w:numPr/w:numId/@w:val")
    if num_id in (None, "0"):
        return None
    level = inherited(paragraph, "w:numPr/w:ilvl/@w:val") or "0"
    bullet = formats.get((num_id, level), "bullet") in ("bullet", "none")
    return "    " * int(level) + ("- " if bullet else "1. ")


def table_markdown(table) -> str:
    from docx.text.paragraph import Paragraph

    rows = []
    seen = set()  # a merged cell is returned for every grid position it spans - keep its text once
    for row in table.rows:
        cells = []
        for cell in row.cells:
            paragraphs = [] if cell._tc in seen else iter_content(cell._tc, cell, {"w:p": Paragraph})
            texts = [inline_markdown(p) for p in paragraphs]
            seen.add(cell._tc)
            cells.append("<br>".join(t for t in texts if t).replace("\n", "<br>").replace("|", "\\|"))
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    lines = ["| " + " | ".join(row + [""] * (width - len(row))) + " |" for row in rows]
    lines.insert(1, "|" + " --- |" * width)
    return "\n".join(lines)


def docx_to_markdown(path: Path) -> str:
    docx = require("docx")
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(str(path))
    formats = numbering_formats(document)
    blocks: list[tuple[str, bool]] = []  # (markdown, is a list item)
    for item in iter_content(document.element.body, document, {"w:p": Paragraph, "w:tbl": Table}):
        if isinstance(item, Table):
            blocks.append((table_markdown(item), False))
            continue
        level = heading_level(item)
        marker = None if level else list_marker(item, formats)
        if level:
            text = " ".join(escape_inline("".join(part.text for part in inline_items(item))).split())
            if text.endswith("#"):  # a heading's trailing `#`s are dropped as its closing sequence
                text = f"{text[:-1]}\\#"
            blocks.append((f"{'#' * level} {text}" if text else "", False))
        else:
            text = escape_block_starts(inline_markdown(item)).replace("\n", "\\\n")
            blocks.append((f"{marker}{text}" if marker and text else text, bool(marker)))
    blocks = [block for block in blocks if block[0]]
    parts = []
    for index, (text, is_item) in enumerate(blocks):
        if index:
            parts.append("\n" if is_item and blocks[index - 1][1] else "\n\n")
        parts.append(text)
    return "".join(parts) + "\n"


# --- .pdf / images --------------------------------------------------------------------------------


def is_legible(span) -> bool:
    """Visible text with real characters - not an invisible OCR layer, not a font without a Unicode mapping."""
    import pymupdf

    visible = pymupdf.mupdf.FZ_STEXT_FILLED | pymupdf.mupdf.FZ_STEXT_STROKED
    return bool(span["char_flags"] & visible) and "\ufffd" not in span["text"]


def text_spans(page) -> list[dict]:
    return [span for block in page.get_text("dict")["blocks"] for line in block.get("lines", []) for span in line["spans"]]


def is_scanned(page) -> bool:
    """Mostly covered by images, or an image with too little legible text."""
    import pymupdf

    images = page.get_image_info()
    if not images:
        return False
    covered = sum(abs(pymupdf.Rect(image["bbox"]) & page.rect) for image in images)
    if covered >= MIN_SCAN_COVERAGE * abs(page.rect):
        return True
    return sum(len(span["text"].strip()) for span in text_spans(page) if is_legible(span)) < MIN_VISIBLE_CHARS


def rasterized(document: Path, number: int):
    """A new one-page document of the given page rendered as an image.

    OCR then reads everything visible on it, a stamp or header added to a scan as text included. pymupdf4llm
    lays out OCR text that Tesseract writes invisibly only on pages without visible text, and an invisible OCR
    layer or text without a Unicode mapping must not get into the readings. One page at a time - a rendered
    page takes tens of MB, a whole scanned document would not fit in memory.
    """
    import pymupdf
    from pymupdf4llm.ocr.get_culled_pixmap import MAX_PIXELS, max_dpi_for_page

    raster = pymupdf.open()
    with pymupdf.open(document) as doc:
        page = doc[number]
        dpi = min(OCR_DPI, max_dpi_for_page(page.rect, max_pixels=MAX_PIXELS))
        raster.new_page(width=page.rect.width, height=page.rect.height).insert_image(
            page.rect, pixmap=page.get_pixmap(dpi=dpi))
    return raster


def rapidocr_function():
    """pymupdf4llm OCR callback using RapidOCR with its Latin-script recognition model (diacritics)."""
    require("rapidocr")
    from pymupdf4llm.ocr.exec_ocr_interface import exec_ocr_full
    from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR

    engine = RapidOCR(params={
        "Global.log_level": "critical",
        "Rec.lang_type": LangRec.LATIN,
        "Rec.ocr_version": OCRVersion.PPOCRV5,
        "Rec.model_type": ModelType.MOBILE,
    })

    def full_ocr(image):
        result = engine(image)
        return [] if result.boxes is None else list(zip(result.boxes, result.txts, result.scores))

    def exec_ocr(page, dpi=OCR_DPI, pixmap=None, language=None, keep_ocr_text=False):
        return exec_ocr_full(page, full_ocr, dpi=dpi, keep_ocr_text=keep_ocr_text)

    return exec_ocr


def page_name(number: int) -> str:
    return f"page-{number:03d}"


def page_markdown(doc, pages: list[int], **options) -> dict[int, str]:
    """Markdown of the given 0-based pages of a document (path or opened), keyed by the 0-based page number."""
    pymupdf4llm = require("pymupdf4llm")
    chunks = pymupdf4llm.to_markdown(doc, pages=pages, page_chunks=True, **options)
    return {
        chunk["metadata"]["page_number"] - 1: "\n".join(line.rstrip() for line in chunk["text"].strip().splitlines())
        for chunk in chunks
    }


def convert_paged(document: Path, work: Path, language: str) -> list[dict]:
    """Write `page-NNN.md` for text pages and both OCR readings of scanned pages; return the merge tasks."""
    require("pymupdf4llm")
    import pymupdf
    from pymupdf4llm.ocr import OCRMode

    with pymupdf.open(document) as doc:
        if doc.needs_pass:
            raise RuntimeError("the document is password-protected")
        page_count = doc.page_count
        scanned = list(range(page_count)) if not doc.is_pdf else [p.number for p in doc if is_scanned(p)]
        for number in scanned:
            page = doc[number]
            zoom = PREVIEW_LONG_SIDE / max(page.rect.width, page.rect.height)
            page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(work / f"{page_name(number + 1)}.png")

    text_pages = [number for number in range(page_count) if number not in scanned]
    if text_pages:
        for number, text in page_markdown(str(document), text_pages, use_ocr=False).items():
            (work / f"{page_name(number + 1)}.md").write_text(text + "\n")
    if not scanned:
        return []

    ensure_tessdata(language)
    from pymupdf4llm.ocr import tesseract_api

    functions = {"tesseract": tesseract_api.exec_ocr, "rapidocr": rapidocr_function()}
    for engine in OCR_ENGINES:
        print(f"{document.name}: OCR of {len(scanned)} page(s) with {engine}")
        for number in scanned:
            # every pass gets a fresh document - OCR writes its text into the page
            with rasterized(document, number) as raster:
                text = page_markdown(raster, [0], use_ocr=OCRMode.FORCE_DROP_OLD, ocr_function=functions[engine],
                                     ocr_language=language, ocr_dpi=OCR_DPI)[0]
            (work / f"{page_name(number + 1)}.{engine}.md").write_text(text + "\n")
    return [
        {
            "document": str(document),
            "page": number + 1,
            "pages": page_count,
            "image": str((work / f"{page_name(number + 1)}.png").resolve()),
            **{engine: str((work / f"{page_name(number + 1)}.{engine}.md").resolve()) for engine in OCR_ENGINES},
            "output": str((work / f"{page_name(number + 1)}.md").resolve()),
        }
        for number in scanned
    ]


def assemble(document: Path) -> bool:
    """Join `page-NNN.md` files into the output; False when a page is still missing."""
    work = work_dir(document)
    numbers = sorted({p.name.split(".")[0] for p in work.glob("page-*.*")}, key=lambda name: int(name[len("page-"):]))
    missing = [n for n in numbers if not (work / f"{n}.md").exists()]
    if not numbers or missing:
        print(f"{document.name}: SKIPPED, missing pages: {missing or 'all - run convert first'}")
        return False
    pages = [(work / f"{n}.md").read_text().strip() for n in numbers]
    output = output_path(document)
    output.write_text("\n\n".join(page for page in pages if page) + "\n")
    print(f"written {output} ({len(numbers)} page(s))")
    return True


# --- commands -------------------------------------------------------------------------------------


def convert_document(document: Path, language: str) -> list[dict]:
    """Convert one document; return the merge tasks of its scanned pages."""
    work = work_dir(document)
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    suffix = document.suffix.lower()
    if suffix in (".doc", ".docx"):
        source = doc_to_docx(document, work) if suffix == ".doc" else document
        output_path(document).write_text(docx_to_markdown(source))
        print(f"written {output_path(document)}")
        return []
    tasks = convert_paged(document, work, language)
    if tasks:
        print(f"{document.name}: {len(tasks)} scanned page(s) to merge")
    else:
        assemble(document)
    return tasks


def command_convert(paths: list[Path], documents: list[Path], language: str) -> None:
    tasks = []
    failed = []
    for document in documents:
        try:
            tasks += convert_document(document, language)
        except Exception as error:  # a damaged or unreadable document must not stop the others
            print(f"{document.name}: cannot be converted - {type(error).__name__}: {error}")
            failed.append(document.name)
    manifest = work_dir(Path(os.path.commonpath([os.path.abspath(path) for path in paths]))) / MANIFEST_NAME
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(tasks, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(tasks)} page merge task(s) pending, listed in {manifest}")
    if failed:
        print(f"FAILED ({len(failed)}): {', '.join(failed)}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("convert", "assemble"):
        sub = commands.add_parser(name)
        sub.add_argument("paths", nargs="+", type=Path, metavar="PATH")
        sub.add_argument("--overwrite", action="store_true", help="replace an existing `<stem>.md`")
        if name == "convert":
            sub.add_argument("--language", default="slk+eng", help="Tesseract language(s) of scanned pages")
    args = parser.parse_args()
    inputs = ", ".join(map(str, args.paths))

    # a document given twice (also through its directory) is converted once
    documents = list({d.resolve(): d for path in args.paths for d in documents_in(path)}.values())
    skipped = sorted({s for path in args.paths for s in unsupported_in(path)}) if args.command == "convert" else []
    if skipped:
        print(f"skipped (unsupported format): {', '.join(skipped)}")
    if not documents:
        raise SystemExit(f"no supported documents found in {inputs} - supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}")
    if args.command == "convert":
        check_outputs(documents, args.overwrite)
        command_convert(args.paths, documents, args.language)
    else:
        scanned = [d for d in documents if any(work_dir(d).glob(f"page-*.{OCR_ENGINES[0]}.md"))]
        if not scanned:
            raise SystemExit(f"no document with scanned pages in {inputs} - run convert first")
        check_outputs(scanned, args.overwrite)
        assembled = [assemble(document) for document in scanned]
        if not all(assembled):
            sys.exit(1)


if __name__ == "__main__":
    main()
