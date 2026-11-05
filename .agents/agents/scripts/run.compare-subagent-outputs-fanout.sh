#!/usr/bin/env bash
# Fan-out orchestrator for the run.compare-subagent-outputs subagent.
# Runs multiple CLI agents (claude/auggie/codex) headless on the same
# prompt, saves outputs to tmp/ (leaves them for inspection). auggie runs
# read-only (--ask); claude additionally has WebFetch/WebSearch/Bash, and codex runs without
# an internal sandbox (bypass) - read-only nature is ensured by prompt + container.
# The prompt is passed to claude/codex/auggie via FILE/STDIN (not via argv).
# Never include secrets in the prompt - .agents/rules/run.secret-safety.md.
# After execution, writes an overview to <out-dir>/manifest.tsv (agent, model, status, exit,
# duration, lines) and flags suspiciously short outputs as SHORT.
# Only stdout (pure analysis for comparison) goes to <agent>[_<model>].md; stderr
# is routed to the sidecar <agent>[_<model>].stderr (an empty one is deleted). Upon failure,
# the tail of stderr is appended to .md to make the reason visible. Codex is an exception - its
# stdout-log (reasoning + tool) is in the sidecar <agent>.transcript, while .md only has the -o message.
set -uo pipefail

# --- recursion guard: orchestrator must never run itself ---
if [[ "${RUN_COMPARE_SUBAGENT_OUTPUTS_ACTIVE:-}" == "1" ]]; then
  echo "run.compare-subagent-outputs: recursive execution is forbidden (RUN_COMPARE_SUBAGENT_OUTPUTS_ACTIVE=1)." >&2
  exit 3
fi
export RUN_COMPARE_SUBAGENT_OUTPUTS_ACTIVE=1

usage() {
  cat >&2 <<'EOF'
Usage:
  run.compare-subagent-outputs-fanout.sh --prompt-file <file> [--out-dir <dir>] [agent[:model] ...]
  run.compare-subagent-outputs-fanout.sh --check [agent[:model] ...]

  --prompt-file   mandatory (except --check); file with the task for subagents
  --out-dir       optional; default tmp/run.compare-subagent-outputs/<timestamp>
  --check         self-test: verify auth + flag validity with a cheap prompt (no fan-out)
  agent[:model]   optional; default "claude auggie" (models based on CLI configuration)
                  supported agents: claude, auggie, codex
EOF
}

PROMPT_FILE=""; OUT_DIR=""; SPECS=(); CHECK_MODE=""; CHECK_TMP_PROMPT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt-file) PROMPT_FILE="${2:-}"; shift 2;;
    --out-dir) OUT_DIR="${2:-}"; shift 2;;
    --check) CHECK_MODE=1; shift;;
    -h|--help) usage; exit 0;;
    --*) echo "Unknown option: $1" >&2; usage; exit 2;;
    *) SPECS+=("$1"); shift;;
  esac
done

if [[ "$CHECK_MODE" == "1" ]]; then
  # self-test: cheap prompt (ignores --prompt-file), only verification of auth + flags
  CHECK_TMP_PROMPT="$(mktemp)"; printf 'Respond with exactly one word: OK\n' > "$CHECK_TMP_PROMPT"
  PROMPT_FILE="$CHECK_TMP_PROMPT"
  [[ -z "$OUT_DIR" ]] && OUT_DIR="tmp/run.compare-subagent-outputs/check-$(date +%Y%m%d-%H%M%S)"
else
  [[ -z "$PROMPT_FILE" || ! -f "$PROMPT_FILE" ]] && { echo "Missing valid --prompt-file." >&2; usage; exit 2; }
  [[ -z "$OUT_DIR" ]] && OUT_DIR="tmp/run.compare-subagent-outputs/$(date +%Y%m%d-%H%M%S)"
