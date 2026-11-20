from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
agg_file = HERE / 'transformed' / 'mortality.csv'
agg_file.parent.mkdir(exist_ok=True)

frames = []
for year in ['2021', '2022']:
    df = pd.read_csv(HERE / 'raw' / f'data_{year}.csv', sep=';', dtype={'DTOBITO': str})

    df['DTOBITO'] = pd.to_datetime(df['DTOBITO'], format='%d%m%Y')
    df = df[['CODMUNOCOR', 'DTOBITO', 'HORAOBITO']].groupby(['CODMUNOCOR', 'DTOBITO']).count().reset_index()

    frames.append(df.rename(columns={
        "CODMUNOCOR": "city_code",
        "DTOBITO": "death_date",
        "HORAOBITO": "death_count"
    }))

# written once, so running the script again never duplicates rows
pd.concat(frames).to_csv(agg_file, index=False, sep=';')
