import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from web.app import app


def test_recherche_globale_web_accessible():
    app.config["TESTING"] = True

    with app.test_client() as client:
        reponse = client.get("/recherche/globale/temporaire")

    assert reponse.status_code == 200

def test_recherche_categorie_transmet_les_pays(monkeypatch):
    app.config["TESTING"] = True

    monkeypatch.setattr(
        "web.app.rechercher_global",
        lambda terme: [],
    )

    monkeypatch.setattr(
        "web.app.get_pays_par_categorie",
        lambda categorie: [(1, "France")],
    )

    with app.test_client() as client:
        reponse = client.post(
            "/recherche/globale/temporaire",
            data={"terme": "Marché"},
        )

    assert reponse.status_code == 200
    assert b"France" in reponse.data

def test_recherche_pays_transmet_les_territoires(monkeypatch):
    app.config["TESTING"] = True

    monkeypatch.setattr(
        "web.app.rechercher_global",
        lambda terme: [],
    )

    monkeypatch.setattr(
        "web.app.get_pays_par_categorie",
        lambda categorie: [(1, "France")],
    )

    monkeypatch.setattr(
        "web.app.get_territoires_par_categorie_et_pays",
        lambda categorie, pays: [(1, "La Réunion")],
    )

    with app.test_client() as client:
        response = client.post(
            "/recherche/globale/temporaire",
            data={
                "terme": "Marché",
                "pays": "France",
            },
        )

    assert response.status_code == 200
    assert b"La R\xc3\xa9union" in response.data

def test_recherche_territoire_transmet_les_villes(monkeypatch):
    app.config["TESTING"] = True

    monkeypatch.setattr(
        "web.app.rechercher_global",
        lambda terme: [],
    )

    monkeypatch.setattr(
        "web.app.get_pays_par_categorie",
        lambda categorie: [(1, "France")],
    )

    monkeypatch.setattr(
        "web.app.get_territoires_par_categorie_et_pays",
        lambda categorie, pays: [(1, "La Réunion")],
    )

    monkeypatch.setattr(
        "web.app.get_villes_par_categorie_pays_territoire",
        lambda categorie, pays, territoire: [
            (1, "Saint-Pierre"),
        ],
    )

    with app.test_client() as client:
        response = client.post(
            "/recherche/globale/temporaire",
            data={
                "terme": "Marché",
                "pays": "France",
                "territoire": "La Réunion",
            },
        )

    assert response.status_code == 200
    assert b"Saint-Pierre" in response.data


def test_recherche_ville_transmet_les_lieux(monkeypatch):
    app.config["TESTING"] = True

    monkeypatch.setattr(
        "web.app.rechercher_global",
        lambda terme: [],
    )

    monkeypatch.setattr(
        "web.app.get_pays_par_categorie",
        lambda categorie: [(1, "France")],
    )

    monkeypatch.setattr(
        "web.app.get_territoires_par_categorie_et_pays",
        lambda categorie, pays: [(1, "La Réunion")],
    )

    monkeypatch.setattr(
        "web.app.get_villes_par_categorie_pays_territoire",
        lambda categorie, pays, territoire: [
            (1, "Saint-Pierre"),
        ],
    )

    monkeypatch.setattr(
        "web.app.get_lieux_par_categorie_pays_territoire_ville",
        lambda categorie, pays, territoire, ville: [
            (1, "Marché de Saint-Pierre"),
        ],
    )

    with app.test_client() as client:
        response = client.post(
            "/recherche/globale/temporaire",
            data={
                "terme": "Marché",
                "pays": "France",
                "territoire": "La Réunion",
                "ville": "Saint-Pierre",
            },
        )

    assert response.status_code == 200
    assert b"March\xc3\xa9 de Saint-Pierre" in response.data


