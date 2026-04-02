from pathlib import Path

import pandas as pd
import typer


app = typer.Typer()


def normalize_title_for_comparison(title):
    return ''.join(char for char in title if char.isalnum()).lower()

def add_norm_title_year(df):
    df = df.copy()
    df["norm_title_year"] = df[["title", "year"]].apply(lambda row: f"{normalize_title_for_comparison(row['title'])}_{row['year']}", axis=1)
    df["identifier"] = df[["DOI", "norm_title_year"]].apply(lambda row: row["DOI"] if row["DOI"] else row["norm_title_year"], axis=1)
    return df



@app.command()
def join(
    tsv2024: str, 
    tsv2026: str,
    tsv_all_out: str,
) -> pd.DataFrame:
    
    """
    Join the annotated data from 2024 and 2026 into a single file.
    Data is stored in the data/annotated folder.
    Save the output to the data/generated folder.

    Example use: slrcli join data/annotated/SLR_2024-09-30_raw_data.tsv data/annotated/data_2024-2026_searched_on_20260226_annotated.tsv data/generated/all_data_2026-03-16.tsv
    """

    df2024 = pd.read_csv(tsv2024, sep='\t', index_col=0).fillna("") # The original dataset has an unnamed index column. Not sure how that happened.
    df2026 = pd.read_csv(tsv2026, sep='\t').fillna("")

    already = df2026[df2026.reject.isin(["already_processed_doi", "already_processed_title_year"])].index
    df2026.drop(index=already, inplace=True)

    dfall = pd.concat([df2024, df2026], ignore_index=True)
    # print(dfall.columns)

    want_columns = ['url', 'title', 'abstract', 'year', 'authors', 'source', 'DOI', 'db_id', 'db', 'reject', 'audio model', 'specific audio conditions / mic configurations / etc', 'contents of signal', 'specific datasets', 'downstream task', 'novel mechanism category', 'spatial attributes', 'spatial attribute novel/referenced/modified', 'validation technique', 'full paper found', 'done date', 'notes', 'norm_title_year']

    dfall = dfall[want_columns]
    dfall = add_norm_title_year(dfall)

    dfall.to_csv(tsv_all_out, sep='\t', index=None)
    print(dfall)

    return dfall