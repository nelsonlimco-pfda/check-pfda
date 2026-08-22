"""Tests for the runner's start-up behavior."""

import check_pfda.core as core

import pytest


@pytest.fixture(autouse=True)
def no_update_check(monkeypatch):
    """check_for_updates() calls PyPI; keep the suite off the network."""
    monkeypatch.setattr(core, "check_for_updates", lambda: None)


@pytest.fixture(autouse=True)
def reset_repo_path():
    """REPO_PATH is mutable module state; isolate tests from run order."""
    core.REPO_PATH = None
    yield
    core.REPO_PATH = None


def _fake_remote_response(url, timeout=None):
    """Stand-in for requests.get(), so get_tests() never hits the network."""

    class FakeResponse:
        text = "def test_x(): pass\n"

        def raise_for_status(self):
            return None

    return FakeResponse()


class TestLazyLookup:
    """The repository lookup must not run while the module is imported."""

    @pytest.mark.parametrize(
        "name", ["REPO_SRC_DIR", "REPO_TESTS_DIR", "REPO_LOG_FILE"]
    )
    def test_removed_constants_are_gone(self, name):
        """These were never part of the downloaded tests' import contract."""
        assert not hasattr(core, name)

    def test_repo_path_is_none_until_a_run_finds_a_repository(self):
        """Exists (see TestRepoPathCompatibility below), but starts unset."""
        assert core.REPO_PATH is None

    def test_importing_core_outside_a_repository_is_safe(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        import importlib

        importlib.reload(core)  # must not raise


class TestMissingRepository:
    def test_reports_a_message_instead_of_raising(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "check_pfda.core._recurse_to_repo_path",
            _raise_repository_not_found,
        )

        core.check_student_code()

        out = capsys.readouterr().out
        assert "Couldn't find your assignment repository" in out
        assert "Traceback" not in out

    def test_does_not_create_files_when_no_repository_is_found(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "check_pfda.core._recurse_to_repo_path",
            _raise_repository_not_found,
        )

        core.check_student_code()

        assert list(tmp_path.iterdir()) == []


class TestRepoPathCompatibility:
    """The downloaded tests do `from check_pfda.core import REPO_PATH`.

    Caught after publishing: c00's and c01's real test files both import this
    name directly, so it has to exist as a real module attribute by the time
    pytest imports them, even though the lookup behind it is lazy.
    """

    def test_repo_path_is_importable_after_a_successful_run(
        self, tmp_path, monkeypatch
    ):
        repo = tmp_path / "c00-lab-hello-world-demo"
        (repo / ".git").mkdir(parents=True)
        (repo / "src").mkdir()
        (repo / "src" / "hello_world.py").write_text("print('hi')\n")
        monkeypatch.chdir(repo)
        monkeypatch.setattr(core.pytest, "main", lambda args: 0)
        monkeypatch.setattr(
            "check_pfda.utils.requests.get", _fake_remote_response
        )

        core.check_student_code()

        # What the downloaded test files actually do.
        from check_pfda.core import REPO_PATH

        assert REPO_PATH == repo


def _raise_repository_not_found(path):
    from check_pfda.utils import RepositoryNotFound

    raise RepositoryNotFound(f"No repository root found starting from {path}.")
