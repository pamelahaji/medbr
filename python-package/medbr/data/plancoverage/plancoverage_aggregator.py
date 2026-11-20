from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
agg_file = HERE / 'transformed' / 'plancoverage.csv'
agg_file.parent.mkdir(exist_ok=True)

df = pd.read_csv(HERE / 'raw' / 'data.csv', sep=';')

df = df[['CD_MUNICIPIO', 'CD_OPERADORA', 'ID_PLANO']].groupby(['CD_MUNICIPIO', 'CD_OPERADORA']).count().reset_index()

df = df.rename(columns={
    "CD_MUNICIPIO": "city_code",
    "CD_OPERADORA": "operator",
    "ID_PLANO": "count"
})

df.to_csv(agg_file, index=False, sep=';')
