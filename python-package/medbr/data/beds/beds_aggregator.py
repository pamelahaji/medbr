from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
agg_file = HERE / 'transformed' / 'beds.csv'
agg_file.parent.mkdir(exist_ok=True)

df = pd.read_csv(HERE / 'raw' / 'data_2023.csv', encoding='latin-1')

df = df[['UF', 'LEITOS_EXISTENTES']].groupby(['UF']).sum().reset_index()

df = df.rename(columns={
    "UF": "uf",
    "LEITOS_EXISTENTES": "beds_count"
})

df.to_csv(agg_file, index=False, sep=';')
