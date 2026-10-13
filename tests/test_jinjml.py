import os
from pathlib import Path

import pytest

from jinjml import JinJML


def write_template(tmp_path: Path, body: str, name: str = "mail.mjml") -> Path:
    template = tmp_path / name
    template.write_text(
        "<mjml><mj-body><mj-section><mj-column>"
        f"{body}"
        "</mj-column></mj-section></mj-body></mjml>",
        encoding="utf-8",
    )
    return template


def test_placeholder(tmp_path):
    template = write_template(tmp_path, "<mj-text>Ciao {{ email }}</mj-text>")
    html = JinJML(template, {"email": "mario@example.com"}).process()
    assert html.startswith("<!doctype html>")
    assert "Ciao mario@example.com" in html
    assert "mj-text" not in html


def test_for_loop(tmp_path):
    template = write_template(
        tmp_path,
        "{% for item in items %}<mj-text>- {{ item }}</mj-text>{% endfor %}",
    )
    html = JinJML(
        template, {"email": "mario@example.com", "items": ["uno", "due", "tre"]}
    ).process()
    assert "- uno" in html
    assert "- due" in html
    assert "- tre" in html


@pytest.mark.parametrize(
    ("premium", "expected", "unexpected"),
    [(True, "Cliente premium", "Cliente standard"),
     (False, "Cliente standard", "Cliente premium")],
)
def test_if_else(tmp_path, premium, expected, unexpected):
    template = write_template(
        tmp_path,
        "<mj-text>{% if premium %}Cliente premium{% else %}Cliente standard{% endif %}</mj-text>",
    )
    html = JinJML(template, {"email": "mario@example.com", "premium": premium}).process()
    assert expected in html
    assert unexpected not in html


def test_missing_optional_var_is_empty(tmp_path):
    template = write_template(
        tmp_path,
        "<mj-text>[{{ nome }}]{% if nome %}presente{% else %}assente{% endif %}</mj-text>",
    )
    html = JinJML(template, {"email": "mario@example.com"}).process()
    assert "[]assente" in html


def test_autoescape(tmp_path):
    template = write_template(
        tmp_path, "<mj-text>{{ azienda }} / {{ grassetto|safe }}</mj-text>"
    )
    html = JinJML(
        template,
        {
            "email": "mario@example.com",
            "azienda": "Rossi & <Figli>",
            "grassetto": "<b>ok</b>",
        },
    ).process()
    assert "Rossi &amp; &lt;Figli&gt;" in html
    assert "<b>ok</b>" in html


def test_include(tmp_path):
    (tmp_path / "firma.mjml").write_text(
        "<mj-text>Scrivici a {{ email }}</mj-text>", encoding="utf-8"
    )
    template = write_template(tmp_path, '{% include "firma.mjml" %}')
    html = JinJML(template, {"email": "mario@example.com"}).process()
    assert "Scrivici a mario@example.com" in html


def test_template_as_str(tmp_path):
    template = write_template(tmp_path, "<mj-text>Ciao {{ email }}</mj-text>")
    html = JinJML(str(template), {"email": "mario@example.com"}).process()
    assert "Ciao mario@example.com" in html


@pytest.mark.parametrize(
    "vars", [{}, {"nome": "Mario"}, {"email": ""}, {"email": None}, None, "mario@example.com"]
)
def test_missing_email_field_in_init(tmp_path, vars):
    template = write_template(tmp_path, "<mj-text>{{ email }}</mj-text>")
    with pytest.raises(JinJML.MissingEmailField, match="email"):
        JinJML(template, vars)


def test_missing_email_field_in_process(tmp_path):
    template = write_template(tmp_path, "<mj-text>{{ email }}</mj-text>")
    jinjml = JinJML(template, {"email": "mario@example.com"})
    del jinjml.vars["email"]
    with pytest.raises(JinJML.MissingEmailField, match="email"):
        jinjml.process()


def assert_wrapped(excinfo, template: Path):
    # L'app deve poter intercettare tutto con JinJML.Error, sapere quale
    # template è coinvolto e risalire all'errore originale
    assert isinstance(excinfo.value, JinJML.Error)
    assert excinfo.value.template == template
    assert template.name in str(excinfo.value)
    assert excinfo.value.__cause__ is not None


