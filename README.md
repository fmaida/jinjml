# JinJML

Trasforma un template email scritto in [MJML](https://mjml.io), con dentro
placeholder, cicli e condizionali [Jinja2](https://jinja.palletsprojects.com),
nel corpo HTML del messaggio.

Riceve il percorso del template e un dizionario di valori, restituisce l'HTML.
Non invia email: di quello si occupa l'applicazione che usa la libreria.

## Esempio

`benvenuto.mjml`:

```xml
<mjml>
  <mj-body>
    <mj-section>
      <mj-column>
        <mj-text>Ciao {{ nome }}, ecco i tuoi ordini:</mj-text>
        {% for ordine in ordini %}
        <mj-text>- {{ ordine }}</mj-text>
        {% endfor %}
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>
```

```python
from pathlib import Path

from jinjml import JinJML

dati = {"email": "mario@example.com", "nome": "Mario", "ordini": ["A12", "B34"]}

try:
    html = JinJML(Path("benvenuto.mjml"), dati).process()
except JinJML.FileNotFound:
    ...  # percorso del template sbagliato
except JinJML.MissingEmailField:
    ...  # nel dizionario manca "email"
except JinJML.Error as errore:
    ...  # qualsiasi altro problema
```

Nel dizionario è obbligatoria solo la chiave `email`; le altre variabili, se
assenti, diventano testo vuoto. I valori vengono sottoposti a escape HTML:
per inserire HTML voluto si usa `{{ valore|safe }}`.

## Errori

Ogni problema viene segnalato con un'eccezione di JinJML:
`MissingEmailField`, `FileNotFound`, `FileNotReadable`, `InvalidSyntax`,
`RenderError`, `InvalidMJML`. Derivano tutte da `JinJML.Error`.

Richiede Python 3.13 o successivo.
