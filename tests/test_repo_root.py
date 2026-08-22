"""Tests for locating the assignment repository root."""

from check_pfda.utils import (
    RepositoryNotFound,
    _has_git_entry,
    _has_repo_doc_files,
    _recurse_to_repo_path,
)

import pytest


def make_repo(parent, name="assignment-repo", marker="git"):
    """Create a directory that looks like a repository root.

    ``marker`` selects how it is identifiable: a ``.git`` directory, a ``.git``
    pointer file, or a ``README.md`` + ``.gitignore`` pair.
    """
    repo = parent / name
    repo.mkdir(parents=True)
    if marker == "git":
        (repo / ".git").mkdir()
    elif marker == "gitfile":
        (repo / ".git").write_text("gitdir: /elsewhere/.git/worktrees/wt\n")
    elif marker == "docs":
        (repo / "README.md").write_text("# readme")
        (repo / ".gitignore").write_text("__pycache__/")
    return repo


class TestMarkers:
    """Which directories count as a repository root."""

    def test_git_directory(self, tmp_path):
        assert _has_git_entry(make_repo(tmp_path, marker="git"))

    def test_git_pointer_file(self, tmp_path):
        # Worktrees and submodules use a file holding "gitdir: <path>".
        assert _has_git_entry(make_repo(tmp_path, marker="gitfile"))

    def test_unrelated_file_named_git_is_rejected(self, tmp_path):
        stray = tmp_path / "stray"
        stray.mkdir()
        (stray / ".git").write_text("notes to self\n")
        assert not _has_git_entry(stray)

    def test_readme_and_gitignore_together(self, tmp_path):
        assert _has_repo_doc_files(make_repo(tmp_path, marker="docs"))

    def test_readme_alone_is_not_enough(self, tmp_path):
        lonely = tmp_path / "lonely"
        lonely.mkdir()
        (lonely / "README.md").write_text("# readme")
        assert not _has_repo_doc_files(lonely)

    def test_gitignore_alone_is_not_enough(self, tmp_path):
        lonely = tmp_path / "lonely"
        lonely.mkdir()
        (lonely / ".gitignore").write_text("*.pyc")
        assert not _has_repo_doc_files(lonely)


class TestSearch:
    """Walking upward to find the root."""

    @pytest.mark.parametrize("marker", ["git", "gitfile", "docs"])
    def test_found_from_the_root_itself(self, tmp_path, marker):
        repo = make_repo(tmp_path, marker=marker)
        assert _recurse_to_repo_path(repo) == repo

    def test_found_when_run_from_a_subdirectory(self, tmp_path):
        # Students commonly run the tool from inside src/.
        repo = make_repo(tmp_path)
        src = repo / "src"
        src.mkdir()
        assert _recurse_to_repo_path(src) == repo

    def test_found_when_run_from_deeper_still(self, tmp_path):
        repo = make_repo(tmp_path)
        deep = repo / "src" / "utils" / "helpers"
        deep.mkdir(parents=True)
        assert _recurse_to_repo_path(deep) == repo

    def test_nearest_root_wins_when_nested(self, tmp_path):
        outer = make_repo(tmp_path, name="outer")
        inner = make_repo(outer, name="inner")
        assert _recurse_to_repo_path(inner) == inner

    def test_git_root_beats_a_nearer_doc_pair(self, tmp_path):
        """The reason the two marker checks run as separate passes.

        A src/ directory holding a README and a .gitignore sits closer than
        the real root, so a single combined pass would stop there. The strong
        signal has to win regardless of which directory is nearer.
        """
        repo = make_repo(tmp_path)
        src = repo / "src"
        src.mkdir()
        (src / "README.md").write_text("# how to use src")
        (src / ".gitignore").write_text("*.pyc")

        assert _recurse_to_repo_path(src) == repo


class TestNamingIsIrrelevant:
    """The repository's name must not affect detection."""

    def test_the_reported_bug(self, tmp_path):
        # This name has no "pfda-" prefix, which is what broke the old lookup.
        repo = make_repo(tmp_path, name="c00-lab-hello-world-nelsonlimdemo")
        assert _recurse_to_repo_path(repo) == repo

    def test_pfda_name_without_markers_is_not_a_root(self, tmp_path):
        """Guards against the old name-matching surviving by accident."""
        looks_right = tmp_path / "pfda-c01-lab-shout-demo"
        looks_right.mkdir()
        assert not _has_git_entry(looks_right)
        assert not _has_repo_doc_files(looks_right)


class TestNotFound:
    def test_raises_and_lists_searched_paths(self, tmp_path, monkeypatch):
        """Stub the markers instead of relying on a real empty directory.

        Walking up from a temp directory eventually reaches the drive root,
        and what lives in those parents differs per machine. Forcing every
        check to fail keeps the test deterministic.
        """
        monkeypatch.setattr(
            "check_pfda.utils._has_git_entry", lambda path: False
        )
        monkeypatch.setattr(
            "check_pfda.utils._has_repo_doc_files", lambda path: False
        )

        start = tmp_path / "nowhere"
        start.mkdir()

        with pytest.raises(RepositoryNotFound) as excinfo:
            _recurse_to_repo_path(start)

        message = str(excinfo.value)
        assert str(start) in message
        assert "Searched paths:" in message
        assert str(tmp_path) in message
