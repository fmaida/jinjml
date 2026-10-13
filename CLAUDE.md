# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Cos'è

Libreria Python che trasforma un template email scritto in MJML, con dentro
placeholder, cicli e condizionali Jinja2, in HTML pronto da inviare.
Pipeline in due passi: **file template → Jinja2 → testo MJML → `mjml2html` → HTML**.

## Contesto d'uso

La libreria si occupa solo del rendering e verrà inglobata da un'altra app
Python, che è responsabile dell'invio: costruisce il messaggio, lo spedisce via
SMTP e ne salva una copia in "Posta inviata" via IMAP. Quell'app fornisce il
dizionario `vars`, che oltre a `email` (destinatario) contiene anche l'oggetto e
il nome completo del mittente, e possiede i dati di connessione SMTP e IMAP.

Il perimetro è volutamente ristretto: **template + dizionario → corpo HTML**,
nient'altro. Non aggiungere né proporre qui costruzione del messaggio
(`EmailMessage`, intestazioni, versione solo testo), invio, codice di rete,
credenziali o controlli su chiavi diverse da `email`: tutto questo appartiene
all'app che usa la libreria.

## Comandi

Progetto Poetry con layout `src/`; il virtualenv è in `.venv/` nel progetto.

```bash
poetry install                                           # dipendenze + pacchetto jinjml
poetry run pytest                                        # tutti i test
poetry run pytest tests/test_jinjml.py::test_for_loop    # un solo test
poetry run pytest -k autoescape                          # test per nome
```

`poetry add` installa le dipendenze ma non il pacchetto stesso: se i test
falliscono con `ModuleNotFoundError: No module named 'jinjml'`, manca un
`poetry install`.

Non c'è nessun linter o formatter configurato.

## Vincoli di piattaforma

- Deve restare installabile senza compilare nulla su **macOS 26** e
  **Debian 13**. Per questo `requires-python` è `>=3.13` (il Python di serie su
  Debian 13): non usare sintassi o API successive al 3.13, anche se in locale si
  sviluppa con una versione più recente.
- Prima di aggiungere una dipendenza con codice nativo, verificare su PyPI che
  abbia wheel binarie per macOS (arm64/x86_64) e Linux glibc (x86_64/aarch64).

## Architettura

Tutta la logica è nella classe `JinJML` in `src/jinjml/jinjml.py`
(`JinJML(template: Path, vars: dict).process() -> str`), riesportata da
`src/jinjml/__init__.py`. Le scelte seguenti sono deliberate:

- **`email` è l'unica chiave obbligatoria** di `vars`: se manca o è vuota viene
  sollevato `JinJML.MissingEmailField`. Il controllo avviene sia in `__init__` sia in
  `process()`, perché `vars` è un attributo pubblico mutabile.
- **Le altre variabili sono facoltative**: si usa l'`Undefined` standard di
  Jinja2 (stringa vuota, falso negli `if`), non `StrictUndefined`.
- **Autoescape sempre attivo**, impostato con `autoescape=True` e non con
  `select_autoescape`, che non riconoscerebbe l'estensione `.mjml`. Serve a
  evitare che un `&` o un `<` in un valore rompa l'XML di MJML; per HTML voluto
  il template usa `|safe`.
- **`FileSystemLoader` sulla cartella del template**, così `{% include %}` ed
  `{% extends %}` risolvono i file vicini al template.
- **Scatola nera per l'app**: chi usa la libreria non deve sapere che dentro ci
  sono due librerie. L'interfaccia pubblica è la sola classe `JinJML`, unico
  nome esportato da `src/jinjml/__init__.py`. Nessun tipo di `jinja2` o `mjml`
  deve uscire dalla libreria, e i test non li importano.
- **JinJML si prende la responsabilità di ogni errore** e lo notifica al
  chiamante con una propria eccezione, senza tentare rimedi né restituire
  risultati parziali. Le eccezioni sono classi annidate in `JinJML`, così
  l'app scrive `except JinJML.FileNotFound` senza altri import:
  `Error` (base, le prende tutte), `MissingEmailField`, `FileNotFound`,
  `FileNotReadable`, `InvalidSyntax`, `RenderError`, `InvalidMJML`. Ognuna
  porta l'errore originale in `__cause__` e il percorso in `.template`.
  Ogni nuovo caso d'errore deve avere la sua sottoclasse di `JinJML.Error`:
  l'app non deve mai dover analizzare un'eccezione generica.
- In `process()` l'ordine degli `except` conta (`TemplateNotFound` di Jinja è
  sottoclasse di `OSError`) e gli ultimi sono volutamente larghi
  (`except Exception`), perché le espressioni di un template possono
  sollevare qualsiasi cosa.
- `template` può essere anche una stringa: `process()` la converte in `Path`.

## Dipendenza MJML: attenzione al nome

Il pacchetto usato è **`mjml-python`** (wrapper di MRML, porting Rust di MJML),
che si importa come `mjml` ed espone `mjml2html`. Su PyPI esiste anche un
pacchetto diverso chiamato `mjml` (porting in Python puro, funzione
`mjml_to_html`): non va confuso né installato insieme, perché occupa lo stesso
nome di modulo.

## Convenzioni

- Commenti nel codice e messaggi delle eccezioni sono in italiano.
- I test scrivono template MJML minimi in `tmp_path` tramite l'helper
  `write_template` di `tests/test_jinjml.py`; non ci sono fixture su file.