def test_file_not_found(tmp_path):
    template = tmp_path / "manca.mjml"
    with pytest.raises(JinJML.FileNotFound) as excinfo:
        JinJML(template, {"email": "mario@example.com"}).process()
    assert_wrapped(excinfo, template)


@pytest.mark.parametrize("template", [None, 42])
def test_file_not_found_when_not_a_path(template):
    with pytest.raises(JinJML.FileNotFound, match="percorso"):
        JinJML(template, {"email": "mario@example.com"}).process()


def test_file_not_found_when_directory(tmp_path):
    template = tmp_path / "cartella.mjml"
    template.mkdir()
    with pytest.raises(JinJML.FileNotFound) as excinfo:
        JinJML(template, {"email": "mario@example.com"}).process()
    assert_wrapped(excinfo, template)


def test_file_not_found_for_include(tmp_path):
    template = write_template(tmp_path, '{% include "firma.mjml" %}')
    with pytest.raises(JinJML.FileNotFound, match="firma.mjml") as excinfo:
        JinJML(template, {"email": "mario@example.com"}).process()
    assert_wrapped(excinfo, template)


@pytest.mark.skipif(
    os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="i permessi di lettura non sono applicabili",
)
def test_file_not_readable(tmp_path):
    template = write_template(tmp_path, "<mj-text>{{ email }}</mj-text>")
    template.chmod(0)
    with pytest.raises(JinJML.FileNotReadable) as excinfo:
        JinJML(template, {"email": "mario@example.com"}).process()
    assert_wrapped(excinfo, template)


def test_file_not_readable_when_not_utf8(tmp_path):
    template = write_template(tmp_path, "<mj-text>perché {{ email }}</mj-text>")
    template.write_bytes(template.read_text(encoding="utf-8").encode("latin-1"))
    with pytest.raises(JinJML.FileNotReadable) as excinfo:
        JinJML(template, {"email": "mario@example.com"}).process()
    assert_wrapped(excinfo, template)


def test_invalid_syntax(tmp_path):
    template = tmp_path / "mail.mjml"
    template.write_text("<mjml>\n<mj-body>\n{% endfor %}\n</mj-body>\n</mjml>", encoding="utf-8")
    with pytest.raises(JinJML.InvalidSyntax, match="alla riga 3") as excinfo:
        JinJML(template, {"email": "mario@example.com"}).process()
    assert_wrapped(excinfo, template)


def test_invalid_syntax_in_include(tmp_path):
    (tmp_path / "firma.mjml").write_text("riga buona\n{% if %}", encoding="utf-8")
    template = write_template(tmp_path, '{% include "firma.mjml" %}')
    with pytest.raises(JinJML.InvalidSyntax, match=r"firma\.mjml alla riga 2") as excinfo:
        JinJML(template, {"email": "mario@example.com"}).process()
    assert excinfo.value.template == template


@pytest.mark.parametrize(
    "body",
    [
        "<mj-text>{{ cliente.nome }}</mj-text>",  # attributo di variabile assente
        "<mj-text>{{ 1 / 0 }}</mj-text>",  # eccezione Python in un'espressione
    ],
)
def test_render_error(tmp_path, body):
    template = write_template(tmp_path, body)
    with pytest.raises(JinJML.RenderError) as excinfo:
        JinJML(template, {"email": "mario@example.com"}).process()
    assert_wrapped(excinfo, template)


@pytest.mark.parametrize(
    "content",
    ["", "ciao {{ email }}", "<mjml><mj-body><mj-text>mai chiuso {{ email }}"],
)
def test_invalid_mjml(tmp_path, content):
    template = tmp_path / "mail.mjml"
    template.write_text(content, encoding="utf-8")
    with pytest.raises(JinJML.InvalidMJML) as excinfo:
        JinJML(template, {"email": "mario@example.com"}).process()
    assert_wrapped(excinfo, template)


def test_invalid_mjml_from_unsafe_value(tmp_path):
    template = write_template(tmp_path, "<mj-text>{{ frammento|safe }}</mj-text>")
    with pytest.raises(JinJML.InvalidMJML):
        JinJML(template, {"email": "mario@example.com", "frammento": "</mj-column>"}).process()


def test_every_error_is_a_jinjml_error():
    for name in ("MissingEmailField", "FileNotFound", "FileNotReadable",
                 "InvalidSyntax", "RenderError", "InvalidMJML"):
        assert issubclass(getattr(JinJML, name), JinJML.Error)
