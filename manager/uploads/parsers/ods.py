import ezodf
import pandas as pd
from .txt import Txt


class Ods(Txt):
    def readPandas(self, fileForPandas, skipRows):
        # Code based on: https://stackoverflow.com/a/36180806
        doc = ezodf.opendoc(fileForPandas.file)

        #print("Spreadsheet contains %d sheet(s)." % len(doc.sheets))
        #for sheet in doc.sheets:
        #    print("-"*40)
        #    print("   Sheet name : '%s'" % sheet.name)
        #    print("Size of Sheet : (rows=%d, cols=%d)" % (sheet.nrows(), sheet.ncols()) )

        # convert the first sheet to a pandas.DataFrame
        sheet = doc.sheets[0]
        df_dict = {}
        for i, row in enumerate(sheet.rows()):
            # row is a list of cells
            # assume the header is on the first row
            if i <= skipRows:
                continue
            for j, cell in enumerate(row):
                # use header instead of column index
                tmp = df_dict.get(j, [])
                tmp.append(cell.value)
                df_dict[j] = tmp
        # and convert to a DataFrame
        return pd.DataFrame(df_dict)
