#!/usr/bin/env python3
"""Transcribe audio/video recordings with speaker diarization and prepare them for cleanup.

PATH is a recording or a directory of recordings (not recursive); outputs go next to the recordings.

  prepare PATH --agent A           extract speech-grade audio and split it into API-sized chunks; report
                                   what a previous run of the agent left (PREVIOUS RUN lines)
  transcribe PATH --agent A --prompt TEXT [--redo transcription|cleanup] [--keep-previous]
                                   prepare, transcribe every chunk twice (diarized pass and a second pass
                                   prompted with TEXT), write `<stem>-A.md` and the cleanup task manifest
  assemble PATH --agent A [--keep-previous]
                                   join the cleaned parts into `<stem>-cleaned-A.md`

--redo discards the agent's cached transcription (both passes and the cleanup) or only its cleanup.
--keep-previous renames an existing different output to `<stem>[-cleaned]-<its mtime>-A.md` instead of
overwriting it.

A is the running agent; it suffixes the outputs and has its own work files, so several agents can
process the same recordings in parallel.

Run from the project root. Work files are cached in tmp/transcribe-work/<path of the recording>/A/,
so a re-run only does what is missing. The cache is refused when the recording changed since it was
made, and `transcribe` refuses it when it was made with a different language or prompt.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

WORK_DIR = Path("tmp/transcribe-work")
AGENTS = ("claude", "auggie", "codex", "agy")  # output suffixes, as in the run-save-chat skill
MANIFEST_NAME = "cleanup-tasks.json"  # pending cleanup tasks, in the work directory of the input PATH
SOURCE_NAME = "source.json"  # fingerprint of the recording the work files were made from
PARAMS_NAME = "transcribe-params.json"  # language and prompt the transcriptions were made with
ENV_FILE = Path(".devcontainer/.env")
API_KEY_NAME = "TRANSCRIBE_OPENAI_API_KEY"

MEDIA_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".m4a", ".mp3", ".wav", ".ogg"}
DIARIZE_MODEL = "gpt-4o-transcribe-diarize"  # speaker labels and timestamps, no prompt support
SECOND_PASS_MODEL = "gpt-4o-transcribe"  # plain text, more accurate wording thanks to the prompt
DIARIZED_SUFFIX = ".json"
SECOND_PASS_SUFFIX = ".second-pass.json"
CHUNK_SEPARATOR = "=+=+=+=+=+="

# Speech-grade encoding: mono 16 kHz is what speech models work with internally.
AUDIO_FILTER = "dynaudnorm"  # evens out loudness of speakers near/far from the microphone
AUDIO_ARGS = ["-vn", "-ac", "1", "-ar", "16000", "-c:a", "aac", "-b:a", "48k"]

# The API rejects inputs longer than ~1400 s (and larger than 25 MB, which 48 kbps never reaches).
TARGET_CHUNK_SECONDS = 1200
MAX_CHUNK_SECONDS = 1380
# Silence detection runs on the original audio - dynaudnorm amplifies pauses towards speech level.
SILENCE_FILTER = "silencedetect=noise=-35dB:d=0.4"

PARALLEL_REQUESTS = 4
# One cleanup subagent handles at most this much audio; a whole chunk exhausts its output budget.
CLEANUP_PART_SECONDS = 300


def load_api_key() -> str:
    if os.environ.get(API_KEY_NAME):
        return os.environ[API_KEY_NAME]
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == API_KEY_NAME:
                return value.strip().strip("'\"")
    raise SystemExit(f"{API_KEY_NAME} is set neither in the environment nor in {ENV_FILE}")


def run(cmd: list[str]) -> str:
    """Run a command and return its stderr (where ffmpeg writes filter reports)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed:\n{result.stderr[-2000:]}")
    return result.stderr


def ffmpeg_to(target: Path, args: list[str]) -> None:
    """Run ffmpeg into a temporary file renamed on success, so an interrupted run leaves no stale output."""
    partial = target.with_name(f"{target.stem}.partial{target.suffix}")
    run(["ffmpeg", "-hide_banner", "-nostats", "-y", *args, str(partial)])
    partial.rename(target)


def duration_of(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout)


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"


def recordings_in(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.iterdir() if p.suffix.lower() in MEDIA_SUFFIXES)


def work_dir(path: Path, agent: str) -> Path:
    """Agent's directory under the mirrored path of a recording or an input directory in WORK_DIR."""
    absolute = Path(os.path.abspath(path))  # symlinks are not resolved - the given path is what identifies a recording
    try:
        relative = absolute.relative_to(Path.cwd())
    except ValueError:
        relative = absolute.relative_to(absolute.anchor)
    return WORK_DIR / relative / agent


