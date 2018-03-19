import pandas as pd
from .txt import Txt

class Xls(Txt):
    def readPandas(self, fileForPandas, skipRows):
        return pd.read_excel(fileForPandas, header=None, skiprows=skipRows)
