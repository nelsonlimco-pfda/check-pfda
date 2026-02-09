## check-pfda

`check-pfda` is a small command-line tool that **downloads the correct autograder tests for a PFDA assignment** and runs them against a student’s code, then prints feedback in the terminal.

This README has two parts:

- **Student quick start**: install + run the checker
- **Developer documentation**: how the tool works internally, where to change things, and how to maintain it

---

## Student quick start

### Installation

```bash
pip install check-pfda
```

### Run it

1. **Open a terminal** in your assignment folder (or any folder inside it).
2. Run one of the following:

- **MacOS/Linux**:

```bash
python3 -m check_pfda
```

- **Windows**:

```bash
python -m check_pfda
```

Tip: **If you are using a Python virtual environment**, you can also run the installed command:

```bash
pfda
```

### Helpful options

- **More/less detail**: `-v/--verbosity` (0–3). Example:

- **Debug log**: `-d/--debug` writes a `debug.log` file in the assignment repo’s root folder:

---

## Developer documentation (for maintainers)

### What problem this repo solves

We want a single tool that students can install once, then run in any PFDA assignment repo to:

- figure out which assignment it is
- fetch the matching test file from a central “tests repo”
- run the tests with `pytest`
- show clear output (and optionally a debug log if something goes wrong *in check_pfda's execution itself, **not** if the student's code does not pass the tests*)

Keeping tests in a separate repo means instructors can update tests without having to ship a new `check-pfda` release every time.

### Big picture: what happens when someone runs `python -m check_pfda`

When a user runs `python -m check_pfda` the tool does roughly this:

- **Find the assignment repo root**
  - starting from the current folder, it walks upward until it finds a folder name containing `pfda-c`
- **Figure out chapter + assignment**
  - it compares the repo’s folder path to the list in `src/check_pfda/config.yaml`
- **Create a local `.tests/` folder**
  - this is a temporary workspace for downloaded tests
- **Download the test file**
  - from the configured GitHub “raw” URL (see `config.yaml`)
- **Make sure Python can find the student code**
  - it temporarily tells Python to look in the assignment repo’s `src/` folder (so tests can `import shout`, etc.)
- **Run `pytest` on that test file**
  - it points `pytest` at the downloaded file and lets pytest print the results

If something goes wrong (no match, network error, missing test file), the tool prints a friendly message and stops.

### Repo layout (where to look)

The important files are:

- **`src/check_pfda/cli.py`**
  - defines the command-line interface (options like `--verbosity` and `--debug`)
- **`src/check_pfda/core.py`**
  - the main “runner” that ties everything together
- **`src/check_pfda/utils.py`**
  - helper functions used by the runner and (importantly) by the autograder tests
- **`src/check_pfda/config.yaml`**
  - the chapter/assignment list + the base URL for where tests are downloaded from
- **`pyproject.toml`**
  - package name/version and the `pfda` command entry point

### How the CLI connects to the code

There are two common ways to start the tool:

- `python -m check_pfda` runs `src/check_pfda/__main__.py`, which calls the CLI.
- `pfda` is installed as a command that points to `check_pfda.cli:cli` (see `pyproject.toml`).

> [!IMPORTANT]
> **`pfda` only works in a Python virtual environment**, which students don't use (they use the global interpreter, since they don't know what a virtual environment is). As such, the recommended way to interact with the package is by executing the module.

In both cases, everything funnels into:

- `check_pfda.core.check_student_code(...)`

### How assignment detection works

The tool needs two pieces of information to download the right tests:

- the **chapter** (like `c01`)
- the **assignment name** (like `shout`)

Because student repo names include both of those (plus a username), we detect them from the folder name.

Example student repo folder names:

- `pfda-c01-lab-shout-someusername`
- `pfda-c01-lab-favorite-artist-someusername`

What the code does:

- First, it finds the repo root folder whose name contains **`pfda-c`**.
- Then it loads `src/check_pfda/config.yaml` and checks:
  - does the path contain `c01`, `c02`, etc?
  - does the path contain one of the assignment names listed for that chapter?

