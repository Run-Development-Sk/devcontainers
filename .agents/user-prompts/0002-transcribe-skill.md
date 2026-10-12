V priečinku `dc-stretnutie-261009` sú video a zvukové záznamy (.mp4, .m4a) zo stretnutia s klientom K&K Import Export. Je to firma, ktorá nakupuje a predáva alkohol. Na stretnutí sme hovorili o požiadavkách na nový informačný systém skladového hospodárstva a o legislatívnych povinnostiach, ktoré má systém pokryť. Spomínali sa mená Tomáš, Ivana a Zboňák („Zboňo“).

Potrebujem z týchto záznamov textové prepisy, v ktorých sú rozlíšení jednotliví hovoriaci. Postup chcem mať zabalený ako znovupoužiteľný skill `run-transcribe` s commandom `/run.transcribe`, vytvorený podľa `/run-add-agent-asset`. Má fungovať v Claude Code, Auggie aj Codexe. Subagentov nechcem definovať v `.agents/agents`.

**Vstup skillu**

- priečinok s video alebo zvukovými súbormi, alebo jeden súbor,
- téma rozhovoru a voliteľne zoznam mien a odborných pojmov,
- jazyk nahrávky, predvolene slovenčina.

**Prepis**

- Zvuk z videa vyber cez ffmpeg. Ak majú nahrávky zbytočne vysoký bitrate, zníž ho tak, aby sa zmenšila veľkosť, ale zrozumiteľnosť reči ostala nedotknutá.
- Na prepis použi OpenAI API s modelom `gpt-4o-transcribe-diarize`. API kľúč je v `.devcontainer/.env` ako `OPENAI_API_KEY_TRANSCRIBE`.
- Nahrávky rozdeľ na menšie časti, ktoré API zvládne. Strih vždy urob v najbližšej pauze, aby sa neporušilo žiadne slovo.
- Prepisy častí spoj do jedného .md súboru pre každú nahrávku, uloženého vedľa nej. Medzi časti vlož oddeľovač `=+=+=+=+=+=`.
- Mená hovoriacich v prepise nechcem. Zodpovedajúce si označenia hovoriacich medzi časťami priradím ručne.
- Potrebné Python balíky si skill nainštaluje sám, ak chýbajú. Do `requirements.txt` ich zatiaľ nepridávaj.

**Upravená verzia**

- Záznamy sú z rušného prostredia a ľudia často hovoria cez seba, takže surový prepis je chaotický. Ku každému prepisu chcem aj upravenú, čitateľnú verziu.
- Upravená verzia má byť **verný upravený prepis**: zachová všetok obsah a poradie, nič nezhŕňa ani nedopĺňa. Spojí roztrhané vety, odstráni vsuvky a opraví zjavne zle rozpoznané slová.
- Neisté opravy a nezrozumiteľné miesta nech sú označené jednotnými značkami nezávislými od jazyka. Agent mi na konci vysvetlí ich význam.
- Odborné pojmy a mená zo vstupu majú pomôcť presnejšie rozpoznať slová.
- Ak to pomôže, najprv mi navrhni, ako úpravu robiť, a over to na pilotnej časti.

**Agenti a súbežný beh**

- Výstupné súbory, surový aj upravený, nech majú na konci názvu príponu agenta, ktorý ich vytvoril (`-claude`, `-auggie`, `-codex`, `-agy`), podobne ako v skille `run-save-chat`.
- Viac agentov má vedieť spracovať tie isté nahrávky súbežne a nezávisle, aby sa ich výsledky dali porovnať. Každý agent preto robí vlastný prepis a má vlastné pracovné súbory.

**Pracovné súbory a opakovaný beh**

- Pracovné súbory pod `tmp/` nech po skončení ostanú, aby sa dali pozrieť priebežné výsledky. Agent ma na konci upozorní, kde sú, a že ich môžem zmazať.
- Prerušený beh má pokračovať tam, kde skončil, bez opakovaného platenia za hotovú prácu.
- Ak ten istý agent spracúva nahrávku, ktorú už spracoval, nech sa ma spýta, či chcem:

  - pokračovať a použiť predošlý výsledok,
  - urobiť nový nezávislý prepis,
  - urobiť len novú úpravu.

  Ak už výstupy existujú, nech sa spýta aj na to, či ich prepísať, alebo ponechať.

- Ak sa nahrávka zmenila, alebo sa mení téma, pojmy či jazyk oproti predošlému behu, nech to agent zistí a spýta sa ma, čo ďalej. Nič nemaže bez opýtania.

**Bezpečnosť a priebeh**

- Pred odoslaním nahrávok do OpenAI nech mi agent ukáže dĺžku nahrávok a odhad ceny a počká na potvrdenie, pokiaľ som beh nepotvrdil už v zadaní.
- API kľúč sa nikdy nesmie zobraziť.
- Skill má dobehnúť celý aj vtedy, keď ho spustím neinteraktívne.

**Zatiaľ neriešiť**

- automatické hodnotenie kvality prepisu a vynechanie úpravy pri dostatočne kvalitnom prepise,
- spoločný prepis všetkých nahrávok.

Najprv tento zámer pripomienkuj, polož otázky, ak nejaké máš, a navrhni vylepšenia. Až potom implementuj.