def test_recherche_categorie_propose_plusieurs_pays(monkeypatch):
    app.config["TESTING"] = True

    monkeypatch.setattr(
        "web.app.rechercher_global",
        lambda terme: [],
    )

    monkeypatch.setattr(
        "web.app.get_pays_par_categorie",
        lambda categorie: [
            (1, "France"),
            (2, "Australie"),
        ],
    )

    with app.test_client() as client:
        reponse = client.post(
            "/recherche/globale/temporaire",
            data={
                "terme": "Marché",
            },
        )

    assert reponse.status_code == 200
    assert b"France" in reponse.data
    assert b"Australie" in reponse.data


def test_recherche_australie_transmet_uniquement_ses_territoires(
    monkeypatch,
):
    app.config["TESTING"] = True

    monkeypatch.setattr(
        "web.app.rechercher_global",
        lambda terme: [],
    )

    monkeypatch.setattr(
        "web.app.get_contexte_recherche",
        lambda terme: {
            "pays": [],
            "regions": [],
            "villes": [],
            "categories": [],
            "lieux": [],
        },
    )

    monkeypatch.setattr(
        "web.app.get_pays_par_categorie",
        lambda categorie: [
            (1, "France"),
            (2, "Australie"),
        ],
    )

    monkeypatch.setattr(
        "web.app.get_territoires_par_categorie_et_pays",
        lambda categorie, pays: (
            [(2, "Queensland")]
            if pays == "Australie"
            else [(1, "La Réunion")]
        ),
    )

    with app.test_client() as client:
        response = client.post(
            "/recherche/globale/temporaire",
            data={
                "terme": "Marché",
                "pays": "Australie",
            },
        )

    assert response.status_code == 200
    assert b"Queensland" in response.data
    assert b"La R\xc3\xa9union" not in response.data

def test_recherche_globale_transmet_contexte(monkeypatch):
    app.config["TESTING"] = True

    monkeypatch.setattr(
        "web.app.rechercher_global",
        lambda terme: [],
    )

    monkeypatch.setattr(
        "web.app.get_contexte_recherche",
        lambda terme: {
            "pays": [(1, "PAYS_TEST")],
            "regions": [(2, "REGION_TEST")],
            "villes": [(3, "VILLE_TEST")],
            "categories": [(4, "CATEGORIE_TEST")],
            "lieux": [(5, "LIEU_TEST")],
        },
    )

    monkeypatch.setattr(
        "web.app.get_pays_par_categorie",
        lambda terme: [],
    )

    with app.test_client() as client:
        response = client.post(
            "/recherche/globale/temporaire",
            data={
                "terme": "TEST_CONTEXTE",
            },
        )

    assert response.status_code == 200

def test_recherche_territoire_transmet_ses_villes(monkeypatch):
    app.config["TESTING"] = True

    monkeypatch.setattr(
        "web.app.rechercher_global",
        lambda terme: [],
    )

    monkeypatch.setattr(
        "web.app.get_contexte_recherche",
        lambda terme: {
            "pays": [],
            "regions": [],
            "villes": [],
            "categories": [],
            "lieux": [],
        },
    )

    monkeypatch.setattr(
        "web.app.get_pays_par_categorie",
        lambda categorie: [(1, "France")],
    )

    monkeypatch.setattr(
        "web.app.get_territoires_par_categorie_et_pays",
        lambda categorie, pays: [(1, "La Réunion")],
    )

    monkeypatch.setattr(
        "web.app.get_villes_par_categorie_pays_territoire",
        lambda categorie, pays, territoire: [
            (1, "Saint-Denis"),
            (2, "Saint-Pierre"),
        ],
    )

    with app.test_client() as client:
        response = client.post(
            "/recherche/globale/temporaire",
            data={
                "terme": "Agriculture",
                "pays": "France",
                "territoire": "La Réunion",
            },
        )

    assert response.status_code == 200
    assert b"Saint-Denis" in response.data
    assert b"Saint-Pierre" in response.data

def test_formulaire_ville_conserve_territoire():
    from pathlib import Path

    template = (
        Path(__file__).resolve().parents[1]
        / "web"
        / "templates"
        / "recherche_globale.html"
    )

    contenu = template.read_text(encoding="utf-8")

    assert 'name="territoire"' in contenu
    assert 'value="{{ territoire_selectionne }}"' in contenu
    assert 'name="ville"' in contenu


