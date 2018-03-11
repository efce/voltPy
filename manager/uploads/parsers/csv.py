import pandas as pd
from .txt import Txt

class Csv(Txt):
    def readPandas(fileForPandas):
        return pd.read_csv(fileForPandas, sep=',', header=None, skiprows=skipRows)
