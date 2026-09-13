from unittest.mock import Mock

from osem.ImportData import get_configuration


def test_get_configuration_falls_back_to_op_sys_getcwd(tmp_path):
    """
    When the .ini file has no [BASE] section, get_configuration() must fall
    back to op_sys.getcwd() for the base folder (see ImportData.py's
    get_configuration: `else: configuration.base_folder = op_sys.getcwd()`).
    This exercises that fallback with a mock in place of the real os module.
    """
    ini_file = tmp_path / "ALM.ini"
    ini_file.write_text("[TRACE]\nenabled = False\n")  # no [BASE] section

    op_sys = Mock()
    op_sys.getcwd.return_value = "C:/fake/cwd"

    configuration = get_configuration(str(ini_file), op_sys)

    op_sys.getcwd.assert_called_once()
    assert configuration.base_folder == "C:/fake/cwd"