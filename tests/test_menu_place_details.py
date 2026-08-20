import menu


def test_afficher_detail_lieu_identifiant_invalide(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "abc")

    menu.afficher_detail_lieu()

    sortie = capsys.readouterr().out
    assert "Identifiant invalide." in sortie


def test_afficher_detail_lieu_inexistant(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "9999")
    monkeypatch.setattr(menu, "get_place_details", lambda _: None)

    menu.afficher_detail_lieu()

    sortie = capsys.readouterr().out
    assert "Aucun lieu trouvé avec cet identifiant." in sortie


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

    monkeypatch.setattr("builtins.input", lambda _: "1")
    monkeypatch.setattr(menu, "get_place_details", lambda _: place_test)

    menu.afficher_detail_lieu()

    sortie = capsys.readouterr().out

    assert "Marché de Saint-Pierre" in sortie
    assert "Marché" in sortie
    assert "Saint-Pierre" in sortie
    assert "Produits locaux" in sortie
    assert "Non renseigné" in sortie
    assert "Oui" in sortie



