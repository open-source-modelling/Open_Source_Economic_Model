import os
from datetime import date
from unittest.mock import Mock

import pytest

from osem.BondClasses import CorpBond, GovBond
from osem.FrequencyClass import Frequency
from osem.ImportData import get_configuration, get_corporate_bonds, get_government_bonds

CORP_HEADER = (
    "Asset_ID,Asset_Type,NACE,Issue_Date,Maturity_Date,Notional_Amount,Coupon_Rate,Spread_Country,"
    "Spread_Sector,Z_Spread,Spread_Stress,Frequency,Recovery_Rate,Default_Probability,Units,Market_Price\n"
)
GOV_HEADER = (
    "Asset_ID,Asset_Type,Issuer_Country,Issue_Date,Maturity_Date,Notional_Amount,Coupon_Rate,Z_Spread,"
    "Frequency,Units,Market_Price\n"
)
CORP_ROW = "1234,{asset_type},A1.4.5,3/12/2021,12/12/2026,100,0.03,0,0,0.01,0,1,0.4,0.03,100,94\n"
GOV_ROW = "5004,{asset_type},Italy,01/09/2020,01/09/2030,100,0.0075,0,2,120,83.78\n"

# Every [INPUT] key that get_configuration requires, without government_bonds
INPUT_SECTION = (
    "[BASE]\nbase_folder = base\n"
    "[INPUT]\nfile_path = Input\nbonds = Bond_Portfolio.csv\ncash = Cash_Portfolio.csv\n"
    "curves = Curves_no_VA.csv\nequities = Equity_Portfolio.csv\nparam_no_VA = Param_no_VA.csv\n"
    "sector_spread = Sector_Spread.csv\nparameters = Parameters.csv\nliability = Liability_Cashflow.csv\n"
    "mortality = mortality.csv\noutput_path = Output\n"
)


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


def test_get_configuration_reads_the_government_bond_file(tmp_path):
    ini_file = tmp_path / "ALM.ini"
    ini_file.write_text(INPUT_SECTION + "government_bonds = Government_Bond_Portfolio.csv\n")

    configuration = get_configuration(str(ini_file), os)

    assert configuration.input_government_bond_portfolio == os.path.join("base", "Input", "Government_Bond_Portfolio.csv")


def test_get_configuration_without_government_bond_file_leaves_it_empty(tmp_path):
    # An ALM.ini written before government bonds were added must still load
    ini_file = tmp_path / "ALM.ini"
    ini_file.write_text(INPUT_SECTION)

    configuration = get_configuration(str(ini_file), os)

    assert configuration.input_government_bond_portfolio == ""
    assert configuration.input_bond_portfolio == os.path.join("base", "Input", "Bond_Portfolio.csv")


def test_get_corporate_bonds(tmp_path):
    bond_file = tmp_path / "Bond_Portfolio.csv"
    bond_file.write_text(CORP_HEADER + CORP_ROW.format(asset_type="Corporate_Bond"))

    bonds = list(get_corporate_bonds(str(bond_file)))

    assert len(bonds) == 1
    assert isinstance(bonds[0], CorpBond)
    assert bonds[0].asset_id == 1234
    assert bonds[0].maturity_date == date(2026, 12, 12)


def test_get_government_bonds(tmp_path):
    bond_file = tmp_path / "Government_Bond_Portfolio.csv"
    bond_file.write_text(GOV_HEADER + GOV_ROW.format(asset_type="Government_Bond"))

    bonds = list(get_government_bonds(str(bond_file)))

    assert len(bonds) == 1
    bond = bonds[0]
    assert isinstance(bond, GovBond)
    assert bond.asset_id == 5004
    assert bond.issuer_country == "Italy"
    assert bond.issue_date == date(2020, 9, 1)
    assert bond.maturity_date == date(2030, 9, 1)
    assert bond.notional_amount == 100
    assert bond.coupon_rate == 0.0075
    assert bond.zspread == 0
    assert bond.frequency == Frequency.BIANNUAL
    assert bond.units == 120
    assert bond.market_price == 83.78


def test_get_government_bonds_rejects_a_corporate_row(tmp_path):
    bond_file = tmp_path / "Government_Bond_Portfolio.csv"
    bond_file.write_text(GOV_HEADER + GOV_ROW.format(asset_type="Corporate_Bond"))

    with pytest.raises(ValueError, match="Asset 5004 .* has Asset_Type Corporate_Bond"):
        list(get_government_bonds(str(bond_file)))


def test_get_corporate_bonds_rejects_a_government_row(tmp_path):
    bond_file = tmp_path / "Bond_Portfolio.csv"
    bond_file.write_text(CORP_HEADER + CORP_ROW.format(asset_type="Government_Bond"))

    with pytest.raises(ValueError, match="Asset 1234 .* has Asset_Type Government_Bond"):
        list(get_corporate_bonds(str(bond_file)))


def test_bond_file_without_asset_type_column_is_rejected(tmp_path):
    bond_file = tmp_path / "Government_Bond_Portfolio.csv"
    bond_file.write_text(
        GOV_HEADER.replace("Asset_Type,", "") + GOV_ROW.format(asset_type="").replace(",,", ",")
    )

    with pytest.raises(ValueError, match="no Asset_Type column"):
        list(get_government_bonds(str(bond_file)))
