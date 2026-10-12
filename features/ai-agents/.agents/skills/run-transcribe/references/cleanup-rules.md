# Cleanup rules for a diarized transcript excerpt

The conversation context (topic, names, domain terms) is given in the task prompt.

## Inputs

1. **Diarized transcript excerpt** (`gpt-4o-transcribe-diarize`) - paragraphs `**[HH:MM:SS] X:** text`,
   where `X` is a speaker label valid only within one transcription chunk. It is complete but noisy:
   overlapping speech splits sentences into fragments attributed to different speakers, short
   backchannels interrupt sentences, and many words are misrecognized (including forms from
   neighbouring languages). The excerpt is cut from a longer transcript, so its first/last paragraph
   may start/end mid-sentence - leave such edges as they are.
2. **Second transcription** (`gpt-4o-transcribe` prompted with the context) of the whole chunk the
   excerpt belongs to - plain text without speakers or timestamps; use only the portion matching the
   excerpt, located by content. Its wording is usually more accurate, but it omits overlapping speech
   and short utterances: something missing from it is **not** evidence that it was not said.

## Output: faithful edited transcript, in the language of the recording

- Keep **all content in its original order**. Do not summarize, paraphrase, shorten, add, or infer
  information. Keep the speakers' spoken register - only fix what speech recognition got wrong.
- Merge sentence fragments split by overlapping speech into whole sentences and assign each one to
  the most plausible speaker from context. Keep the input speaker labels (`A`, `B`, ...) - never
  rename them and never replace them with people's names.
- A new paragraph starts only on a speaker change. It begins with `**[HH:MM:SS] X:**` carrying the
  timestamp of the first input paragraph it was built from - timestamps are only copied from the
  input, never invented.
- Drop pure backchannels and fillers (`áno`, `mhm`, `jasné`, `no`, `hej`, false starts, stutter
  repetitions) unless they answer a question or express agreement/disagreement that matters.
- Correct a misrecognized word only when the correct word is unambiguous from context, from the
  second transcription, or from the given names and terms. When a correction is plausible but not
  certain, write it followed by `[?]`. Write `[???]` for passages that cannot be reconstructed.
  Both markers are fixed, regardless of the language of the recording.
- Use the second transcription for wording only; speaker attribution and timestamps come from the
  diarized excerpt.
- Text in another language stays as spoken if it was genuinely spoken in that language; obvious
  recognition errors (e.g. `wiedział` -> `vedel`) are corrected.
- Output the transcript only: no heading, no introduction, no summary, no notes about the edits.
