import pandas as pd
from .txt import Txt

class Xlsx(Txt):
    def readPandas(self, fileForPandas, skipRows):
        return pd.read_excel(fileForPandas, header=None, skiprows=skipRows)
