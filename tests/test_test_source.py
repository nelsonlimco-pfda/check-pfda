"""Tests for where the assignment's test file is loaded from.

Sources are tried in order: --dir, then the repository's own tests/
directory, then the remote tests repository.
"""

# TestFileError is reached through the module rather than imported by name,
# so pytest does not try to collect it as a test class.
from check_pfda import utils
from check_pfda.utils import _find_local_test_file, get_tests

import pytest

REMOTE_BODY = "def test_remote(): pass\n"


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "c00-lab-hello-world-demo"
    (repo / ".git").mkdir(parents=True)
    return repo


@pytest.fixture
def no_network(monkeypatch):
    """Fail loudly on any network use, and count remote fetches."""
    calls = []

    class FakeResponse:
        text = REMOTE_BODY

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=None):
        calls.append(url)
        return FakeResponse()

    monkeypatch.setattr("check_pfda.utils.requests.get", fake_get)
    return calls


def write_test_file(directory, assignment="hello_world", body=None):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"test_{assignment}.py"
    path.write_text(body or f"def test_{assignment}(): pass\n")
    return path


class TestFindLocalTestFile:
    def test_flat_layout(self, tmp_path):
        """How a repository's own tests/ directory is usually arranged."""
        write_test_file(tmp_path)
        found = _find_local_test_file(tmp_path, "00", "hello_world")
        assert found == tmp_path / "test_hello_world.py"

    def test_chaptered_layout(self, tmp_path):
        """The layout --dir has always expected."""
        write_test_file(tmp_path / "c00")
        found = _find_local_test_file(tmp_path, "00", "hello_world")
        assert found == tmp_path / "c00" / "test_hello_world.py"

    def test_chaptered_layout_wins_when_both_exist(self, tmp_path):
        write_test_file(tmp_path)
        write_test_file(tmp_path / "c00")
        found = _find_local_test_file(tmp_path, "00", "hello_world")
        assert found.parent.name == "c00"

    def test_missing_file_returns_none(self, tmp_path):
        assert _find_local_test_file(tmp_path, "00", "hello_world") is None

    def test_wrong_assignment_name_returns_none(self, tmp_path):
        write_test_file(tmp_path, assignment="shout")
        assert _find_local_test_file(tmp_path, "00", "hello_world") is None


class TestPrecedence:
    def test_repo_tests_directory_is_preferred_over_remote(
        self, repo, no_network
    ):
        write_test_file(repo / "tests", body="def test_local(): pass\n")

        content = get_tests("00", "hello_world", None, repo)

        assert content == "def test_local(): pass\n"
        assert no_network == [], "should not have fetched the remote tests"

    def test_dir_flag_beats_the_repo_tests_directory(
        self, repo, tmp_path, no_network
    ):
        write_test_file(repo / "tests", body="def test_repo_copy(): pass\n")
        explicit = tmp_path / "remote_checkout"
        write_test_file(explicit / "c00", body="def test_from_dir(): pass\n")

        content = get_tests("00", "hello_world", explicit, repo)

        assert content == "def test_from_dir(): pass\n"
        assert no_network == []

    def test_falls_through_to_remote_when_no_matching_file(
        self, repo, no_network
    ):
        """A tests/ dir without this assignment's file isn't a local source."""
        write_test_file(repo / "tests", assignment="something_else")

        content = get_tests("00", "hello_world", None, repo)

        assert content == REMOTE_BODY
        assert len(no_network) == 1

    def test_falls_through_to_remote_when_no_tests_directory(
        self, repo, no_network
    ):
        content = get_tests("00", "hello_world", None, repo)

        assert content == REMOTE_BODY
        assert len(no_network) == 1

    def test_remote_is_used_when_no_repo_path_is_given(self, no_network):
        """Preserves the original two-source behavior."""
        content = get_tests("00", "hello_world")

        assert content == REMOTE_BODY
        assert len(no_network) == 1


class TestAnnouncement:
    def test_repo_tests_are_announced(self, repo, no_network, capsys):
        write_test_file(repo / "tests")

        get_tests("00", "hello_world", None, repo)

        out = capsys.readouterr().out
        assert "tests" in out and "test_hello_world.py" in out
        assert "this repository" in out.lower()

    def test_dir_flag_is_announced(self, repo, tmp_path, no_network, capsys):
        explicit = tmp_path / "remote_checkout"
        write_test_file(explicit / "c00")

        get_tests("00", "hello_world", explicit, repo)

        out = capsys.readouterr().out
        assert "--dir" in out
        assert "test_hello_world.py" in out

    def test_remote_is_not_announced_as_local(self, repo, no_network, capsys):
        get_tests("00", "hello_world", None, repo)

        out = capsys.readouterr().out
        assert "this repository" not in out.lower()


class TestErrors:
    def test_missing_dir_file_is_an_error_not_a_fallback(
        self, repo, tmp_path, no_network
    ):
        """--dir states an intent, so a missing file there errors out."""
        empty = tmp_path / "empty"
        empty.mkdir()

        with pytest.raises(utils.TestFileError):
            get_tests("00", "hello_world", empty, repo)

        assert no_network == []

    def test_empty_local_file_is_an_error(self, repo, no_network):
        write_test_file(repo / "tests", body="   \n")

        with pytest.raises(utils.TestFileError):
            get_tests("00", "hello_world", None, repo)

    def test_local_file_without_tests_warns_but_returns(
        self, repo, no_network, capsys
    ):
        write_test_file(repo / "tests", body="x = 1\n")

        content = get_tests("00", "hello_world", None, repo)

        assert content == "x = 1\n"
        assert "may not be a valid test file" in capsys.readouterr().out
