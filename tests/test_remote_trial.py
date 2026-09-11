"""Tests for the remote-tests trial offered when the local tests fail."""

from pathlib import Path
from types import SimpleNamespace

import check_pfda.core as core
from check_pfda.utils import (
    ORIGIN_DIR,
    ORIGIN_REMOTE,
    ORIGIN_REPO,
    get_tests,
    resolve_tests,
)

import pytest

REMOTE_BODY = "def test_remote(): pass\n"
LOCAL_BODY = "def test_local(): pass\n"


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


@pytest.fixture
def fake_remote(monkeypatch):
    """Serve REMOTE_BODY instead of downloading, and count the fetches."""
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


@pytest.fixture
def repo(tmp_path):
    """A student repo for c00's hello_world, holding some student code."""
    repo = tmp_path / "pfda-c00-lab-hello-world-demo"
    (repo / ".git").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / "src" / "hello_world.py").write_text("print('hi')\n")
    return repo


@pytest.fixture
def runs(monkeypatch):
    """Record every pytest.main() call and hand out queued exit codes."""
    paths = []
    exit_codes = []

    def fake_main(args):
        paths.append(Path(args[0]))
        return exit_codes.pop(0) if exit_codes else 0

    monkeypatch.setattr(core.pytest, "main", fake_main)
    return SimpleNamespace(paths=paths, exit_codes=exit_codes)


class FakeStdin:
    def __init__(self, interactive):
        self.interactive = interactive

    def isatty(self):
        return self.interactive


@pytest.fixture
def interactive(monkeypatch):
    monkeypatch.setattr(core.sys, "stdin", FakeStdin(True))


def never_prompts(*args, **kwargs):
    raise AssertionError("should not have prompted")


def write_repo_tests(repo, body=LOCAL_BODY):
    tests = repo / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    path = tests / "test_hello_world.py"
    path.write_text(body)
    return path


class TestOrigin:
    """resolve_tests reports which of the three sources it used."""

    def test_repo_tests_directory(self, repo, fake_remote):
        write_repo_tests(repo)

        source = resolve_tests("00", "hello_world", None, repo)

        assert source.origin == ORIGIN_REPO
        assert source.path == repo / "tests" / "test_hello_world.py"
        assert fake_remote == []

    def test_dir_flag(self, repo, tmp_path, fake_remote):
        explicit = tmp_path / "remote_checkout" / "c00"
        explicit.mkdir(parents=True)
        (explicit / "test_hello_world.py").write_text(LOCAL_BODY)

        source = resolve_tests(
            "00", "hello_world", tmp_path / "remote_checkout", repo
        )

        assert source.origin == ORIGIN_DIR
        assert fake_remote == []

    def test_remote(self, repo, fake_remote):
        source = resolve_tests("00", "hello_world", None, repo)

        assert source.origin == ORIGIN_REMOTE
        assert source.path is None
        assert len(fake_remote) == 1

    def test_force_remote_skips_the_repo_tests_directory(
        self, repo, fake_remote
    ):
        write_repo_tests(repo)

        source = resolve_tests(
            "00", "hello_world", None, repo, force_remote=True
        )

        assert source.origin == ORIGIN_REMOTE
        assert source.content == REMOTE_BODY
        assert len(fake_remote) == 1

    def test_get_tests_still_returns_a_string(self, repo, fake_remote):
        """The wrapper kept its old signature for the downloaded tests."""
        write_repo_tests(repo)

        assert get_tests("00", "hello_world", None, repo) == LOCAL_BODY