Small detail (important in practice): folder names often use hyphens (`favorite-artist`) but Python files/tests use underscores (`favorite_artist`), so the matcher treats `-` and `_` as “basically the same”.

### What the tool expects from an assignment repo

For the checker to work, the assignment repo usually needs:

- a folder name that contains a chapter like `c01` and an assignment name like `shout`
- a `src/` folder in the repo root (this is where student code lives)
- the assignment’s Python file(s) inside `src/` (often `src/<assignment>.py`)

### Configuration: `config.yaml`

`src/check_pfda/config.yaml` controls:

- **Where tests are downloaded from**
  - `tests.tests_repo_url`
- **Which assignments exist**
  - `tests.c00`, `tests.c01`, … lists of assignment “slugs”

The download URL is built like this:

- base URL from `tests_repo_url`
- plus `/c{chapter}/test_{assignment}.py`

So if the chapter is `01` and the assignment is `shout`, the tool downloads:

- `c01/test_shout.py`

### What gets created in a student repo

Running the tool in a student repo will create:

- **`.tests/`**
  - a folder that stores the downloaded test file
  - safe to delete; it will be recreated next run
- **`debug.log`** (only with `--debug`)
  - a log file with extra details to help diagnose problems

### How to develop locally (a simple workflow)

This repo uses **uv** for dependency management and packaging.

You usually want to edit this `check-pfda` repo, but run the tool inside a “student-style” assignment repo so the path-matching logic behaves like it does for real students.

#### 1) Get a demo assignment repo to test against

You need a folder that looks like a student assignment repo (the folder name matters).

You can either:

- clone a real PFDA assignment repo (recommended), or
- create a small demo folder named something like `pfda-c01-lab-shout-dev` with a `src/shout.py` file inside

#### 2) Set up your dev environment (uv)

From the root of this `check-pfda` repo:

```bash
uv sync
```

This creates/updates `.venv/` and installs this project in **editable mode**, so your code changes take effect immediately.

#### 3) Run the checker against the demo repo

The easiest way is to activate this repo’s `.venv` once, then you can run `pfda` from anywhere.

From the `check-pfda` repo root, activate:

- **MacOS/Linux**:

```bash
source .venv/bin/activate
```

- **Windows (PowerShell)**:

```bash
.\.venv\Scripts\Activate.ps1
```

- **Windows (cmd.exe)**:

```bash
.\.venv\Scripts\activate.bat
```

Then `cd` into the demo assignment repo and run:

```bash
pfda -v 2
```

Tip: If you don’t want to activate a venv, you can run through uv instead:

```bash
uv run --directory <path-to-demo-assignment-repo> pfda -v 2
```

### Adding or updating an assignment

Most maintenance work is one of these:

#### Add a new assignment (so it can be detected)

1. Add the assignment slug to `src/check_pfda/config.yaml` under the right chapter.
2. Make sure the tests repo contains a file with the matching name:
   - folder: `cXX/`
   - file: `test_<assignment>.py`

Keep names simple:

- Prefer **underscores** in `config.yaml` (example: `favorite_artist`)
- The code will still match student repo folders that use hyphens (example: `favorite-artist`)

#### Change where tests are hosted (staging vs production)

Edit `tests.tests_repo_url` in `src/check_pfda/config.yaml`.

This is useful if you have:

- a temporary test repo for development
- a new location for the official tests

### The “test helpers” in `utils.py` (why they exist)

The downloaded test files are normal pytest tests, but many of them rely on shared helper functions in `check_pfda.utils` so tests stay consistent and student-facing messages stay friendly.

Common helpers:

- **`patch_input_output(...)`**
  - simulates user input and captures printed output
- **`build_user_friendly_err(actual, expected)`**
  - generates a readable “what you printed vs what we expected” message
- **`assert_script_exists(...)`**
  - fails the test with a clear message if a required `*.py` file is missing

Maintenance tip: try to keep these helpers backward-compatible, because changing them can affect many assignments at once.

### Troubleshooting (common issues)

- **“Unable to match chapter and assignment against cwd.”**
  - You’re probably not inside a repo whose folder name includes both:
    - a chapter like `c01`
    - an assignment name listed in `config.yaml`
  - Fix: rename the folder to match, or update `config.yaml` if it’s a new assignment.

