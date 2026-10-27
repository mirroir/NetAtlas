"""Tests de configuration du reverse proxy Caddy."""

import sys
from pathlib import Path

from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.test import EnvironBuilder

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "web"))

from app import app


def test_proxy_caddy_configuration():
    """NetAtlas utilise un seul reverse proxy de confiance."""

    assert isinstance(app.wsgi_app, ProxyFix)

    assert app.wsgi_app.x_for == 1
    assert app.wsgi_app.x_proto == 1
    assert app.wsgi_app.x_host == 1


def test_proxy_caddy_transmet_https_et_ip_client():
    """Le middleware NetAtlas interprète les en-têtes Caddy."""

    builder = EnvironBuilder(
        path="/",
        base_url="http://127.0.0.1:5000",
        headers={
            "X-Forwarded-For": "192.0.2.42",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "netatlas.home.arpa",
        },
    )

    environnement = builder.get_environ()
    valeurs_recues = {}

    def application(environ, start_response):
        valeurs_recues["ip"] = environ["REMOTE_ADDR"]
        valeurs_recues["protocole"] = environ["wsgi.url_scheme"]
        valeurs_recues["hote"] = environ["HTTP_HOST"]

        start_response(
            "200 OK",
            [("Content-Type", "text/plain")],
        )

        return [b"OK"]

    # Utilise les paramètres du ProxyFix réellement configuré.
    proxy = ProxyFix(
        application,
        x_for=app.wsgi_app.x_for,
        x_proto=app.wsgi_app.x_proto,
        x_host=app.wsgi_app.x_host,
    )

    def demarrer_reponse(status, headers, exc_info=None):
        return None

    list(proxy(environnement, demarrer_reponse))

    assert valeurs_recues == {
        "ip": "192.0.2.42",
        "protocole": "https",
        "hote": "netatlas.home.arpa",
    }
