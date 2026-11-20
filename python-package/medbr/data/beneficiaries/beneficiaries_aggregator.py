from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
agg_file = HERE / 'transformed' / 'beneficiaries.csv'
agg_file.parent.mkdir(exist_ok=True)

files = ['tb_br_2209.csv', 'tb_br_2212.csv', 'tb_br_2303.csv', 'tb_br_2306.csv']
df = pd.concat([pd.read_csv(HERE / 'raw' / f, sep=';') for f in files])

df = df[['SG_UF', 'NR_BENEF_T']].groupby(['SG_UF']).sum().reset_index()

df = df.rename(columns={
    "SG_UF": "uf",
    "NR_BENEF_T": "beneficiaries_count"
})

df.to_csv(agg_file, index=False, sep=';')
