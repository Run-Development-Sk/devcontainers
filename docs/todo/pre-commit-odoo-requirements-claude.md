**=+=+=+=+=+= PROMPT =+=+=+=+=+=**

Ako docieliť aby pre-commit kontroly python kódu v tomto projekte chápali že tieto requirements: https://github.com/odoo/odoo/blob/19.0/requirements.txt sú nainštalované a dostupné keďže sa nachádzame v decker kontajneri Odoo 19 CE ... ?

**=+=+=+=+=+= RESPONSE =+=+=+=+=+=**

Preveril som aktuálny stav priamo v kontajneri (spustil som len read-only kontroly, nič som nemenil).

## Krátka odpoveď: už to funguje — a mechanizmus je `language: system`

Pylint hook v [.pre-commit-config.yaml](.pre-commit-config.yaml) beží ako `language: system`, takže pre-commit mu **nevytvára izolovaný venv**, ale spustí `pylint` z `PATH`. Ten má shebang `/usr/bin/python3`, čiže vidí:

```
/home/developer/.local/lib/python3.12/site-packages   ← pylint, ruff, pytest, playwright
/usr/lib/python3/dist-packages                        ← odoo 19.0 + celý requirements.txt
```

Overené empiricky — `pylint` nad všetkými 126 `.py` v `extra-addons` + `tests` s **vypnutým** `ignored-modules` a **zapnutým** `import-error` nehlási ani jeden nevyriešený import z `odoo/requirements.txt` (`lxml`, `psycopg2`, `werkzeug`, `reportlab`, `PIL`, `babel`, `requests`, …).

Kľúčové je, že [.devcontainer/requirements.txt](.devcontainer/requirements.txt) inštaluje lint nástroje cez `pip install --break-system-packages` do **toho istého** interpretera, kde je Odoo. To je celá „mágia" — netreba žiadny `PYTHONPATH`, žiaden `additional_dependencies`.

**Ruff to nepotrebuje vôbec** — je to čisto statický analyzátor, nikdy nič neimportuje. Aj isort klasifikáciu robí heuristicky a odoo závislosti zaraďuje správne (overené: `psycopg2`, `werkzeug`, `lxml`, `reportlab` → third-party, `odoo` → first-party podľa `known-first-party`).

## Čo tooling naozaj „nechápe" (a nesúvisí s requirements.txt)

Odoo 19 je PEP 420 **namespace package** — `/usr/lib/python3/dist-packages/odoo/` nemá `__init__.py` (init je v `odoo/init.py`). Submoduly ako `odoo.models`, `odoo.fields`, `odoo.api`, `odoo.exceptions` sú reálne súbory a rezolvujú sa. Dynamicky doplnené mená nie. Celý rozsah slepej škvrny v projekte je presne 17 hlásení:

| Hlásenie                                                         | Počet |
| ---------------------------------------------------------------- | ----- |
| `E0611: No name '_' in module 'odoo'`                            | 13    |
| `E0611: No name 'SUPERUSER_ID' / 'Command' in module 'odoo'`     | 2     |
| `E0611/E0401` na `odoo.addons.excise_tax.*` (cross-addon import) | 2     |

Práve toto je dôvod, prečo v [pyproject.toml](pyproject.toml) existuje `[tool.pylint.typecheck] ignored-modules = ["odoo"]`. Je to funkčné, ale hrubé kladivo — vypne kontrolu importov pre _celý_ `odoo` namespace.

## Čo by som (voliteľne) upravil

1. **Zúžiť `ignored-modules`** z `["odoo"]` na `["odoo.addons"]` a namiesto zvyšku pridať do disable listu `no-name-in-module`, prípadne nechať `ignored-modules` a len doplniť komentár, že ide o namespace package, nie o chýbajúce requirements. Získa sa tým kontrola importov naprieč `odoo.*` submodulmi, stratí sa detekcia preklepu v `from odoo import _`.
2. **Poistka proti behu mimo kontajnera** — `language: system` mimo devcontainera tíško degraduje (buď `pylint: command not found`, alebo pylint bez Odoo → záplava `import-error`). Dá sa pridať jednoriadkový `entry`, ktorý najprv overí `python3 -c "import odoo"` a inak zrozumiteľne padne.
3. **`--disable=import-error` v hooku `pylint-tests` je dnes mŕtvy** — playwright aj `_wms_helpers` sa rezolvujú (komentár tvrdí, že playwright žije v `tests/e2e/.venv-e2e`, ale post-create ho inštaluje aj globálne). Nechať ako lacnú poistku pre klon mimo devcontainera, alebo zmazať a opraviť komentár.

## Dva nálezy mimo zadania

- `pre-commit run pylint-tests --all-files` **aktuálne padá** na reálnej chybe, nie na importoch: [test_fix_request_lifecycle.py:59](tests/e2e/03_stock/wms_edit_mode/test_fix_request_lifecycle.py#L59) — `E1123: Unexpected keyword argument 'company_name'`.
- [.devcontainer/requirements.txt](.devcontainer/requirements.txt) pinuje `ruff==0.7.4`, zatiaľ čo pre-commit používa `rev: v0.16.1` — komentár tvrdí „versions aligned", ale nie sú.

Mám niektorú z tých úprav zapracovať?