fi
[[ ${#SPECS[@]} -eq 0 ]] && SPECS=(claude auggie)
mkdir -p "$OUT_DIR"
# we COPY the input prompt to out-dir → there is always a copy of the task
# in <timestamp>/prompt.md and the source file is not deleted by default (non-destructive cp).
# Exception – throwaway prompt prepared by the orchestrator
# (tmp/run.compare-subagent-outputs/prompt.md): we delete this after copying (net effect = mv)
# so that nothing is left at the top level of tmp/run.compare-subagent-outputs/.
# Safety guard: if PROMPT_FILE IS already the target (e.g., via --out-dir), skip copying.
THROWAWAY_PROMPT="tmp/run.compare-subagent-outputs/prompt.md"
if [[ "$(readlink -f "$PROMPT_FILE")" != "$(readlink -f "$OUT_DIR/prompt.md")" ]]; then
  cp "$PROMPT_FILE" "$OUT_DIR/prompt.md"
  # only delete throwaway source; custom --prompt-file on a different path remains untouched
  if [[ "$(readlink -f "$PROMPT_FILE")" == "$(readlink -f "$THROWAWAY_PROMPT")" ]]; then
    rm -f "$PROMPT_FILE"
  fi
fi
PROMPT_FILE="$OUT_DIR/prompt.md"   # from now on we work with the copy in out-dir
printf '%s\n' "${SPECS[@]}" > "$OUT_DIR/specs.txt"

run_agent() {
  local agent="$1" model="$2" out="$3" meta="$4"
  local start ec=0 dur stderr="${out%.md}.stderr"
  start=$(date +%s)
  if ! command -v "$agent" >/dev/null 2>&1; then
    echo "SKIP: '$agent' is not installed/available." > "$out"
    dur=$(( $(date +%s) - start ))
    # placeholder '-' for empty model: tab is whitespace for `read` and empty
    # fields would collapse (column shift in manifest)
    printf '%s\t%s\t%s\t%s\n' "$agent" "${model:--}" "SKIP" "$dur" > "$meta"
    return 0
  fi
  case "$agent" in
    claude)
      # tools: read tools (Read/Grep/Glob) + WebFetch/WebSearch/Bash for verification;
      # --allowedTools pre-approves them so they run in -p without an interactive prompt.
      # The analysis becomes the final message, so -p/text output captures it correctly.
      # --permission-mode plan is NOT USED: in plan mode, the final message is only a stub
      # ("analysis delivered above") and the entire content is discarded.
      # NOTE: these --tools are tools of the EXECUTED claude subagent –
      # they are unrelated to `tools:` in the orchestrator's frontmatter (run.compare-subagent-outputs.md).
      local ctools="Read,Grep,Glob,WebFetch,WebSearch,Bash"
      local a=(--permission-mode default --tools "$ctools" --allowedTools "$ctools")
      [[ -n "$model" ]] && a+=(--model "$model")
      # stdout → .md (analysis), stderr → sidecar; upon failure, tail of stderr is appended to .md
      claude -p "${a[@]}" < "$PROMPT_FILE" > "$out" 2>"$stderr"; ec=$?
      if [[ $ec -ne 0 ]]; then
        [[ -s "$stderr" ]] && tail -n 20 "$stderr" >> "$out"
        echo "[claude failed, exit $ec]" >> "$out"
      fi
      ;;
    auggie)
      # --ask = retrieval/non-editing tools only (read-only run)
      # --allow-indexing = skip indexing confirmation; --wait-for-indexing =
      # wait for index completion before retrieval (same context as from console)
      local a=(--print --quiet --ask --allow-indexing --wait-for-indexing)
      [[ -n "$model" ]] && a+=(--model "$model")
      # Login: retrieve saved session (`auggie token print`) and pass it
      # via ENVIRONMENT (AUGMENT_SESSION_AUTH), not via argv – run.secret-safety.
      # NEVER print the session value.
      # `auggie token print` returns multiline output; JSON is on the line SESSION=<json>.
      # cut -d= -f2- preserves potential '=' inside the value (base64 padding, etc.).
      local sess=""; sess="$(auggie token print 2>/dev/null | grep -m1 '^SESSION=' | cut -d= -f2-)" || sess=""
      # stdout → .md (analysis), stderr → sidecar; upon failure, tail of stderr is appended to .md
      if [[ -n "$sess" ]]; then
        AUGMENT_SESSION_AUTH="$sess" auggie "${a[@]}" --instruction-file "$PROMPT_FILE" > "$out" 2>"$stderr"; ec=$?
        [[ $ec -ne 0 ]] && { [[ -s "$stderr" ]] && tail -n 20 "$stderr" >> "$out"; echo "[auggie failed, exit $ec – verify login or enterprise gating of non-interactive mode]" >> "$out"; }
      else
        auggie "${a[@]}" --instruction-file "$PROMPT_FILE" > "$out" 2>"$stderr"; ec=$?
        [[ $ec -ne 0 ]] && { [[ -s "$stderr" ]] && tail -n 20 "$stderr" >> "$out"; echo "[auggie failed, exit $ec – failed to obtain session (auggie token print); verify login]" >> "$out"; }
      fi
      ;;
    codex)
      # Context: dev-container is an external sandbox, so we do not need
      # the internal codex sandbox (and in a container without unprivileged userns,
      # bwrap would fail anyway – "No permissions to create new namespace").
      # Therefore, it runs by default via --dangerously-bypass-approvals-and-sandbox
      # (specifically for external sandbox environments); read-only nature is ensured
      # by the prompt + external container.
      # -a/--ask-for-approval was removed from codex CLI (>=0.14x).
      local a=(exec --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox)
      [[ -n "$model" ]] && a+=(-m "$model")
      local last_msg; last_msg="$(mktemp)"
      # transcript (reasoning + tool log) goes to sidecar .transcript; we put
      # ONLY the final message (-o) into the main .md → pure, comparable output like claude -p
      local transcript="${out%.md}.transcript"
      codex "${a[@]}" -o "$last_msg" < "$PROMPT_FILE" > "$transcript" 2>&1; ec=$?
      if [[ -s "$last_msg" ]]; then
        cat "$last_msg" >> "$out"
      fi
      rm -f "$last_msg"
      if [[ $ec -ne 0 ]]; then
        # upon failure, final message is missing → make the reason from transcript visible in .md
        [[ -s "$transcript" ]] && tail -n 20 "$transcript" >> "$out"
        echo "[codex failed, exit $ec]" >> "$out"
      fi
      ;;
    *)
      echo "SKIP: unknown agent '$agent'." > "$out"
      dur=$(( $(date +%s) - start ))
      printf '%s\t%s\t%s\t%s\n' "$agent" "${model:--}" "SKIP" "$dur" > "$meta"
      return 0
      ;;
  esac
  # do not leave empty stderr sidecar in out-dir
  [[ -f "$stderr" && ! -s "$stderr" ]] && rm -f "$stderr"
  dur=$(( $(date +%s) - start ))
  printf '%s\t%s\t%s\t%s\n' "$agent" "${model:--}" "$ec" "$dur" > "$meta"
  return 0
}

