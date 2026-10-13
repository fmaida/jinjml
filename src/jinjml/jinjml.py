from collections.abc import Mapping
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError
from mjml import mjml2html


class JinJML:

    class Error(Exception):
        """Base di tutte le eccezioni di JinJML: intercettandola si prendono tutte.

        template è il percorso del file passato a JinJML; l'errore originale
        resta disponibile in __cause__.
        """

        def __init__(self, message:str, template:Path | None = None):
            super().__init__(message)
            self.template = template

    class MissingEmailField(Error):
        """vars non è un dizionario o non contiene una chiave "email" non vuota.

        Riguarda solo il campo del dizionario: JinJML non verifica che
        l'indirizzo sia valido né che la casella esista.
        """

    class FileNotFound(Error):
        """Il file template, o un file che il template include, non esiste."""

    class FileNotReadable(Error):
        """Il file esiste ma non si può leggere: permessi o codifica non UTF-8."""

    class InvalidSyntax(Error):
        """Placeholder, cicli o condizionali del template sono scritti male."""

    class RenderError(Error):
        """Il template non riesce a usare i dati di vars."""

    class InvalidMJML(Error):
        """Il template, una volta compilato con i dati, non è MJML valido."""

    def __init__(self, template:Path, vars:dict):
        self.template = template
        self.vars = vars
        self._check_vars()

    def _check_vars(self) -> None:
        # Vars deve contenere perlomeno una chiave "email"
        # Altrimenti genera un eccezione
        if not isinstance(self.vars, Mapping) or not self.vars.get("email"):
            raise self.MissingEmailField(
                'vars deve essere un dizionario con una chiave "email" non vuota'
            )

    def process(self) -> str:
        # vars è mutabile: potrebbe essere cambiato dopo __init__
        self._check_vars()
        try:
            template = Path(self.template)
        except TypeError as e:
            raise self.FileNotFound(
                f"template non è un percorso valido: {self.template!r}"
            ) from e
        # Jinja risolve placeholder, cicli e condizionali del template
        # usando vars e restituisce il testo MJML. Il loader punta alla
        # cartella del template, così funzionano anche include ed extends.
        # autoescape esplicito: l'estensione .mjml non lo attiva da sola.
        try:
            env = Environment(
                loader=FileSystemLoader(template.parent),
                autoescape=True,
            )
            mjml_source = env.get_template(template.name).render(self.vars)
        except TemplateNotFound as e:
            # Va prima di OSError, di cui è sottoclasse. e.name è il file
            # cercato: il template stesso oppure uno che il template include
            missing = template.parent / e.name if e.name else template
            included = f" (incluso da {template})" if missing != template else ""
            raise self.FileNotFound(
                f"file non trovato: {missing}{included}", template
            ) from e
        except (OSError, UnicodeDecodeError) as e:
            raise self.FileNotReadable(
                f"impossibile leggere il template {template}: {e}", template
            ) from e
        except TemplateSyntaxError as e:
            # e.filename è il file con l'errore, che può essere un file incluso
            raise self.InvalidSyntax(
                f"errore di sintassi in {e.filename or template} "
                f"alla riga {e.lineno}: {e.message}",
                template,
            ) from e
        except Exception as e:
            # Oltre agli errori di Jinja, le espressioni del template possono
            # sollevare qualsiasi eccezione (es. una divisione per zero)
            raise self.RenderError(
                f"il template {template} non riesce a usare i dati: {e}", template
            ) from e
        # MJML trasforma il testo in HTML pronto per essere inviato per email
        try:
            return mjml2html(mjml_source)
        except Exception as e:
            raise self.InvalidMJML(
                f"il template {template} non produce MJML valido: {e}", template
            ) from e