def source_unchanged(recording: Path, agent: str) -> bool:
    """Record the recording's fingerprint on first use; False when the recording changed since then."""
    work = work_dir(recording, agent)
    work.mkdir(parents=True, exist_ok=True)
    stat = recording.stat()
    current = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    source = work / SOURCE_NAME
    if not source.exists():
        source.write_text(json.dumps(current) + "\n")
    return json.loads(source.read_text()) == current


def params_conflict(recording: Path, agent: str, language: str, prompt: str) -> str | None:
    """Record the transcription parameters on first use; describe the conflict when they differ."""
    params_file = work_dir(recording, agent) / PARAMS_NAME
    current = {"language": language, "prompt": prompt}
    if not params_file.exists():
        params_file.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n")
        return None
    stored = json.loads(params_file.read_text())
    differing = [key for key in current if stored.get(key) != current[key]]
    if not differing:
        return None
    return (f"{recording}: transcribed with a different {' and '.join(differing)} (stored in {params_file}); "
            f"to keep that transcription rerun with the stored values, to redo it rerun with --redo transcription")


def discard_cache(recording: Path, agent: str, redo: str) -> None:
    """Delete the agent's cleanup work files and, for "transcription", also its API responses."""
    work = work_dir(recording, agent)
    shutil.rmtree(work / "cleanup", ignore_errors=True)
    if redo == "transcription":
        for file in [*work.glob("chunk_*.json"), work / PARAMS_NAME]:
            file.unlink(missing_ok=True)


def silence_midpoints(source: Path) -> list[float]:
    report = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(source), "-vn",
                  "-af", SILENCE_FILTER, "-f", "null", "-"])
    starts = [float(s) for s in re.findall(r"silence_start: (-?[\d.]+)", report)]
    ends = [float(e) for e in re.findall(r"silence_end: ([\d.]+)", report)]
    return [(start + end) / 2 for start, end in zip(starts, ends)]


def plan_boundaries(duration: float, source: Path) -> list[float]:
    """Chunk boundaries [0, cut_1, ..., duration], each cut in the silence closest to the target length."""
    boundaries = [0.0]
    if duration > MAX_CHUNK_SECONDS:
        silences = silence_midpoints(source)
        while duration - boundaries[-1] > MAX_CHUNK_SECONDS:
            pos = boundaries[-1]
            candidates = [m for m in silences if pos < m <= pos + MAX_CHUNK_SECONDS]
            if candidates:
                cut = min(candidates, key=lambda m: abs(m - (pos + TARGET_CHUNK_SECONDS)))
            else:
                cut = pos + TARGET_CHUNK_SECONDS
                print(f"  WARNING: no silence found after {format_time(pos)}, cutting blindly at {format_time(cut)}")
            boundaries.append(cut)
    boundaries.append(duration)
    return boundaries