# --- self-test mode (--check): verify auth + flag validity, no costly fan-out ---
if [[ "$CHECK_MODE" == "1" ]]; then
  echo "run.compare-subagent-outputs --check: verifying ${#SPECS[@]} agents with a cheap prompt → $OUT_DIR" >&2
  mkdir -p "$OUT_DIR/.meta"
  cpids=(); clabels=()
  for spec in "${SPECS[@]}"; do
    agent="${spec%%:*}"; model=""
    [[ "$spec" == *:* ]] && model="${spec#*:}"
    label="$agent"; [[ -n "$model" ]] && label="${agent}_$(echo "$model" | tr ' /' '__')"
    run_agent "$agent" "$model" "$OUT_DIR/${label}.md" "$OUT_DIR/.meta/${label}.meta" &
    cpids+=("$!"); clabels+=("$label")
  done
  for pid in "${cpids[@]}"; do wait "$pid" || true; done

  echo "" >&2
  crc=0; CHK="$OUT_DIR/check.tsv"
  printf 'agent\tmodel\tstatus\texit\n' > "$CHK"
  for label in "${clabels[@]}"; do
    meta="$OUT_DIR/.meta/${label}.meta"; cout="$OUT_DIR/${label}.md"
    a=""; m=""; e=""; d="0"
    [[ -f "$meta" ]] && IFS=$'\t' read -r a m e d < "$meta"
    [[ "$m" == "-" ]] && m=""
    status="OK"
    if [[ "$e" == "SKIP" ]]; then status="SKIP"
    elif [[ "$e" != "0" || ! -s "$cout" ]]; then status="FAIL"; crc=1; fi
    printf '%s\t%s\t%s\t%s\n' "${a:-?}" "$m" "$status" "${e:-?}" >> "$CHK"
  done
  column -t -s "$(printf '\t')" "$CHK" >&2 2>/dev/null || cat "$CHK" >&2
  [[ -n "$CHECK_TMP_PROMPT" ]] && rm -f "$CHECK_TMP_PROMPT"
  echo "$OUT_DIR"
  exit $crc