class TestTrialIsOffered:
    def test_accepting_runs_the_remote_tests(
        self, repo, monkeypatch, runs, fake_remote, interactive
    ):
        write_repo_tests(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(core, "confirm", lambda *a, **k: True)
        runs.exit_codes.extend([1, 0])

        core.check_student_code()

        assert len(runs.paths) == 2

    def test_the_trial_uses_a_different_file_from_the_first_run(
        self, repo, monkeypatch, runs, fake_remote, interactive
    ):
        """Reusing the name would make pytest re-run the cached module."""
        write_repo_tests(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(core, "confirm", lambda *a, **k: True)
        runs.exit_codes.extend([1, 0])

        core.check_student_code()

        first, second = runs.paths
        assert first.name == "test_hello_world.py"
        assert second.name == "test_hello_world_remote.py"

    def test_the_trial_file_holds_the_remote_tests(
        self, repo, monkeypatch, runs, fake_remote, interactive
    ):
        write_repo_tests(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(core, "confirm", lambda *a, **k: True)
        runs.exit_codes.extend([1, 0])

        core.check_student_code()

        assert runs.paths[1].read_text() == REMOTE_BODY

    def test_declining_runs_pytest_once(
        self, repo, monkeypatch, runs, fake_remote, interactive
    ):
        write_repo_tests(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(core, "confirm", lambda *a, **k: False)
        runs.exit_codes.append(1)

        core.check_student_code()

        assert len(runs.paths) == 1

    def test_ctrl_c_at_the_prompt_is_not_a_traceback(
        self, repo, monkeypatch, runs, fake_remote, interactive
    ):
        write_repo_tests(repo)
        monkeypatch.chdir(repo)

        def abort(*args, **kwargs):
            raise core.Abort()

        monkeypatch.setattr(core, "confirm", abort)
        runs.exit_codes.append(1)

        core.check_student_code()

        assert len(runs.paths) == 1


class TestTrialIsNotOffered:
    def test_when_the_local_tests_pass(
        self, repo, monkeypatch, runs, fake_remote, interactive
    ):
        write_repo_tests(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(core, "confirm", never_prompts)
        runs.exit_codes.append(0)

        core.check_student_code()

        assert len(runs.paths) == 1

    def test_when_the_tests_already_came_from_the_remote_repo(
        self, repo, monkeypatch, runs, fake_remote, interactive
    ):
        monkeypatch.chdir(repo)
        monkeypatch.setattr(core, "confirm", never_prompts)
        runs.exit_codes.append(1)

        core.check_student_code()

        assert len(runs.paths) == 1

    def test_when_dir_was_given(
        self, repo, tmp_path, monkeypatch, runs, fake_remote, interactive
    ):
        """--dir names a folder on purpose, so it is left alone."""
        explicit = tmp_path / "remote_checkout" / "c00"
        explicit.mkdir(parents=True)
        (explicit / "test_hello_world.py").write_text(LOCAL_BODY)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(core, "confirm", never_prompts)
        runs.exit_codes.append(1)

        core.check_student_code(tests_dir=tmp_path / "remote_checkout")

        assert len(runs.paths) == 1

    def test_when_remote_was_forced(
        self, repo, monkeypatch, runs, fake_remote, interactive
    ):
        write_repo_tests(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(core, "confirm", never_prompts)
        runs.exit_codes.append(1)

        core.check_student_code(force_remote=True)

        assert len(runs.paths) == 1
        assert runs.paths[0].read_text() == REMOTE_BODY


class TestNonInteractive:
    def test_prints_the_remote_hint_instead_of_prompting(
        self, repo, monkeypatch, runs, fake_remote, capsys
    ):
        write_repo_tests(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(core.sys, "stdin", FakeStdin(False))
        monkeypatch.setattr(core, "confirm", never_prompts)
        runs.exit_codes.append(1)

        core.check_student_code()

        assert len(runs.paths) == 1
        assert "--remote" in capsys.readouterr().out


class TestCli:
    def test_dir_and_remote_together_is_a_usage_error(self, tmp_path):
        from click.testing import CliRunner

        from check_pfda.cli import cli

        result = CliRunner().invoke(
            cli, ["--dir", str(tmp_path), "--remote"]
        )

        assert result.exit_code != 0
        assert "cannot be used together" in result.output
