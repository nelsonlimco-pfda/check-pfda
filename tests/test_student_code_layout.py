"""Tests that student code is importable wherever it lives in the repo."""

import sys

from check_pfda.utils import _add_to_path, find_student_code_dirs

import pytest


@pytest.fixture
def repo(tmp_path):
    """An otherwise empty repository root."""
    repo = tmp_path / "c00-lab-hello-world-demo"
    (repo / ".git").mkdir(parents=True)
    return repo


def add_module(directory, name="hello_world"):
    """Write a trivial importable module into ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.py").write_text(f"NAME = {name!r}\n")
    return directory


def dir_names(repo):
    return {d.name for d in find_student_code_dirs(repo)}


class TestNoDirectoryNameIsPrivileged:
    def test_code_in_src(self, repo):
        add_module(repo / "src")
        assert repo / "src" in find_student_code_dirs(repo)

    def test_code_at_the_repository_root(self, repo):
        add_module(repo)
        assert repo in find_student_code_dirs(repo)

    def test_code_in_an_arbitrarily_named_directory(self, repo):
        """Nothing hardcodes 'code', so this is the real proof."""
        add_module(repo / "code")
        assert repo / "code" in find_student_code_dirs(repo)

    def test_modules_split_across_directories(self, repo):
        add_module(repo / "src", name="shout")
        add_module(repo / "extra", name="whisper")
        found = find_student_code_dirs(repo)
        assert repo / "src" in found
        assert repo / "extra" in found

    def test_helper_beside_the_main_module(self, repo):
        src = add_module(repo / "src")
        add_module(src, name="helpers")
        assert repo / "src" in find_student_code_dirs(repo)

    def test_no_code_anywhere_still_returns_the_root(self, repo):
        """No crash, no warning; whether code is missing is the tests' call."""
        assert find_student_code_dirs(repo) == [repo]

    def test_repository_root_is_always_included(self, repo):
        add_module(repo / "src")
        assert repo in find_student_code_dirs(repo)

    def test_shallowest_first(self, repo):
        add_module(repo / "src" / "deep" / "deeper")
        add_module(repo / "src")
        found = find_student_code_dirs(repo)
        depths = [len(d.relative_to(repo).parts) for d in found]
        assert found[0] == repo
        assert depths == sorted(depths)


class TestSkippedDirectories:
    def test_tests_directory_is_not_importable(self, repo):
        """Keeps a repo's own test file from shadowing the copy in .tests/."""
        (repo / "tests").mkdir()
        test_file = repo / "tests" / "test_hello_world.py"
        test_file.write_text("def test_x(): pass\n")
        assert "tests" not in dir_names(repo)

    def test_singular_test_directory_is_skipped(self, repo):
        (repo / "test").mkdir()
        test_file = repo / "test" / "test_hello_world.py"
        test_file.write_text("def test_x(): pass\n")
        assert "test" not in dir_names(repo)

    def test_dot_directories_are_skipped(self, repo):
        add_module(repo / ".venv" / "lib")
        add_module(repo / ".tests")
        names = dir_names(repo)
        assert ".venv" not in names
        assert ".tests" not in names

    def test_virtualenv_under_any_name_is_skipped(self, repo):
        """Identified by pyvenv.cfg rather than by being called '.venv'."""
        env = add_module(repo / "myenv")
        (env / "pyvenv.cfg").write_text("home = /usr\n")
        assert "myenv" not in dir_names(repo)

    def test_pycache_and_node_modules_are_skipped(self, repo):
        add_module(repo / "__pycache__")
        add_module(repo / "node_modules")
        names = dir_names(repo)
        assert "__pycache__" not in names
        assert "node_modules" not in names

    def test_directories_without_python_files_are_skipped(self, repo):
        (repo / "docs").mkdir()
        (repo / "docs" / "notes.md").write_text("notes")
        assert "docs" not in dir_names(repo)


class TestPathHandling:
    def test_code_is_actually_importable(self, repo):
        add_module(repo / "code")
        with _add_to_path(find_student_code_dirs(repo)):
            module = __import__("hello_world")
            assert module.NAME == "hello_world"
        sys.modules.pop("hello_world", None)

    def test_search_order_matches_the_given_order(self, repo):
        add_module(repo / "src")
        dirs = find_student_code_dirs(repo)
        with _add_to_path(dirs):
            assert sys.path[0] == str(dirs[0].resolve())

    def test_sys_path_is_restored(self, repo):
        add_module(repo / "src")
        add_module(repo / "code")
        before = list(sys.path)
        with _add_to_path(find_student_code_dirs(repo)):
            assert sys.path != before
        assert sys.path == before

    def test_sys_path_is_restored_after_an_error(self, repo):
        add_module(repo / "src")
        before = list(sys.path)
        with pytest.raises(RuntimeError):
            with _add_to_path(find_student_code_dirs(repo)):
                raise RuntimeError("boom")
        assert sys.path == before

    def test_a_single_path_still_works(self, repo):
        """Widened to accept a list, but a lone path must still work."""
        src = add_module(repo / "src")
        before = list(sys.path)
        with _add_to_path(src):
            assert str(src.resolve()) in sys.path
        assert sys.path == before

    def test_paths_already_present_are_left_alone(self, repo):
        src = add_module(repo / "src")
        resolved = str(src.resolve())
        sys.path.insert(0, resolved)
        try:
            with _add_to_path([src]):
                pass
            assert resolved in sys.path
        finally:
            sys.path.remove(resolved)
