import menu


def test_afficher_detail_lieu_recherche_vide(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "")

    menu.afficher_detail_lieu()

    sortie = capsys.readouterr().out
    assert "Recherche vide." in sortie


def test_afficher_detail_lieu_sans_resultat(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "lieu-inexistant")
    monkeypatch.setattr(menu, "rechercher_global", lambda _: [])

    menu.afficher_detail_lieu()

    sortie = capsys.readouterr().out
    assert "Aucun lieu trouvé." in sortie


def test_afficher_detail_lieu_affichage_complet(monkeypatch, capsys):
    place_test = (
        1,
        "Marché de Saint-Pierre",
        "Produits locaux",
        "Saint-Pierre",
        -21.3393,
        55.4781,
        None,
        None,
        None,
        True,
        "Saint-Pierre",
        "Marché",
    )

    resultats = [
        (
            1,
            "Marché de Saint-Pierre",
            "Saint-Pierre",
            "Marché",
            None,
            None,
            None,
            1.0,
        )
    ]

    reponses = iter(["marché", "1"])

    monkeypatch.setattr("builtins.input", lambda _: next(reponses))
    monkeypatch.setattr(menu, "rechercher_global", lambda _: resultats)
    monkeypatch.setattr(menu, "get_place_details", lambda _: place_test)

    menu.afficher_detail_lieu()

    sortie = capsys.readouterr().out
    assert "Marché de Saint-Pierre" in sortie
    assert "Marché" in sortie
    assert "Saint-Pierre" in sortie
    assert "Produits locaux" in sortie
    assert "Non renseigné" in sortie
    assert "Oui" in sortie




