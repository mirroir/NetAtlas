from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = (
    Path(__file__).resolve().parents[1]
    / "web"
    / "templates"
)


def test_formulaire_ville_conserve_territoire():
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
    )

    template = env.get_template("recherche_globale.html")

    html = template.render(
        terme="Agriculture",
        origine="utilisateur",
        pays_categorie=[],
        territoires_categorie=[],
        villes_categorie=[(1, "Saint-Pierre")],
        lieux_categorie=[],
        pays_selectionne="France",
        territoire_selectionne="La Réunion",
        ville_selectionnee="",
        resultats_principaux=[],
        resultats_secondaires=[],
        url_for=lambda endpoint, **kwargs: "/test",
    )

    assert 'name="territoire"' in html
    assert 'value="La Réunion"' in html
    assert 'name="ville"' in html
    assert 'value="Saint-Pierre"' in html


def test_lieu_cliquable_vers_fiche_detail():
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
    )

    template = env.get_template("recherche_globale.html")

    def fake_url_for(endpoint, **kwargs):
        if endpoint == "detail_lieu":
            return (
                f"/lieu/{kwargs['place_id']}/"
                f"{kwargs['origine']}"
            )
        return "/test"

    html = template.render(
        terme="Agriculture",
        origine="utilisateur",
        pays_categorie=[],
        territoires_categorie=[],
        villes_categorie=[],
        lieux_categorie=[(1, "Marché de Saint-Pierre")],
        pays_selectionne="France",
        territoire_selectionne="La Réunion",
        ville_selectionnee="Saint-Pierre",
        resultats_principaux=[],
        resultats_secondaires=[],
        url_for=fake_url_for,
    )

    assert "Marché de Saint-Pierre" in html
    assert 'href="/lieu/1/utilisateur"' in html


