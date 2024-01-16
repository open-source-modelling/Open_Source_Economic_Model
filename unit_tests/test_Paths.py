from PathsClasses import Paths
import pytest

@pytest.fixture
def paths() -> Paths:
    paths = Paths(base_folder="Test folder/")
    return paths

def test_base_path(paths):
      assert paths.base == "Test folder/"

def test_intermediate_path(paths):
    assert paths.intermediate == "Test folder/Intermediate/"

def test_input_path(paths):
    assert paths.input == "Test folder/Input/"
