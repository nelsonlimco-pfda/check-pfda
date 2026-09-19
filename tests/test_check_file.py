"""Tests for the explicit .check-pfda.yml assignment declaration.

This is the authoritative source of assignment identity when present: no
folder-name parsing is involved at all, and a broken file is a hard failure
rather than something that silently falls back to guessing.
"""

from pathlib import Path

import pytest

from check_pfda.utils import (
    AssignmentInfo,
    CheckFileError,
    _read_check_file,
    get_current_assignment,
)

CONFIG = {
    "tests": {
        "tests_repo_url": "https://example.invalid",
        "c00": ["hello_world"],
        "c01": ["shout", "favorite_artist", "time_lapse_calc"],
    }
}


def write_check_file(repo: Path, content: str):
    repo.mkdir(parents=True, exist_ok=True)
    (repo / ".check-pfda.yml").write_text(content)


class TestReadCheckFile:
    def test_missing_file_returns_none(self, tmp_path):
        assert _read_check_file(tmp_path) is None

    def test_valid_file_returns_assignment_name(self, tmp_path):
        write_check_file(tmp_path, "assignment: favorite_artist\n")
        assert _read_check_file(tmp_path) == "favorite_artist"

    def test_malformed_yaml_raises(self, tmp_path):
        write_check_file(tmp_path, "assignment: [unclosed\n")
        with pytest.raises(CheckFileError):
            _read_check_file(tmp_path)

    def test_missing_assignment_key_raises(self, tmp_path):
        write_check_file(tmp_path, "not_assignment: shout\n")
        with pytest.raises(CheckFileError):
            _read_check_file(tmp_path)

    def test_whitespace_only_assignment_raises(self, tmp_path):
        write_check_file(tmp_path, 'assignment: "   "\n')
        with pytest.raises(CheckFileError):
            _read_check_file(tmp_path)

    def test_non_mapping_yaml_raises(self, tmp_path):
        """A file that parses fine but isn't a mapping (e.g. a bare scalar
        from a missing colon, or a list) must not crash with AttributeError."""
        write_check_file(tmp_path, "just_a_string_no_colon\n")
        with pytest.raises(CheckFileError):
            _read_check_file(tmp_path)

    def test_empty_file_raises(self, tmp_path):
        write_check_file(tmp_path, "")
        with pytest.raises(CheckFileError):
            _read_check_file(tmp_path)


class TestGetCurrentAssignmentWithCheckFile:
    def test_check_file_overrides_a_misleading_folder_name(self, tmp_path, monkeypatch):
        """The folder name says `shout`; the .check file says otherwise, and
        the .check file must win -- proving real decoupling from naming."""
        monkeypatch.setattr("check_pfda.utils._load_config_yaml", lambda: CONFIG)
        repo = tmp_path / "pfda-c01-lab-shout-alice"
        write_check_file(repo, "assignment: favorite_artist\n")

        result = get_current_assignment(repo)

        assert result == AssignmentInfo(name="favorite_artist")
        assert result.chapter is None

    def test_missing_check_file_falls_back_to_folder_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr("check_pfda.utils._load_config_yaml", lambda: CONFIG)
        repo = tmp_path / "pfda-c01-lab-shout-alice"
        repo.mkdir(parents=True)

        result = get_current_assignment(repo)

        assert result == AssignmentInfo(chapter="01", name="shout")

    def test_malformed_check_file_hard_fails_without_fallback(
        self, tmp_path, monkeypatch, capsys
    ):
        """Even though the folder name would otherwise match `shout`, a
        broken .check file must not be silently papered over."""
        monkeypatch.setattr("check_pfda.utils._load_config_yaml", lambda: CONFIG)
        repo = tmp_path / "pfda-c01-lab-shout-alice"
        write_check_file(repo, "assignment: [unclosed\n")

        result = get_current_assignment(repo)

        assert result is None
        assert ".check-pfda.yml" in capsys.readouterr().out

    def test_check_file_missing_assignment_key_hard_fails(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.setattr("check_pfda.utils._load_config_yaml", lambda: CONFIG)
        repo = tmp_path / "pfda-c01-lab-shout-alice"
        write_check_file(repo, "chapter: c01\n")

        result = get_current_assignment(repo)

        assert result is None
        assert ".check-pfda.yml" in capsys.readouterr().out
