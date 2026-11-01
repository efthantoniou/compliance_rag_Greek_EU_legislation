from agent import eurovoc


def test_concept_resolves_known_id_to_greek_and_english():
    assert eurovoc.concept("2413") == {
        "id": "2413",
        "el": "βιομηχανικό φυτό",
        "en": "industrial plant",
    }


def test_concept_unknown_id_falls_back_to_raw_id():
    assert eurovoc.concept("does-not-exist") == {
        "id": "does-not-exist",
        "el": "does-not-exist",
        "en": "does-not-exist",
    }


def test_concepts_maps_a_list_in_order():
    resolved = eurovoc.concepts(["100149", "100160"])
    assert [c["en"] for c in resolved] == ["social questions", "industry"]


def test_level_1_options_are_21_sorted_alphabetically_ignoring_accents_and_case():
    # Raw code-point order would put accented vowels (ά, έ, ή, ί) and capitals
    # ahead of plain lowercase α, scrambling the domain dropdown.
    options = eurovoc.level_1_options()
    assert len(options) == 21
    assert options[0]["el"] == "απασχόληση και συνθήκες εργασίας"
    assert options[-1]["el"] == "πολιτική"
    names = [c["el"] for c in options]
    assert names.index("Ευρωπαϊκή Ένωση") < names.index("οικονομικά")


def test_level_1_greek_labels_are_accented():
    # The bundled level-1 names had lost their tonos (lowercased from Greek caps).
    assert eurovoc.concept("100149")["el"] == "κοινωνικά θέματα"
    assert eurovoc.concept("100144") == {
        "id": "100144",
        "el": "Ευρωπαϊκή Ένωση",
        "en": "European Union",
    }


def test_latin_concept_survived_encoding():
    assert eurovoc.concept("4150")["el"] == "grande école"
