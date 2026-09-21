---
description: >-
  Default to English for generated code and documentation text regardless of
  the prompt's language, with narrow exceptions for code comments and
  documentation; user-facing UI strings are instead written in the
  application's target-audience language, and agent chat responses always
  follow the language of the user's prompt. Applies to all agents and all
  skills in this workspace.
type: always_apply
trigger: always_on
---

# Rule: language policy

## Code

- Source code and identifiers (variable/function/class/file names, string
  keys, etc.) are **always exclusively in English** - no exceptions,
  regardless of the prompt's language (whether given directly or via a file).
- String literals displayed to the user are the one kind of in-code text this
  does not cover - their language is governed by the UI strings section below.
- Code comments and doc comments (docstrings, JSDoc, Javadoc, XML doc
  comments, etc.) default to English, with the shared exceptions below.

## Documentation and other text

- Default to English, regardless of the prompt's language (direct or via a
  file), with the shared exceptions below.

## Exceptions (documentation text and code comments only, never identifiers or code itself)

- the user **explicitly** requests another language,
- the target unit (document, file, class, or function) is **already entirely
  written/commented** in another language - continue in that language to keep
  that unit consistent (e.g. comments that anchor to a co-located non-English
  scenario/spec document).

## User-facing (UI) strings

- Every string displayed to the user (labels, messages, errors - whether it
  goes through an i18n framework or is written out directly) is in the
  **language of the application's target audience**, not in English by
  default - English applies only when that audience is English-speaking.
- Determine that language from the project itself (its description and
  documentation, the locales of the existing `.po` catalogues, the language of
  strings already present in the code). When it cannot be established that way,
  ask the user and always offer the language they are communicating in as one
  of the options.
- Name the language you settled on in the response, so that a wrong inference
  can be corrected before more strings are added.
- Rationale: the source string must be in the more specific language. Where a
  more inflected language distinguishes several forms, English often has just
  one word, and a single source string cannot be translated into several of
  those forms; the opposite direction always works - several source strings map
  onto the same English word.
- This governs strings you **add or change**; strings you do not touch keep the
  language they are already written in.
- Where the i18n framework uses a symbolic key separate from the source string
  (e.g. `t('user.profile.title')`), that key stays English per the Code section
  above.

## Agent chat responses

- The agent's chat responses (conversational text to the user) are **always
  in the language of the user's prompt**, regardless of the English-by-default
  rules above for code and documentation - these apply only to generated
  code/documentation content, not to the conversational response itself.
