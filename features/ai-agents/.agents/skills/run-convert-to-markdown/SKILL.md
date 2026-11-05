---
name: run-convert-to-markdown
description: >-
  Convert .pdf, .doc, .docx documents and scanned images (.jpg, .png, .tif) to Markdown `<name>.md`
  next to each file; scanned pages are read by two OCR engines (Tesseract, RapidOCR) and the agent
  merges both readings into clean Markdown. Use for "convert to markdown", "pdf/docx to md",
  "OCR a scan", "konvertuj do markdownu", "prepíš sken do md".
---

# run-convert-to-markdown

The mechanics live in `scripts/convert_to_markdown.py` (run it from the project root; `--help` lists
the subcommands); the agent only merges the OCR readings of scanned pages.

| Input                                        | Conversion                                                                   |
| -------------------------------------------- | ---------------------------------------------------------------------------- |
| `.docx`                                      | python-docx - headings, bold/italic, links, lists, tables                    |
| `.doc`                                       | LibreOffice to `.docx`, then as above                                        |
| `.pdf` text pages                            | pymupdf4llm - layout analysis (headings, tables, reading order)              |
| `.pdf` scanned pages, `.jpg`, `.png`, `.tif` | pymupdf4llm layout with OCR twice (Tesseract, RapidOCR), merged by the agent |

A PDF page counts as scanned when images cover at least half of it, or when it holds an image and
fewer than 20 legible characters. Scanned pages are rendered as images for OCR: their visible text
(e.g. a stamp or header added to a scan) is read along with the scan, an invisible OCR layer left by a
scanner is discarded.

## When to use

- "convert to markdown", "pdf/docx to md", "OCR a scan", "konvertuj do markdownu", "prepíš sken do md",
- invoked directly as `/run-convert-to-markdown` in Claude Code; Codex and Auggie use the skill natively.

## 1. Input

- **PATH** (required) - one or more documents and/or folders of documents (not recursive), all passed
  to a single run. Ask for them if missing.
- **Language of the scans** - Tesseract codes joined by `+` (`slk`, `ces`, `eng`, `deu`, ...), default
  `slk+eng`; take it from the prompt or from the documents' context. Only Latin-script languages
  (RapidOCR runs its Latin model).

## 2. Outputs

- `<stem>.md` next to each document. Documents sharing a stem in one folder (`a.pdf`, `a.docx`) are
  refused - ask the user to rename one.
- Work files in `tmp/convert-to-markdown-work/<path of the document>/`, kept after the run: for every
  scanned page `page-NNN.png` (page image), `page-NNN.tesseract.md` and `page-NNN.rapidocr.md` (OCR
  readings); `page-NNN.md` for every finished page. `convert` starts every document from scratch.

## 3. Prerequisites

The script installs what the given documents need on first use, nothing else; a pip package of an
unsupported version is replaced by a supported one:

- pip (`--break-system-packages`): `pymupdf>=2,<3` (ships pymupdf4llm; PDF, images),
  `python-docx>=1.0` (`.doc`, `.docx`), `rapidocr` (scans; downloads its models on first OCR),
- apt (root or passwordless sudo): `libreoffice-writer-nogui` (`.doc`), `tesseract-ocr` and
  `tesseract-ocr-<lang>` (scans).

When an installation fails, the script stops and names what to install - pass that on to the user.
When it stops with `<package> installed - rerun`, rerun the same command.

## 4. Procedure

1. **Convert**: `python3 .agents/skills/run-convert-to-markdown/scripts/convert_to_markdown.py convert <PATH>... [--language <L>] [--overwrite]`
   - If it stops because an output already exists, ask the user whether to overwrite it and rerun with
     `--overwrite` only after a yes.
   - Text documents are finished by this step. OCR takes several seconds per page - do not pipe the
     output through `tail`/`head`. If you run it in the background, keep checking its output until it
     exits instead of ending your turn - in a non-interactive run (`claude -p`, `codex exec`,
     `auggie --print`) ending the turn ends the run.
   - It prints the number of pending page merges and the path of their manifest `merge-tasks.json`
     (in `tmp/convert-to-markdown-work/`, under the PATH or the closest folder of all PATHs). With 0
     pending merges, skip to step 5.
   - Files of unsupported formats, given or in a folder, are listed as `skipped (unsupported format)`.
     A document that cannot be read (damaged, password-protected) is reported as `cannot be converted`
     and the others are converted; the script then exits with 1 and lists them after `FAILED`.
2. **Merge** every task of the manifest by `references/merge-rules.md`: read both readings, look at the
   page image where they disagree, and write the task's `output`. Go through the tasks in order and
   write each page before reading the next. With more than 10 pending pages and subagent support,
   hand them out in runs of at most 5 consecutive pages of one document per subagent, at most 8
   subagents in parallel, with the prompt template below.
3. **Assemble**: `python3 .agents/skills/run-convert-to-markdown/scripts/convert_to_markdown.py assemble <PATH>... [--overwrite]`
   (the PATHs and `--overwrite` of step 1) - writes `<stem>.md` of every document with scanned pages;
   for missing pages, merge them and rerun.
4. **Check headings** of every assembled file (`grep -n '^#' <stem>.md`) and fix levels that are
   inconsistent across pages.
5. **Report** the written files, the skipped and failed files with the reasons from step 1, the counts of `[?]` / `[???]` in the merged ones with their meaning
   (`word [?]` - a plausible but uncertain reading; `[???]` - an unreadable passage), and that the work
   files stay in `tmp/convert-to-markdown-work/` for review and can be deleted.

### Subagent prompt template

Fill `<...>` from the manifest:

```text
Merge two OCR readings of scanned pages into clean Markdown.

1. Read the rules: <project root>/.agents/skills/run-convert-to-markdown/references/merge-rules.md and follow them exactly.
2. Document <document>, pages <first>–<last> of <pages>. For each task below, in order: read its `tesseract` and `rapidocr` files, look at its `image` where they disagree, and write the result with the Write tool to its `output` before moving on to the next task.
<the tasks' JSON entries>

Do not modify any other file. Final message: only the written paths with their counts of [?] and [???].
```

## Known limits

- `.docx`/`.doc`: images, headers/footers, footnotes, comments, and text boxes are left out;
  automatic numbering of headings is not rendered and lists get generic `-` / `1.` markers;
  tracked changes are converted as if accepted (insertions kept, deletions left out).
- A PDF whose text layer is gibberish without being marked illegible (broken font encoding) is
  converted as text - glance at the output of text PDFs.
- Handwriting is read poorly by both OCR engines.
- Both OCR readings of a scanned page share one layout analysis (pymupdf4llm), so a wrong reading
  order, a missed table, or a mis-detected heading is the same in both and their comparison does not
  reveal it.

## Related
