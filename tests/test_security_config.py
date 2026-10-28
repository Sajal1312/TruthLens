from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_env_example_contains_only_a_tavily_placeholder():
    lines = (PROJECT_ROOT / ".env.example").read_text().splitlines()
    values = [line.partition("=")[2].strip() for line in lines
              if line.partition("=")[0].strip() == "TAVILY_API_KEY"]

    assert values == ["your_tavily_api_key_here"]


def test_local_secret_files_are_listed_in_gitignore():
    ignored = set((PROJECT_ROOT / ".gitignore").read_text().splitlines())

    assert ".env" in ignored
    assert ".streamlit/secrets.toml" in ignored
