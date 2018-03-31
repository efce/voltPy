import pandas as pd
from overrides import overrides
from manager.uploads.parsers.txt import Txt


class Xls(Txt):
    """
    Parses XLS excel files.
    """
    @overrides
    def readPandas(self, fileForPandas, skipRows):
        return pd.read_excel(fileForPandas, header=None, skiprows=skipRows)
