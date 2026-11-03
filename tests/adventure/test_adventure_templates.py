from pokemon.adventures.templates import ALPHA_MEADOW, get_template, list_templates, validate_template


def test_alpha_meadow_template_validates():
    assert validate_template(ALPHA_MEADOW) == []
    assert get_template("alpha_meadow") is ALPHA_MEADOW
    assert get_template("Alpha Meadow Survey") is ALPHA_MEADOW
    assert ALPHA_MEADOW.start_node == "entrance"
    assert "old_tree" in ALPHA_MEADOW.nodes


def test_list_templates_includes_alpha_meadow():
    templates = list_templates()
    assert ALPHA_MEADOW in templates
