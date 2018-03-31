import pandas as pd
from overrides import overrides
from manager.uploads.parsers.txt import Txt


class Xlsx(Txt):
    """
    This parses XLSX files of excel 2010 and newer.
    """
    @overrides
    def readPandas(self, fileForPandas, skipRows):
        return pd.read_excel(fileForPandas, header=None, skiprows=skipRows)
