---
description: >-
  Entry point to the run-convert-to-markdown skill – convert .pdf, .doc, .docx documents and scanned
  images to Markdown, merging two OCR readings of scanned pages.
---

# /run.convert-to-markdown – Convert documents and scans to Markdown

Follow the procedure according to the **`run-convert-to-markdown`** skill
(`.agents/skills/run-convert-to-markdown/SKILL.md`). The command and the skill have the same output;
this command is the entry point for Claude Code, Auggie, and Antigravity. (Codex does not support
slash commands – use the `run-convert-to-markdown` skill directly there.)

In short (details in the skill):

1. Take the documents and/or folders and the language of scans (default `slk+eng`) from the argument;
   ask for the paths if missing.
2. `convert` -> text documents become `<stem>.md` directly; scanned pages are read by Tesseract and
   RapidOCR and listed in a merge manifest.
3. Merge both readings of every scanned page into `page-NNN.md` (subagents for long scans).
4. Only with pending merges: `assemble` -> `<stem>.md`, check heading levels.
5. Report the result.

Hard rule: an existing `<stem>.md` is overwritten only after the user confirms it.

If the user provided an argument, use it as the input instead of asking again.
