import pandas as pd
from .txt import Txt

class Csv(Txt):
    def readPandas(self, fileForPandas, skipRows):
        return pd.read_csv(fileForPandas, sep=',', header=None, skiprows=skipRows)
