import pandas as pd
from pathlib import Path

def save_matrices_to_csv(path: str, name: str, frame):
    """
    Save DataFrame as a csv file on a specified path

    Parameters
    ----------
    :type path: string; absolute location where the csv will be saved
    :type name: string; name of the csv (Note that the name should be without ".csv" ending)
    :type frame: Pandas.DataFrame; DataFrame that needs to be saved 

    Returns
    -------
    
    """
    filepath = Path(path + name+'.csv')
    filepath.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(frame).to_csv(filepath)
