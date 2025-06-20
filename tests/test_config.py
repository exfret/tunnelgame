import os
from pathlib import Path
import pytest


from engine.config import Config


@pytest.fixture
def config_for_view_for_testing(monkeypatch):
    """
    Config object, but with all files going in a tmp path.
    """
    # Redirect the environment variable that config uses a tmp folder inside of the tunnelgame folder
    monkeypatch.setenv(Path(os.getenv("TUNNELGAME_DATA_DIR", Path.home() / "tunnelgame")) / "tmp")
    # Render deploy flag off
    monkeypatch.setenv("RENDER", "FALSE")

    config = Config("dummy_story.yaml", view_type="test", profiling=False)

    return config