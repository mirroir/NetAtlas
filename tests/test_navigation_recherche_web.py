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

def test_suggestions_geographiques_masquent_resultats_secondaires():
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
    )

    template = env.get_template("recherche_globale.html")

    html = template.render(
        terme="Marché",
        origine="temporaire",
        pays_categorie=[(1, "France")],
        territoires_categorie=[],
        villes_categorie=[],
        lieux_categorie=[],
        pays_selectionne="",
        territoire_selectionne="",
        ville_selectionnee="",
        resultats_principaux=[],
        resultats_secondaires=[
            (1, "Lieu secondaire", "Saint-Pierre",
             "Marché", None, None, None, 0.30)
        ],
        url_for=lambda endpoint, **kwargs: "/test",
    )

    assert "Pays disponibles" in html
    assert "résultat(s) moins pertinent(s)" not in html
    assert "Afficher les autres résultats" not in html

def test_resultats_secondaires_visibles_sans_suggestion_geographique():
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
    )

    template = env.get_template("recherche_globale.html")

    html = template.render(
        terme="Marche approximatif",
        origine="temporaire",
        pays_categorie=[],
        territoires_categorie=[],
        villes_categorie=[],
        lieux_categorie=[],
        pays_selectionne="",
        territoire_selectionne="",
        ville_selectionnee="",
        resultats_principaux=[],
        resultats_secondaires=[
            (1, "Lieu secondaire", "Saint-Pierre",
             "Marché", None, None, None, 0.30)
        ],
        url_for=lambda endpoint, **kwargs: "/test",
    )

    assert "résultat(s) moins pertinent(s)" in html
    assert "Afficher les autres résultats" in html
    assert "Lieu secondaire" in html


