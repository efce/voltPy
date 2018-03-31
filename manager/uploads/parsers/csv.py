import pandas as pd
from overrides import overrides
from manager.uploads.parsers.txt import Txt


class Csv(Txt):
    """
    Parser for CSV files.
    """

    @overrides
    def readPandas(self, fileForPandas, skipRows):
        return pd.read_csv(fileForPandas, sep=',', header=None, skiprows=skipRows)
