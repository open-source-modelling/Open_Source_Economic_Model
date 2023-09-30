from PathsClasses import Paths
import pytest
import os

@pytest.fixture
def paths() -> Paths:
    paths = Paths()
    return paths

def test_base_path(paths):
    assert os.path.exists(paths.base)

def test_intermediate_path(paths):
    assert os.path.exists(paths.intermediate)

def test_input_path(paths):
    assert os.path.exists(paths.input)