def prepare_chunks(recording: Path, agent: str) -> list[tuple[Path, float, float]]:
    """Return (chunk file, start, end) in recording time, creating the files when missing."""
    work = work_dir(recording, agent)
    audio = work / "audio.m4a"
    if not audio.exists():
        print(f"{recording.name}: extracting audio")
        ffmpeg_to(audio, ["-i", str(recording), "-af", AUDIO_FILTER, *AUDIO_ARGS])

    duration = duration_of(audio)
    boundaries = plan_boundaries(duration, recording)
    chunks = []
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:]), start=1):
        chunk = work / f"chunk_{index:02d}_{int(start)}-{int(end)}.m4a"
        if not chunk.exists():
            ffmpeg_to(chunk, ["-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(audio), "-c", "copy"])
        chunks.append((chunk, start, end))
    print(f"{recording.name}: {format_time(duration)}, {len(chunks)} chunk(s)")
    return chunks


def transcribe_chunk(client, chunk: Path, suffix: str, language: str, prompt: str) -> None:
    if suffix == DIARIZED_SUFFIX:
        params = {"model": DIARIZE_MODEL, "response_format": "diarized_json"}
    else:
        params = {"model": SECOND_PASS_MODEL, "response_format": "json", "prompt": prompt}
    print(f"  transcribing {chunk.parent.name}/{chunk.name} ({params['model']})")
    with chunk.open("rb") as audio:
        response = client.audio.transcriptions.create(
            file=audio, chunking_strategy="auto", language=language, **params
        )
    chunk.with_suffix(suffix).write_text(response.model_dump_json(indent=2))


def paragraphs(chunk: Path, offset: float) -> list[tuple[float, str]]:
    """Timestamped speaker paragraphs; consecutive segments of the same speaker are merged."""
    merged: list[tuple[str, float, list[str]]] = []
    for segment in json.loads(chunk.with_suffix(DIARIZED_SUFFIX).read_text())["segments"]:
        text = segment["text"].strip()
        if not text:
            continue
        if merged and merged[-1][0] == segment["speaker"]:
            merged[-1][2].append(text)
        else:
            merged.append((segment["speaker"], offset + segment["start"], [text]))
    return [(start, f"**[{format_time(start)}] {speaker}:** {' '.join(texts)}") for speaker, start, texts in merged]


def write_cleanup_parts(recording: Path, chunks: list[tuple[Path, float, float]], agent: str) -> list[dict]:
    """Split every chunk into CLEANUP_PART_SECONDS excerpts; return the tasks whose cleaned output is missing."""
    cleanup = work_dir(recording, agent) / "cleanup"
    cleanup.mkdir(exist_ok=True)
    tasks = []
    for chunk, start, end in chunks:
        second_pass = cleanup / f"{chunk.stem}.second-pass.txt"
        second_pass.write_text(json.loads(chunk.with_suffix(SECOND_PASS_SUFFIX).read_text())["text"] + "\n")
        count = max(1, round((end - start) / CLEANUP_PART_SECONDS))
        groups: list[list[str]] = [[] for _ in range(count)]
        for para_start, line in paragraphs(chunk, start):
            groups[min(int((para_start - start) // CLEANUP_PART_SECONDS), count - 1)].append(line)
        for part, lines in enumerate(groups, start=1):
            if not lines:
                continue
            diarized = cleanup / f"{chunk.stem}.part_{part:02d}.diarized.md"
            diarized.write_text("\n\n".join(lines) + "\n")
            output = cleaned_path(diarized)
            if output.exists():
                continue
            excerpt_end = end if part == count else start + part * CLEANUP_PART_SECONDS
            tasks.append({
                "recording": recording.name,
                "excerpt": f"{format_time(start + (part - 1) * CLEANUP_PART_SECONDS)}–{format_time(excerpt_end)}",
                "part": part,
                "parts": count,
                "diarized": str(diarized.resolve()),
                "second_pass": str(second_pass.resolve()),
                "output": str(output.resolve()),
            })
    return tasks


def cleaned_path(diarized: Path) -> Path:
    return diarized.with_name(diarized.name.replace(".diarized.md", ".cleaned.md"))


def output_path(recording: Path, agent: str, label: str = "") -> Path:
    """`<stem><label>-<agent>.md` next to the recording; label is "" (raw) or "-cleaned"."""
    return recording.with_name(f"{recording.stem}{label}-{agent}.md")


def write_output(recording: Path, agent: str, label: str, text: str, keep_previous: bool) -> Path:
    output = output_path(recording, agent, label)
    if keep_previous and output.exists() and output.read_text() != text:
        stamp = datetime.fromtimestamp(output.stat().st_mtime).strftime("%Y%m%d-%H%M%S")
        kept = recording.with_name(f"{recording.stem}{label}-{stamp}-{agent}.md")
        output.rename(kept)
        print(f"kept previous {kept}")
    output.write_text(text)
    return output


def previous_run(recording: Path, agent: str, chunks: list[tuple[Path, float, float]]) -> str | None:
    """Describe what a previous run of the agent left for the recording; None when there is nothing."""
    transcribed = sum(
        all(chunk.with_suffix(suffix).exists() for suffix in (DIARIZED_SUFFIX, SECOND_PASS_SUFFIX))
        for chunk, _, _ in chunks
    )
    parts = list((work_dir(recording, agent) / "cleanup").glob("*.diarized.md"))
    cleaned = sum(cleaned_path(part).exists() for part in parts)
    outputs = [p.name for p in (output_path(recording, agent), output_path(recording, agent, "-cleaned")) if p.exists()]
    if not (transcribed or parts or outputs):
        return None
    return (f"transcribed {transcribed}/{len(chunks)} chunk(s), cleaned {cleaned}/{len(parts)} excerpt(s), "
            f"existing outputs: {', '.join(outputs) or 'none'}")


def command_transcribe(recordings: list[Path], manifest: Path, agent: str, prompt: str, language: str,
                       redo: str | None, keep_previous: bool) -> None:
    from openai import OpenAI

    if redo:
        for recording in recordings:
            discard_cache(recording, agent, redo)
    conflicts = [c for c in (params_conflict(r, agent, language, prompt) for r in recordings) if c]
    if conflicts:
        raise SystemExit("\n".join(conflicts))
    chunks_by_recording = {recording: prepare_chunks(recording, agent) for recording in recordings}
    missing = [
        (chunk, suffix)
        for chunks in chunks_by_recording.values()
        for chunk, _, _ in chunks
        for suffix in (DIARIZED_SUFFIX, SECOND_PASS_SUFFIX)
        if not chunk.with_suffix(suffix).exists()
    ]
    if missing:
        client = OpenAI(api_key=load_api_key(), max_retries=5, timeout=900)
        with ThreadPoolExecutor(PARALLEL_REQUESTS) as pool:
            list(pool.map(lambda item: transcribe_chunk(client, *item, language, prompt), missing))

    tasks = []
    for recording, chunks in chunks_by_recording.items():
        transcript = f"\n\n{CHUNK_SEPARATOR}\n\n".join(
            "\n\n".join(line for _, line in paragraphs(chunk, start)) for chunk, start, _ in chunks
        )
        output = write_output(recording, agent, "", transcript + "\n", keep_previous)
        print(f"written {output}")
        tasks += write_cleanup_parts(recording, chunks, agent)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(tasks, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(tasks)} cleanup task(s) pending, listed in {manifest}")


def command_assemble(recordings: list[Path], agent: str, keep_previous: bool) -> None:
    incomplete = False
    for recording in recordings:
        parts = sorted((work_dir(recording, agent) / "cleanup").glob("*.diarized.md"))
        missing = [p.name for p in parts if not cleaned_path(p).exists()]
        if not parts or missing:
            incomplete = True
            print(f"{recording.name}: SKIPPED, missing cleaned parts: {missing or 'all - run transcribe first'}")
            continue
        by_chunk: dict[str, list[str]] = {}
        for part in parts:
            cleaned = cleaned_path(part).read_text().strip()
            # Cleaned paragraphs must start at a timestamp copied from the diarized excerpt.
            known = set(re.findall(r"^\*\*\[([\d:]+)\]", part.read_text(), re.M))
            invented = set(re.findall(r"^\*\*\[([\d:]+)\]", cleaned, re.M)) - known
            if invented:
                print(f"  WARNING: {cleaned_path(part).name} has timestamps not in its input: {sorted(invented)}")
            by_chunk.setdefault(part.name.split(".part_")[0], []).append(cleaned)
        transcript = f"\n\n{CHUNK_SEPARATOR}\n\n".join("\n\n".join(texts) for texts in by_chunk.values())
        output = write_output(recording, agent, "-cleaned", transcript + "\n", keep_previous)
        print(f"written {output} (unsure: {transcript.count('[?]')}, unintelligible: {transcript.count('[???]')})")
    if incomplete:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "transcribe", "assemble"):
        sub = commands.add_parser(name)
        sub.add_argument("path", type=Path)
        sub.add_argument("--agent", required=True, choices=AGENTS,
                         help="running agent, suffixes the outputs and owns its work directory")
        if name == "transcribe":
            sub.add_argument("--prompt", required=True,
                             help="topic, names and domain terms in the recording's language (second pass)")
            sub.add_argument("--language", default="sk", help="ISO-639-1 language of the recordings")
            sub.add_argument("--redo", choices=("transcription", "cleanup"),
                             help="discard the agent's cached transcription (with cleanup) or only its cleanup")
        if name != "prepare":
            sub.add_argument("--keep-previous", action="store_true",
                             help="rename an existing different output instead of overwriting it")
    args = parser.parse_args()

    recordings = recordings_in(args.path)
    if not recordings:
        raise SystemExit(f"no recordings found in {args.path}")
    changed = [r for r in recordings if not source_unchanged(r, args.agent)]
    if changed:
        raise SystemExit("\n".join(
            f"{r}: the recording changed since its work files were made - delete {work_dir(r, args.agent)} to process it again"
            for r in changed
        ))
    if args.command == "prepare":
        for recording in recordings:
            status = previous_run(recording, args.agent, prepare_chunks(recording, args.agent))
            if status:
                print(f"{recording.name}: PREVIOUS RUN - {status}")
    elif args.command == "transcribe":
        manifest = work_dir(args.path, args.agent) / MANIFEST_NAME
        command_transcribe(recordings, manifest, args.agent, args.prompt, args.language, args.redo,
                           args.keep_previous)
    else:
        command_assemble(recordings, args.agent, args.keep_previous)


if __name__ == "__main__":
    main()
