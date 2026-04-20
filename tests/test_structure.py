from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_src_directory_exists():
    assert (REPO_ROOT / "src").is_dir()


def test_agents_module_exists():
    assert (REPO_ROOT / "src" / "agents" / "__init__.py").is_file()
    assert (REPO_ROOT / "src" / "agents" / "base.py").is_file()


def test_api_module_exists():
    assert (REPO_ROOT / "src" / "api" / "__init__.py").is_file()
    assert (REPO_ROOT / "src" / "api" / "routes.py").is_file()


def test_core_module_exists():
    assert (REPO_ROOT / "src" / "core" / "__init__.py").is_file()
    assert (REPO_ROOT / "src" / "core" / "llm_client.py").is_file()


def test_main_exists():
    assert (REPO_ROOT / "src" / "main.py").is_file()


def test_requirements_exists():
    assert (REPO_ROOT / "requirements.txt").is_file()
