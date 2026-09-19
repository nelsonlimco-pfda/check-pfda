"""Tests for matching a student repo's folder name to a chapter/assignment.

The folder name always looks like ``pfda-c01-lab-<assignment>-<username>``,
where the username is student-controlled and may coincidentally contain
text that looks like an assignment or chapter name. Matching must not be
fooled by that.
"""

from pathlib import Path

from check_pfda.utils import (
    AssignmentInfo,
    _match_assignment_from_config,
    get_current_assignment,
)

CONFIG = {
    "tests": {
        "tests_repo_url": "https://example.invalid",
        "c00": ["hello_world"],
        "c01": ["shout", "favorite_artist", "time_lapse_calc"],
        "c07": ["not_actually_tested"],
    }
}


class TestTokenBoundaryMatching:
    def test_basic_match(self):
        result = _match_assignment_from_config(CONFIG, "pfda-c01-lab-shout-alice")
        assert result == AssignmentInfo(chapter="01", name="shout")

    def test_multi_word_assignment_match(self):
        result = _match_assignment_from_config(
            CONFIG, "pfda-c01-lab-favorite-artist-alice"
        )
        assert result == AssignmentInfo(chapter="01", name="favorite_artist")

    def test_username_substring_of_assignment_is_not_a_match(self):
        """The reported bug: a raw substring match on an unrelated username."""
        result = _match_assignment_from_config(
            CONFIG, "pfda-c01-lab-favorite-artist-leshoutier"
        )
        assert result == AssignmentInfo(chapter="01", name="favorite_artist")

    def test_username_with_delimiters_matching_another_assignment(self):
        """A username token run (`shout-master`) that coincidentally equals
        another valid assignment name must lose to the real, earlier one."""
        result = _match_assignment_from_config(
            CONFIG, "pfda-c01-lab-favorite-artist-shout-master"
        )
        assert result == AssignmentInfo(chapter="01", name="favorite_artist")

    def test_username_repeating_the_real_assignment_name_is_harmless(self):
        result = _match_assignment_from_config(CONFIG, "pfda-c01-lab-shout-shout-fan")
        assert result == AssignmentInfo(chapter="01", name="shout")

    def test_chapter_substring_in_username_is_not_a_match(self):
        """A username like `marc02thens` must not be read as chapter c02."""
        result = _match_assignment_from_config(CONFIG, "pfda-c01-lab-shout-marc02thens")
        assert result == AssignmentInfo(chapter="01", name="shout")

    def test_no_match_returns_none(self):
        result = _match_assignment_from_config(CONFIG, "pfda-c01-lab-shout-alice")
        assert result is not None
        result = _match_assignment_from_config(CONFIG, "some-unrelated-folder")
        assert result is None

    def test_ambiguity_is_logged(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING, logger="check_pfda.utils"):
            _match_assignment_from_config(
                CONFIG, "pfda-c01-lab-favorite-artist-shout-master"
            )

        assert any("Ambiguous assignment match" in r.message for r in caplog.records)


class TestGetCurrentAssignment:
    def test_uses_only_the_repo_folder_name(self, tmp_path, monkeypatch):
        """An ancestor directory that happens to look like a match must not
        count -- only the repo's own folder name does."""
        monkeypatch.setattr(
            "check_pfda.utils._load_config_yaml", lambda: CONFIG
        )
        repo = tmp_path / "shout" / "c00" / "pfda-c01-lab-favorite-artist-alice"
        repo.mkdir(parents=True)

        result = get_current_assignment(repo)

        assert result == AssignmentInfo(chapter="01", name="favorite_artist")

    def test_c07_is_skipped(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(
            "check_pfda.utils._load_config_yaml", lambda: CONFIG
        )
        repo = tmp_path / "pfda-c07-lab-not-actually-tested-alice"
        repo.mkdir(parents=True)

        result = get_current_assignment(repo)

        assert result is None
        assert "C07 and C08 do not have any automated tests" in capsys.readouterr().out

    def test_c07_substring_in_username_does_not_trigger_skip(self, tmp_path, monkeypatch, capsys):
        """A username like `marc07thens` must not be read as chapter c07."""
        monkeypatch.setattr(
            "check_pfda.utils._load_config_yaml", lambda: CONFIG
        )
        repo = tmp_path / "pfda-c01-lab-shout-marc07thens"
        repo.mkdir(parents=True)

        result = get_current_assignment(repo)

        assert result == AssignmentInfo(chapter="01", name="shout")
        assert "C07 and C08" not in capsys.readouterr().out