- **“C07 and C08 do not have any automated tests…”**
  - This is expected behavior: the tool intentionally stops for those chapters.

> [!TIP]
> This needs to be refactored. Could be a good place to start getting used to this codebase.

- **“Error fetching test file…”**
  - Common causes:
    - no internet access
    - the tests repo URL changed
    - the test file doesn’t exist at the expected path
  - Fix: check `tests_repo_url` and confirm the test file name/location.

- **`.tests/` permission errors**
  - The tool needs to create `.tests/` and write a file inside it.
  - Fix: make sure the assignment folder is writable.

### Code quality checks (simple and optional, but recommended)

This repo is set up for pre-commit checks:

- **flake8** for basic style issues
- **pydoclint** for docstring consistency

If you want those checks to run automatically before every commit:

```bash
uv tool run pre-commit install
```

To run them on demand:

```bash
uv tool run pre-commit run --all-files
```

---

## Maintainer notes

- **Be careful with breaking changes**: students and tests may depend on existing behavior.
- **When in doubt, add logging** behind `--debug` rather than printing extra output by default.
- **If you update `config.yaml`**, double-check that the remote tests repo uses the same names and folder structure.

---

## Publishing to PyPI (release checklist)

This repo uses **uv** for building and publishing.

This section is for maintainers who have publish access to the `check-pfda` project on PyPI (contact Nelson for access).

### One-time setup (access + security)

- **API token**: publishing uses a **PyPI API token**.
  - Create one in PyPI → Account settings → API tokens (and separately in TestPyPI if you use it).
  - Keep it secret. Don't commit it, put it in an LLM, send it in a chat, etc.

### 1) Update the version number

You can either:

- use uv (recommended):

```bash
uv version --bump patch
```

- or edit `pyproject.toml` and bump `project.version` (example: `1.0.1` → `1.0.2`)

### 2) Build the package locally

From the repo root:

```bash
uv build --no-sources --clear
```

This creates a `dist/` folder containing the files that will be uploaded to PyPI.

### 3) (Optional) Dry-run the publish

```bash
uv publish --dry-run
```

### 4) (Optional but recommended) Upload to TestPyPI first

TestPyPI is a separate “practice” registry to catch mistakes before a real release.

Set a token (recommended via environment variable), then publish to the TestPyPI upload endpoint:

- **MacOS/Linux**:

```bash
export UV_PUBLISH_TOKEN="<YOUR_TESTPYPI_TOKEN>"
uv publish --publish-url https://test.pypi.org/legacy/ --check-url https://test.pypi.org/simple/
```

- **Windows (PowerShell)**:

```bash
$env:UV_PUBLISH_TOKEN="<YOUR_TESTPYPI_TOKEN>"
uv publish --publish-url https://test.pypi.org/legacy/ --check-url https://test.pypi.org/simple/
```

Then try running it from TestPyPI (this avoids using your local checkout):

```bash
uv run --no-project --default-index https://test.pypi.org/simple --index https://pypi.org/simple --with check-pfda pfda --help
```

### 5) Upload to the real PyPI

Set a PyPI token, then publish:

- **MacOS/Linux**:

```bash
export UV_PUBLISH_TOKEN="<YOUR_PYPI_TOKEN>"
uv publish
```

- **Windows (PowerShell)**:

```bash
$env:UV_PUBLISH_TOKEN="<YOUR_PYPI_TOKEN>"
uv publish
```

### 6) Verify the release

Run it from PyPI (this avoids using your local checkout):

```bash
uv run --no-project --with check-pfda pfda --help
```

### Common “oops” fixes

- **“File already exists” on upload**: PyPI does not allow re-uploading the same version.
  - Fix: bump the version in `pyproject.toml` and rebuild.
- **Built files look wrong**: rebuild with a clean `dist/`:
  - Fix: `uv build --clear`
- **Verification still shows the old version**: refresh the cached package when running:
  - Fix: add `--refresh-package check-pfda` to the `uv run ...` command
