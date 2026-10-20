# Merge rules for the OCR readings of a scanned page

## Inputs

1. **Two Markdown readings of the page** - the same layout analysis (pymupdf4llm), different text
   recognition:
   - **Tesseract** - usually more accurate words and diacritics, but tends to lose table rows and
     cells and adds stray characters next to stamps, signatures, and lines (`dielo=`, `č.w`).
   - **RapidOCR** - keeps table rows and cells more reliably, but loses or mangles diacritics
     (`ľ` -> `l'`, `ť` -> `t`, `ä` -> `â`) and drops letters at word starts (`Ťažké` -> `ažké`).
2. **The page image** - the authority wherever the readings disagree and context does not settle it.
   Without image support, decide from context alone and mark the uncertain words.

## Output: clean Markdown of the page, in the language of the document

- All text of the page in reading order. Do not summarize, translate, rephrase, add, or complete
  anything; keep the document's wording, spelling, and punctuation - only fix what OCR got wrong.
- Choose the correct reading word by word. When both readings are wrong and the image or context makes
  the word unambiguous, write it. A plausible but uncertain reading is followed by `[?]`; an unreadable
  passage is `[???]`. Both markers are fixed, regardless of the language of the document.
- Numbers, dates, amounts, and identifiers that differ between the readings are checked character by
  character against the image - never guessed.
- Structure: headings (`#`, levels consistent with the previous pages of the document when known),
  lists, pipe tables taken from the reading with the complete table and corrected cell by cell,
  bold/italic only where clearly visible.
- Join lines broken mid-sentence, rejoin words hyphenated at line ends, and merge paragraphs split by
  the layout analysis.
- Drop scan artifacts (stray characters from stamps, signatures, punch holes, page edges) and bare
  page numbers. Keep the readable text of stamps and handwritten notes; omit signatures.
- Output the page Markdown only: no heading for the page, no notes about the merge.
