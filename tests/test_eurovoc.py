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


def test_level_1_options_are_21_sorted_by_greek_name():
    options = eurovoc.level_1_options()
    assert len(options) == 21
    assert [c["el"] for c in options] == sorted(c["el"] for c in options)
