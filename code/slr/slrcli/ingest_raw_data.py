import pandas as pd
import json
from typing import List
import typer

#uv run ingest_raw_data.py scopus_2024-2026.csv wos_2024-2026.txt ss_2024-2026.tsv SLR_2024-09-30_raw_data.tsv SLR_Feb_2026-data.tsv data_2024-2026_searched_on_20260226.tsv

app = typer.Typer()



def extract_DOI_wob(df):
    return df["DI"]

def extract_DOI_scopus(df):
    return df["DOI"]

def extract_DOI_ss(df):
    return df["externalIds"].map(lambda d: json.loads(d.replace('\'', '\"')).get('DOI', ""))

def normalize_title_for_comparison(title):
    return ''.join(char for char in title if char.isalnum()).lower()

def normalize_scopus(df):
    col_map = {
        "Link": "url", 
        "Title":"title",
        "Abstract": "abstract",
        "Year": "year",
        "Authors": "authors",
        "Source title": "source",
        "DOI": "DOI",
        "Cited by": "citation_count",
    }
    out = df[["Link", "Title", "Abstract", "Year", "Authors", "Source title", "DOI", "Cited by"]].rename(columns=col_map)
    out['year'] = out['year'].map(int)
    out['db'] = 'scopus'
    out['db_id'] = df['EID']
    return out

def normalize_wos(df):
    urls = df["UT"].map(lambda x: f"https://www-webofscience-com.ep.bib.mdh.se/wos/woscc/full-record/{x}")
    titles = df["TI"]
    abstracts = df["AB"]
    years = df["PY"].map(int)
    authors = df["AU"]
    dois = df["DI"]
    citation_count = df['TC']
    return pd.DataFrame({
        "url": urls,
        "title": titles,
        "abstract": abstracts,
        "year": years,
        "authors": authors,
        "source": "none",
        "DOI": dois,
        'citation_count': citation_count,
        "db": "web_of_science",
        "db_id": df["UT"],
    })


def normalize_ss(df):
    dois = df["DOI"] = extract_DOI_ss(df)
    out = df[["url", "title", "abstract", "year", "authors", "venue", "citationCount"]].rename(columns={"venue": "source", "citationCount": "citation_count"})
    out['year'] = out['year'].map(lambda x: int(x) if x else -1)
    out["DOI"] = dois
    out["db"] = "semantic_scholar"
    out["db_id"] = df["paperId"]
    return out


def normalize_all(scopus_df, wos_df, ss_df, fill_columns):
    df = pd.concat([
        normalize_scopus(scopus_df),
        normalize_wos(wos_df),
        normalize_ss(ss_df),
    ]).reset_index()
    del df['index']
    df["reject"] = ""
    df[fill_columns] = ""
    return df


def mark_duplicates(df):
    seen = set()
    title_and_year_seen = set()
    for idx, row in df.iterrows():
        doi = row['DOI']
        this_title = normalize_title_for_comparison(row['title'])
        this_year = row['year']
        if doi != '':
            if doi in seen:
                df.loc[idx, "reject"] = "duplicate_by_doi"
            else:
                seen.add(doi)
        elif (this_title, this_year) in title_and_year_seen:
            df.loc[idx, "reject"] = "duplicate_by_title_and_year"
        
        title_and_year_seen.add((this_title, this_year))
    
    return df


def mark_already_processed_2024(df: pd.DataFrame, already: pd.DataFrame):
    already_processed_title_years = already["norm_title_year"].values
    already_processed_doi = already["DOI"].dropna().values
    for idx, row in df.iterrows():
        # Do nothing if we've already rejected for another reason
        if row['reject']:
            continue
        doi = row['DOI']
        title_year = row['norm_title_year']
        if doi in already_processed_doi:
            df.loc[idx, "reject"] = "already_processed_doi"
        elif title_year in already_processed_title_years:
            df.loc[idx, "reject"] = "already_processed_title_year"
    return df


def fill_data_2026(df: pd.DataFrame, df_2026: pd.DataFrame, fill_columns: List[str]):
    for idx, row in df.iterrows():
        if row['reject']:
            continue

        record_by_doi = df_2026[df_2026['DOI']==row['DOI']]
        if not record_by_doi.empty:
            df.loc[idx, fill_columns] = record_by_doi.iloc[0][fill_columns]
        
        record_by_title_year = df_2026[df_2026['norm_title_year']==row['norm_title_year']]
        if not record_by_title_year.empty:
            df.loc[idx, fill_columns] = record_by_title_year.iloc[0][fill_columns]
    
    return df
        



def add_norm_title_year(df):
    df["norm_title_year"] = df[["title", "year"]].apply(lambda row: f"{normalize_title_for_comparison(row['title'])}_{row['year']}", axis=1)
    # df["norm_title_year"] = f"{normalize_title_for_comparison(df['title'])}_{df['year']}"
    return df



@app.command()
def ingest(
    scopus: str,
    wos: str,
    ss: str,
    processed2024: str,
    processed2026: str,
    out: str,
    outsep: str = '\t',
):
    """
    Ingest raw data from the second search (2026) normalize it, and join it with the original annotaded data.
    The script was made when there were already some annoations done for 2026, which is why the 'processed2026' argument exists.
    Data is stored in the data/raw or data/annotated folders. Write the results to the data/generated folder.

    Example use: slrcli ingest data/raw/scopus_2024-2026.csv data/raw/wos_2024-2026.txt data/raw/ss_2024-2026.tsv data/annotated/SLR_2024-09-30_raw_data.tsv data/annotated/SLR_Feb_2026-data.tsv data/generated/ingested_data.tsv
    """
    wos_papers = pd.read_csv(wos, sep='\t').fillna("")
    scopus_papers = pd.read_csv(scopus).fillna("")
    ss_papers = pd.read_csv(ss, sep='\t').fillna("")

    already_processed_2024 = pd.read_csv(processed2024, sep='\t')
    already_processed_2026 = pd.read_csv(processed2026, sep='\t')

    fill_columns = [
        "reject",
        "audio model", 
        "specific audio conditions / mic configurations / etc", 
        "contents of signal", 
        "specific datasets",
        "downstream task",
        "novel mechanism category",
        "spatial attributes",
        "spatial attribute novel/referenced/modified",
        "validation technique",
        "done date",
        "notes"
    ]

    df = normalize_all(scopus_papers, wos_papers, ss_papers, fill_columns)
    df = add_norm_title_year(df)
    already_processed_2024 = add_norm_title_year(already_processed_2024)
    already_processed_2026 = add_norm_title_year(already_processed_2026)
    df = mark_duplicates(df)
    df = mark_already_processed_2024(df, already_processed_2024)
    df = fill_data_2026(df, already_processed_2026, fill_columns)

    for group, group_df in df.groupby(by=['db', 'reject']):
        print(group, len(group_df))

    print(df["reject"].value_counts())

    # print('Duplicate by DOI', (df["reject"] == "duplicate_by_doi").sum())
    # print('Duplicate by title and year', (df["reject"] == "duplicate_by_title_and_year").sum())
    # print('Not duplicate', (df["reject"] == "").sum())

    df.to_csv(out, sep=outsep)