fi

echo "run.compare-subagent-outputs: running ${#SPECS[@]} subagents, output → $OUT_DIR" >&2
mkdir -p "$OUT_DIR/.meta"
PIDS=(); LABELS=()
for spec in "${SPECS[@]}"; do
  agent="${spec%%:*}"; model=""
  [[ "$spec" == *:* ]] && model="${spec#*:}"
  label="$agent"; [[ -n "$model" ]] && label="${agent}_$(echo "$model" | tr ' /' '__')"
  out="$OUT_DIR/${label}.md"
  run_agent "$agent" "$model" "$out" "$OUT_DIR/.meta/${label}.meta" &
  PIDS+=("$!"); LABELS+=("$label")
done

for pid in "${PIDS[@]}"; do wait "$pid" || true; done

# --- aggregation: manifest.tsv + short output detection ---
labels=(); ag=(); mo=(); ecf=(); du=(); ln=()
for label in "${LABELS[@]}"; do
  meta="$OUT_DIR/.meta/${label}.meta"; out="$OUT_DIR/${label}.md"
  a=""; m=""; e=""; d="0"
  [[ -f "$meta" ]] && IFS=$'\t' read -r a m e d < "$meta"
  [[ "$m" == "-" ]] && m=""   # map placeholder back to empty model
  l=$(wc -l < "$out" 2>/dev/null || echo 0); l="${l//[^0-9]/}"; l="${l:-0}"
  labels+=("$label"); ag+=("${a:-?}"); mo+=("$m"); ecf+=("${e:-?}"); du+=("${d:-0}"); ln+=("$l")
done

# line median over usable outputs (exit 0) → relative threshold for "SHORT"
elig=(); for i in "${!labels[@]}"; do [[ "${ecf[$i]}" == "0" ]] && elig+=("${ln[$i]}"); done
median=0
if [[ ${#elig[@]} -gt 0 ]]; then
  mapfile -t sorted < <(printf '%s\n' "${elig[@]}" | sort -n)
  n=${#sorted[@]}; mid=$((n/2))
  if (( n % 2 == 1 )); then median="${sorted[$mid]}"; else median=$(( (sorted[mid-1] + sorted[mid]) / 2 )); fi
fi
thr=$(( median / 5 ))   # 20% of median

MAN="$OUT_DIR/manifest.tsv"
printf 'agent\tmodel\tstatus\texit\tduration_s\tlines\n' > "$MAN"
rc=0; short_list=""
for i in "${!labels[@]}"; do
  status="OK"
  if [[ "${ecf[$i]}" == "SKIP" ]]; then status="SKIP"
  elif [[ "${ecf[$i]}" != "0" ]]; then status="FAIL"; rc=1
  elif (( ln[i] < 8 )) || { (( median > 0 )) && (( ln[i] < thr )); }; then status="SHORT"; short_list+=" ${ag[$i]}${mo[$i]:+:${mo[$i]}}"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "${ag[$i]}" "${mo[$i]}" "$status" "${ecf[$i]}" "${du[$i]}" "${ln[$i]}" >> "$MAN"
done

echo "" >&2
echo "Done. Intermediate solutions (left for inspection):" >&2
ls -1 "$OUT_DIR"/*.md >&2 || true
echo "" >&2
echo "Overview (manifest.tsv):" >&2
column -t -s "$(printf '\t')" "$MAN" >&2 2>/dev/null || cat "$MAN" >&2
[[ -n "$short_list" ]] && echo "⚠️  Suspiciously short output (potentially summarized – check manually):${short_list}" >&2
echo "$OUT_DIR"   # path to stdout for the orchestrator
exit $rc
