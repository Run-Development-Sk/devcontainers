---
description: >-
  Entry point to the run-transcribe skill – diarized transcription of audio/video recordings via
  the OpenAI API and their cleanup into faithful edited `<name>-cleaned-<agent>.md` transcripts.
---

# /run.transcribe – Transcribe and clean up recordings

Follow the procedure according to the **`run-transcribe`** skill
(`.agents/skills/run-transcribe/SKILL.md`). The command and the skill have the same output;
this command is the entry point for Claude Code, Auggie, and Antigravity. (Codex does not
support slash commands – use the `run-transcribe` skill directly there.)

In short (details in the skill):

1. Take the recording or folder, the topic, and optional names/terms from the argument; ask for
   whatever required input is missing.
2. `prepare` the audio locally, report duration and cost estimate, and wait for confirmation.
3. `transcribe` (diarized pass + glossary-prompted second pass) -> raw `<stem>-<agent>.md` and cleanup tasks.
4. Clean up every 5-minute excerpt with its own subagent (at most 8 in parallel).
5. `assemble` -> `<stem>-cleaned-<agent>.md` next to each recording, then report the result.

Hard rules: recordings go to OpenAI only after confirmation; one subagent never gets more than one
excerpt; the API key is never printed (`.agents/rules/run.secret-safety.md`).

If the user provided an argument, use it as the input instead of asking again.
