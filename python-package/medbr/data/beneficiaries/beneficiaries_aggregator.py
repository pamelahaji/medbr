from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
agg_file = HERE / 'transformed' / 'beneficiaries.csv'
agg_file.parent.mkdir(exist_ok=True)

# Each file is a quarterly snapshot of the same beneficiaries: summing several
# of them would count the same people more than once, so use only the latest.
latest = 'tb_br_2306.csv'
df = pd.read_csv(HERE / 'raw' / latest, sep=';')

df = df[['SG_UF', 'NR_BENEF_T']].groupby(['SG_UF']).sum().reset_index()

df = df.rename(columns={
    "SG_UF": "uf",
    "NR_BENEF_T": "beneficiaries_count"
})

df.to_csv(agg_file, index=False, sep=';')
