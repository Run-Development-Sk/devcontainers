---
name: run-transcribe
description: >-
  Transcribe audio/video recordings (one file or a folder) into Markdown with speaker diarization
  via the OpenAI API, then clean the noisy transcript up with subagents into a faithful edited
  `<name>-cleaned-<agent>.md`. Use for "transcribe recording", "transcribe meeting", "prepis nahrávky",
  "prepis stretnutia", "prepíš záznam".
---

# run-transcribe

Pipeline: speech-grade audio (ffmpeg) -> chunks cut in silences -> two OpenAI transcriptions per
chunk -> raw diarized `<stem>-<agent>.md` -> cleanup of 5-minute excerpts by subagents ->
`<stem>-cleaned-<agent>.md`.
The mechanics live in `scripts/transcribe.py` (run it from the project root; `--help` lists the
subcommands); this file is the procedure around it.

## When to use

- "transcribe recording/meeting", "prepis nahrávky/stretnutia", "prepíš záznam",
- invoked directly as `/run-transcribe` in Claude Code; Codex and Auggie use the skill natively.

## 1. Input

- **PATH** (required) - a recording or a folder of recordings (not recursive).
- **Topic** (required) - what the conversation is about (company, its business, subject of the
  meeting).
- **Names and domain terms** (optional) - participants, companies, products, jargon.
- **Language** - Slovak (`sk`) unless the prompt says otherwise.

Ask in one question for whatever required input is missing.

**Agent suffix** `<agent>` - identifier of the running agent, passed as `--agent` and appended to
the output names (same identifiers as in `run-save-chat`):

| Agent       | Suffix   |
| ----------- | -------- |
| Auggie      | `auggie` |
| Claude Code | `claude` |
| Codex       | `codex`  |

## 2. Outputs

- `<stem>-<agent>.md` (raw diarized) and `<stem>-cleaned-<agent>.md` (faithful edited transcript)
  next to each recording, e.g. `my-recording-claude.md`, `my-recording-cleaned-claude.md`.
- Paragraphs `**[HH:MM:SS] X:** text`, timestamps in recording time. Recordings longer than ~23 min
  are transcribed in ~20-minute chunks separated by `=+=+=+=+=+=`; speaker labels (`A`, `B`, ...)
  are assigned per chunk, so the same person can have different labels in different chunks -
  matching them across chunks is left to the user.
- Work files (cache, a re-run only does what is missing; kept after the run for review):
  `tmp/transcribe-work/<path of the recording>/<agent>/`, e.g.
  `tmp/transcribe-work/meetings/2026-10-09/my-recording.m4a/claude/`. Each agent has its own work
  files, so several agents can process the same recordings in parallel (each pays its own API
  transcription).

### Cache conflicts

The script stops (before doing anything) instead of reusing a cache that does not fit:

- **the recording changed** since its work files were made (size/modification time differ from
  `source.json`) - the message names the work directory to delete,
- **`transcribe` with a different `--language` or `--prompt`** than the cached transcription
  (`transcribe-params.json`) - the message names the stored values; redoing means rerunning with
  `--redo transcription`.

In both cases show the message to the user and ask whether to keep the earlier result (rerun with the
stored values) or redo it (delete the named directory, or `--redo transcription`). Never discard
cached work without asking.

## 3. Prerequisites

- `ffmpeg` / `ffprobe` on the PATH.
- Python package `openai` - if missing, install it with `pip install openai --break-system-packages`.
- API key `TRANSCRIBE_OPENAI_API_KEY` in the environment or in `.devcontainer/.env`; if absent, ask
  the user to add it there. Never print it (`.agents/rules/run.secret-safety.md`).

## 4. Procedure

1. **Prepare** (local only): `python3 .agents/skills/run-transcribe/scripts/transcribe.py prepare <PATH> --agent <agent>`

   - prints the duration and chunk count of each recording, and a `PREVIOUS RUN` line for each
     recording this agent has already worked on (cached chunks/excerpts, existing outputs).
   - **Previous run** - if any `PREVIOUS RUN` line is printed, show it and ask (together with the
     confirmation in step 2) how to proceed:

     - **continue / reuse** (default when the previous run is unfinished) - no option; only the
       missing work is done, cached API responses and cleaned excerpts are reused at no cost,
     - **new independent transcript** - `--redo transcription` in step 3 (new API transcription
       and cleanup),
     - **new cleanup only** - `--redo cleanup` in step 3 (keeps the API transcription).

     When outputs already exist next to the recording, also ask whether to overwrite them or keep
     them - keeping means `--keep-previous` in steps 3 and 5 (an existing different output is
     renamed to `<stem>[-cleaned]-<its modification time>-<agent>.md`).

