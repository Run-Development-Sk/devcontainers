**=+=+=+=+=+= PROMPT =+=+=+=+=+=**

Ako docieliť aby pre-commit kontroly python kódu v tomto projekte chápali že tieto requirements: https://github.com/odoo/odoo/blob/19.0/requirements.txt sú nainštalované a dostupné keďže sa nachádzame v decker kontajneri Odoo 19 CE ... ?

**=+=+=+=+=+= RESPONSE =+=+=+=+=+=**

## Krátka odpoveď

Nič netreba „doinštalovať" – v tomto projekte to už funguje. Overil som to priamo v kontajneri:

| Nástroj                | Rieši importy?                             | Stav                                                                                                                                                                                                               |
| ---------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ruff (check aj format) | **Nie** – čisto AST, nikdy nič neimportuje | netreba nič                                                                                                                                                                                                        |
| pylint / astroid       | **Áno**                                    | `language: system` → beží nad `/usr/bin/python3`, ktorý má `/usr/lib/python3/dist-packages` na `sys.path`, teda vidí aj `odoo`, aj celý `requirements.txt` (lxml, werkzeug, requests, psycopg2, babel, reportlab…) |

Kontrolné behy (bez projektovej konfigurácie, `--rcfile=/dev/null`):

- `from odoo import models, fields`, `from odoo.addons.stock.models.stock_move import StockMove`, `import requests`, `import playwright.sync_api` → **0 chýb** `E0401/E0611`
- celé `tests/e2e/` (87 súborov) so **zapnutým** `import-error` → **0 chýb**

Takže požiadavka „aby pre-commit chápal, že requirements sú nainštalované" je splnená už samotným `language: system` – to je presne ten správny mechanizmus. Opak (`additional_dependencies` s Odoo requirements) by bol chybný: pre-commit by staval izolovaný venv a duplikoval by kontajnerové prostredie.

## Čo v konfigurácii je _navyše_ a čo naopak nutné

Dve zo súčasných „obchádzok" už nie sú potrebné a maskujú reálne chyby:

<augment_code_snippet path=".pre-commit-config.yaml" mode="EXCERPT">

```yaml
entry: >-
  pylint
  --disable=duplicate-code,redefined-outer-name,wrong-import-position,import-error,global-statement
```

</augment_code_snippet>

- `import-error` v hooku `pylint-tests` – overené, že bez neho neprejde ani jedna chyba; playwright aj `_wms_helpers` sa rozlíšia (playwright je nainštalovaný aj systémovo, nielen v `.venv-e2e`). Dá sa vypustiť → získate detekciu preklepov v importoch v testoch.

Naopak toto **nutné je** a treba to nechať:

<augment_code_snippet path="pyproject.toml" mode="EXCERPT">

```toml
[tool.pylint.typecheck]
ignored-modules = ["odoo"]
```

</augment_code_snippet>

Dôvod nie je „chýbajúce requirements", ale to, že `odoo` v 19.0 **nemá `__init__.py`** – je to implicitný _namespace package_ (`odoo.__file__ is None`). Symboly ako `_`, `SUPERUSER_ID`, `Command` sa doň vkladajú až za behu, takže staticky neexistujú. Bez tohto riadku dostanete napr.:

```
E0611: No name '_' in module 'odoo' (no-name-in-module)
```

Rovnaký namespace mechanizmus spôsobuje, že sa nerozlíši ani import naprieč vlastnými modulmi – jediný výskyt v projekte je `excise_tax_return/models/excise_tax_return_dashboard.py:8` (`from odoo.addons.excise_tax.models.excise_tax import …`); dnes ho ticho prekrýva práve `ignored-modules`.

## Ak by ste chceli ísť ďalej (voliteľné)

1. **Rozlíšenie vlastných addonov** bez `ignored-modules`: stačí tieňový strom na `sys.path`, lebo `odoo.addons` je namespace – overil som, že to funguje:
   ```
   tmp/pylint-path/odoo/addons/<modul> -> extra-addons/<modul>   (symlinky)
   init-hook = 'import sys; sys.path.insert(0, "tmp/pylint-path")'
   ```
   Import `odoo.addons.excise_tax…` sa potom rozlíši. Podľa YAGNI to pre jediný výskyt zrejme nestojí za réžiu udržiavania symlinkov.
2. **Odolnosť voči nesprávnemu interpretu**: `entry: python3 -m pylint` namiesto `entry: pylint` zaručí, že sa nikdy nepoužije pylint z iného venv-u.
3. **CI**: momentálne žiadny workflow pre-commit nespúšťa (`bootstrap-isdev.yml`, `deploy-isdev.yml` – len pytest/playwright). Ak by ste lint pridali do GitHub Actions, _tam_ bude predpoklad „requirements sú dostupné" neplatný – job musí bežať v Odoo 19 image, inak `pylint` zaplaví `E0401`. Alternatíva pre CI: hooky `ruff` + prettier + OCA áno, `pylint` nechať iba lokálne (`stages: [manual]` alebo skip cez `SKIP=pylint`).

Nič som v projekte nemenil – všetky testy bežali read-only, symlinky som vytváral v `/tmp`. Ak chcete, viem aplikovať bod 2 a odstránenie `import-error` z `pylint-tests`.

**=+=+=+=+=+= PROMPT =+=+=+=+=+=**

# /run.save-chat – Save entire chat history to .md

Follow the procedure according to the **`run-save-chat`** skill (`.agents/skills/run-save-chat/SKILL.md`). The command and the skill have the same output; this command is the entry point for Claude Code, Auggie, and Antigravity. (Codex does not support slash commands – use the `run-save-chat` skill directly there.)

In short (details in the skill):

1. Determine the agent's suffix (`auggie` / `claude` / `agy` / `codex`).
2. Determine the target path:
   - without an argument -> ask the user whether to auto-generate the name (slug from the conversation topic, folder `tmp/`) or if they want to enter it,
   - name without a folder -> folder `tmp/`,
   - name with a folder -> stays in that folder,
   - missing extension -> append `.md`.
3. Add the suffix `-<agent>` before `.md` (e.g., `my-chat-auggie.md`).
4. Write the **literal** (verbatim) content of the entire conversation – **all** prompts and responses in chronological order, delimited by `PROMPT` / `RESPONSE` separator lines (exact file format in the skill) – and announce the resulting path.

Hard rules: prompts and responses are verbatim, the entire chat history is saved (not just the last turn), the agent suffix is always added, no secrets in the file (`.agents/rules/run.secret-safety.md`).

If the user provided an argument (name, potentially with a folder), narrow the procedure accordingly.

**=+=+=+=+=+= RESPONSE =+=+=+=+=+=**

Chat je uložený: `tmp/precommit-odoo-requirements-auggie.md`
