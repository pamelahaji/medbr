from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
agg_file = HERE / 'transformed' / 'birth.csv'
agg_file.parent.mkdir(exist_ok=True)

frames = []
for year in ['2021', '2022']:
    df = pd.read_csv(HERE / 'raw' / f'data_{year}.csv', sep=';', dtype={'DTNASC': str})

    df['DTNASC'] = pd.to_datetime(df['DTNASC'], format='%d%m%Y')
    df = df[['CODMUNNASC', 'DTNASC', 'HORANASC']].groupby(['CODMUNNASC', 'DTNASC']).count().reset_index()

    frames.append(df.rename(columns={
        "CODMUNNASC": "city_code",
        "DTNASC": "birth_date",
        "HORANASC": "birth_count"
    }))

# written once, so running the script again never duplicates rows
pd.concat(frames).to_csv(agg_file, index=False, sep=';')