2. **Confirm** - the recordings are sent to OpenAI and the run costs money and tokens. Report the
   recordings, the total duration, and the estimate below, and wait for confirmation unless the
   prompt already confirmed the run explicitly:
   - OpenAI API: two passes, roughly $0.006 per audio minute each (verify current pricing),
   - cleanup: one subagent per 5 minutes of audio, ~90k tokens and 5–8 minutes each.
3. **Transcribe**: compose the second-pass prompt in the recording's language - one or two
   sentences on the topic followed by the names and terms (e.g. "Rozhovor o skladovom hospodárstve
   firmy X, ktorá predáva alkohol: daňový sklad, spotrebná daň, kolky, šarža. Účastníci: Tomáš,
   Ivana.") - and run
   `python3 .agents/skills/run-transcribe/scripts/transcribe.py transcribe <PATH> --agent <agent> --prompt "<prompt>" [--language <code>] [--redo transcription|cleanup] [--keep-previous]`.
   - It takes tens of minutes (a 20-minute chunk ≈ 10 minutes, 4 requests in parallel) - do not pipe
     it through `tail`/`head`, which hides the progress. If you run it in the background, keep
     checking its output until it exits instead of ending your turn to wait for a notification - in a
     non-interactive run (`claude -p`, `codex exec`, `auggie --print`) ending the turn ends the run.
     If it gets interrupted (e.g. by a command timeout), rerun it - finished work is cached.
   - It writes the raw `<stem>-<agent>.md` files and `tmp/transcribe-work/<PATH>/<agent>/cleanup-tasks.json`
     (pending cleanup tasks; the exact path is printed at the end).
4. **Clean up**: for every task in that `cleanup-tasks.json` start one subagent with
   the prompt template below, at most 8 running in parallel. Never hand one subagent more than one
   task - a whole 20-minute chunk exhausts its output budget before anything is written. Without
   subagent support, process the tasks yourself one by one, writing each output before reading the
   next task.
5. **Assemble**: `python3 .agents/skills/run-transcribe/scripts/transcribe.py assemble <PATH> --agent <agent> [--keep-previous]`
   - writes `<stem>-cleaned-<agent>.md` and warns about missing parts or timestamps not present in the
     input; rerun the affected tasks (delete their `.cleaned.md` first) if needed.
6. **Report** the written files with their counts of `[?]` / `[???]`, explain the meaning of both
   markers (`word [?]` - a plausible but uncertain correction of a misrecognized word; `[???]` - a
   passage that could not be reconstructed), and suggest spot-checking a few timestamps against the
   recording. End by pointing out that the temporary work files stay in
   `tmp/transcribe-work/<PATH>/` (subdirectories `<agent>/`) - the intermediate transcripts (raw API responses, second-pass
   texts, cleanup excerpts) can be reviewed there, and the directory can be deleted once no longer
   needed.

### Subagent prompt template

Fill `<...>` from the task and from step 1:

```text
Clean up a noisy diarized transcript excerpt into a faithful edited transcript, using an independent second transcription to fix wording.

1. Read the rules: <project root>/.agents/skills/run-transcribe/references/cleanup-rules.md and follow them exactly.
2. Conversation context: <topic>. Names and terms: <names and terms>.
3. Inputs (read both files whole):
   - diarized transcript excerpt <excerpt>: <diarized>
   - second transcription of the whole chunk: <second_pass> - this excerpt is part <part> of <parts> of that chunk.
4. Write the result with the Write tool to: <output>

Work efficiently: do not draft the whole output in your reasoning first - go through the input and write the output directly. Do not modify any other file. Final message: only the output path and the number of output paragraphs.
```

## Known limits

- The second transcription alone is not a usable transcript - it drops overlapping speech (about
  half of the text in a busy meeting); it only serves as a source of better wording.
- `gpt-4o-transcribe-diarize` accepts `language` but no `prompt`; that is why the glossary goes
  only to the second pass and to the cleanup.
- Overlapping speech stays partly `[???]` - no step can separate it reliably.

## Related
