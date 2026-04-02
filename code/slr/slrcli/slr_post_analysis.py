import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Set, Annotated
import ast
from pathlib import Path
from jupyter_tikz import TexFragment
import typer


app = typer.Typer()

very_relevant_tasks = {
    "MIR", 
    "analysis", 
    "spatial analysis",
    "musicology",
    # "psychoacoustics",
    "visualization",
    "classification",
}

splitable_columns = ["audio model", "contents of signal", "specific datasets", "downstream task", "novel mechanism category", "spatial attributes", "spatial attribute novel/referenced/modified", "validation technique"]

def explode_comma_separated_lists(arr: pd.Series) -> pd.Series:
    def split_into_set(l):
        if type(l) == str:
            return set(map(str.strip, l.split(',')))
        else:
            return set()
    return pd.Series([split_into_set(a) for a in arr.values])

def split_lists(df, columns):
    for col in columns:
        df[col] = explode_comma_separated_lists(df[col])
    return df

def unique_terms_and_counts_in_series_of_sets(s: pd.Series) -> pd.Series:
    return pd.Series(np.hstack(s.map(list).to_numpy())).value_counts()

def map_value_in_set(arr: pd.Series, map: Dict[str, str]):
    def map_set(l: List[str]):
        return {map.get(s) or s for s in l}
    return arr.map(map_set)

def reject_non_music(df):
    things_that_count_as_music = {
        "music", 
        "instruments", 
        "sound art",
        "everything",
        "many",
        "mixed",
        # "HRTF",
        # "RIR"
    }
    not_music = df['contents of signal'].map(lambda s: bool(things_that_count_as_music & s)) == False
    not_already_rejected = df['reject'].isin(["n", "m_recent"]) == True
    df.loc[not_music & not_already_rejected, "reject"] = "full_not_music"
    return df

def reject_non_stereo(df):
    things_that_count_as_stereo = {
        "stereo", 
        "binaural",
    }
    not_stereo = df['audio model'].map(lambda s: bool(things_that_count_as_stereo & s)) == False
    not_already_rejected = df['reject'].isin(["n", "m_recent"]) == True
    df.loc[not_stereo & not_already_rejected, "reject"] = "full_not_stereo"
    return df

def reject_maybes_too_old(df):
    df.loc[df['reject'] == "m", 'reject'] = 'ta_borderline_too_old'
    return df

def reject_downstream_task(df):
    good = df['downstream task'].map(lambda s: bool(very_relevant_tasks & s)) == True
    not_already_rejected = df['reject'].isin(["n", "m_recent"]) == True
    df.loc[~good & not_already_rejected, "reject"] = "full_not_correct_task"
    return df

def correct_naming_inconsistances(df):
    df.loc[df['reject'] == "ta_english", 'reject'] = 'ta_not_english'
    return df

def clean_audio_model(df):
    audio_model_map = {
        "1st order ambisonic": "ambisonic",
        "4th order ambisonic": "ambisonic",
        "FOA": "ambisonic",
        "HOA": "ambisonic",
        "B-format": "ambisonic",
        "b-format": "ambisonic",
        "b-format ambisonic": "ambisonic",
        "a-format": "ambisonic",
        "ambisonics": "ambisonic",
        "Binaural": "binaural",
        "7.1.4": "multichannel",
    }

    df.loc[:,"audio model"] = map_value_in_set(df["audio model"], audio_model_map)
    return df


# Just clean a few of the contents that are relevent for music.
# Most will be rejected because they are not music anyway.
def clean_contents(df):
    contents_map = {
        "mix of noise/speech/music": "mixed",
        "mixed speech/music/noise/reverb": "mixed",
    }

    df.loc[:,"contents of signal"] = map_value_in_set(df["contents of signal"], contents_map)
    return df

def clean_referenced(df: pd.DataFrame) -> pd.DataFrame:
    _map = {
        "ref": "referenced",
        "reference": "referenced",
        "mod": "modified",
        "nov": "novel",
        "novel (maybe modified from self-attention)": "ref", # [Zhang, 2021] The neural network architechture was novel but the spatial features are not
    }

    df.loc[:,"spatial attribute novel/referenced/modified"] = map_value_in_set(df["spatial attribute novel/referenced/modified"], _map)
    return df 

def clean_downstream_task(df: pd.DataFrame) -> pd.DataFrame:
    _map = {
        "QOE": "quality prediction",
        "Quality evaluation": "quality prediction",
        "quality estimation": "quality prediction",
        "binaural quality prediction": "quality prediction",
        "spatial quality prediction": "quality prediction",
        "spatial quality metrics": "quality prediction",
        # "perceptual model": "quality prediction",
        # "perceptial modelling": "quality prediction",
        "perceptual modeling": "perceptual model",
        "sound field reconstruction": "quality prediction", # [Conceição, 2013] Quality of a reproduced sound field is assessed.
        "compressions": "compression",
        "mono->binaural upmix": "upmix",
        "upmixing low-order ambisonics to high-order": "upmix",
        "mono to ambisonic generation": "upmix",
        "separation": "source separation",
        "singing voice extraction": "source separation",
        "spatial decomposition": "source separation", # [Breebaart, 2006] Example is a singer's voice extracted from a rock track because it's in the centre
        "sound localization": "localization",
        "DOA": "localization",
        "estimate number of sources and panning of each source": "localization", 
        "front-back localization": "localization",
        "search": "spatial analysis", # [Antoniuk, 2023] "Search" is achieved through matching analysis results between two tracks
        "source enhancement": "enhancement",
        "stereo enhancement": "enhancement",
        "re-panning": "enhancement", # [Avendano, 2003] ADRESS, used for lots of enhancements
        "source suppresion": "enhancement", # [Avendano, 2003] ADRESS, used for lots of enhancements
        "stereo widening": "enhancement", # [Cobos, 2010]
        "room acoustic analysis": "acoustics",
        "speech/music classification": "classification",
        # "just noticeable difference": "perception", # [Klockgether, 2016]
        "BRIR rendering": "rendering",
        "AR/VR rendering": "rendering",
        "binaural rendering": "rendering",
        "ambisonic rendering": "rendering",
        "reverse engineering": "MIR", # [Colonel, 2021] Reverse engineering of mixing parameters
        "archival research": "MIR", # [D'Aleman Arango, 2021]
        "ensemble width": "MIR", # [Antoniuk and Zieliński, 2025]
        # "perceptual modeling": "perception",
        "pop music analysis": "MIR", # [Bourbon, 2023]
        "audio vizualization": "visualization",
        "audio visualization": "visualization",
        "ambience recording": "recording",
        "environmental sound segmentation": "source separation",
        "fundamental frequency estimation": "MIR",
        "automatic music transcription": "MIR",
        "analysis": "spatial analysis", # [Yang 2022, Takanen 2012]
        "neural singing synthesis": "synthesis", # [Zhao et al, 2025]
    }

    df.loc[:,"downstream task"] = map_value_in_set(df["downstream task"], _map)
    return df 


def clean_ss_authors(df):
    ss = df["db"] == "semantic_scholar"
    
    def __normalize_ss_authors(s):
        j = ast.literal_eval(s) # nice and safe 
        return "; ".join([a["name"] for a in j])
    
    df.loc[ss, "authors"] = df.loc[ss, "authors"].map(__normalize_ss_authors)
    return df


def num_studies(df, reasons):
    subset = df.loc[df["reject"].isin(reasons), "reject"]
    return len(subset)


def to_camel_case(snake_str):
    return "".join(x.capitalize() for x in snake_str.lower().split("_"))

def to_lower_camel_case(snake_str):
    # We capitalize the first letter of each component except the first one
    # with the 'capitalize' method and join them together.
    camel_string = to_camel_case(snake_str)
    return snake_str[0].lower() + camel_string[1:]


def latex_macro_name(key):
    return f"n{to_camel_case(key)}"

def latex_macro(name, val):
    return f'\\newcommand{{\\{name}}}{{{val}}}'


def clean_raw_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    cleaned = raw_data.copy(deep=True)
    cleaned = split_lists(cleaned, splitable_columns)
    cleaned = reject_maybes_too_old(cleaned)
    cleaned = correct_naming_inconsistances(cleaned)
    cleaned = clean_audio_model(cleaned)
    cleaned = clean_contents(cleaned)
    cleaned = clean_downstream_task(cleaned)
    cleaned = clean_referenced(cleaned)
    cleaned = reject_non_music(cleaned)
    # cleaned = reject_non_stereo(cleaned)
    cleaned = reject_downstream_task(cleaned)
    cleaned = clean_ss_authors(cleaned)
    return cleaned


def organize_rejection_reasons(cleaned: pd.DataFrame) -> pd.Series:
    reasons = set(cleaned["reject"].values)
    reasons_removed_before_screening = {"duplicate_by_doi", "duplicate_by_title_and_year"}
    reasons_screened = reasons - reasons_removed_before_screening
    reasons_excluded_after_screening = set([r for r in reasons_screened if r.startswith("ta_")])
    reasons_sought_for_retrieval = reasons_screened - reasons_excluded_after_screening
    reasons_not_retrieved = {"full_bad_record", "full_not_available", "m_full_bad_record", "m_full_not_available"}
    reasons_assessed_for_eligibility = reasons_sought_for_retrieval - reasons_not_retrieved
    reasons_excluded_not_very_relevant = {"full_not_correct_task"}
    reasons_excluded_after_assessment = set([r for r in reasons_assessed_for_eligibility if (r.startswith("full_") or r.startswith("m_full_")) and r not in reasons_excluded_not_very_relevant])
    reasons_included = reasons_assessed_for_eligibility - reasons_excluded_after_assessment
    reasons_included_very_relevant = reasons_included - reasons_excluded_not_very_relevant


    reasons_assessed_maybe = set([r for r in reasons_assessed_for_eligibility if r.startswith("m_")])
    reasons_assessed_definitely = set([r for r in reasons_assessed_for_eligibility if not r.startswith("m_")])
    reasons_included_maybe = set([r for r in reasons_included if r.startswith("m_")])
    reasons_included_definitely = set([r for r in reasons_included if not r.startswith("m_")])

    return pd.Series({
        "all": reasons,
        "removed_before_screening": reasons_removed_before_screening,
        "screened": reasons_screened,
        "excluded_after_screening": reasons_excluded_after_screening,
        "sought_for_retrieval": reasons_sought_for_retrieval,
        "not_retrieved": reasons_not_retrieved,
        "assessed_for_eligibility": reasons_assessed_for_eligibility,
        "excluded_not_very_relevant": reasons_excluded_not_very_relevant,
        "excluded_after_assessment": reasons_excluded_after_assessment,
        "included": reasons_included,
        "included_very_relevant": reasons_included_very_relevant,
        "assessed_maybe": reasons_assessed_maybe,
        "assessed_definitely": reasons_assessed_definitely,
        "included_maybe": reasons_included_maybe,
        "included_definitely": reasons_included_definitely,
    })


def calculate_inclusion_ratios(
    cleaned: pd.DataFrame, 
    reasons: pd.Series,
) -> pd.DataFrame:
    n_assessed_maybe = num_studies(cleaned, reasons["assessed_maybe"])
    n_assessed_definitely = num_studies(cleaned, reasons["assessed_definitely"])
    n_included_maybe = num_studies(cleaned, reasons["included_maybe"])
    n_included_definitely = num_studies(cleaned, reasons["included_definitely"])
    n_assessed = n_assessed_maybe + n_assessed_definitely
    n_included = n_included_maybe + n_included_definitely
    maybe_ratio = n_included_maybe/n_assessed_maybe
    definitely_ratio = n_included_definitely/n_assessed_definitely
    total_ratio = n_included / n_assessed

    maybes_inclusion_table = pd.DataFrame(columns=["Assessed", "Included", "Proportion"])
    maybes_inclusion_table.loc["Obvious"] = [n_assessed_definitely, n_included_definitely, f"{definitely_ratio*100:.0f}\\%"]
    maybes_inclusion_table.loc["Unclear"] = [n_assessed_maybe, n_included_maybe, f"{maybe_ratio*100:.0f}\\%"]
    maybes_inclusion_table.loc["Total"] = [n_assessed, n_included, f"{total_ratio*100:.0f}\\%"]

    return maybes_inclusion_table


# These need to be hard-coded because there's no record of them in the original search data
# for p in (cat followedreferences.txt); rg -c $p sn-article.tex; end | wc -l
def hard_coded_numbers_of_papers() -> pd.Series:
    return pd.Series({
        "followed_references": 15,
        "recommendation_service": 4,
        "peers": 5,
        "preprints": 14,
    })


def latex_macros_for_flow_diagram(s: pd.Series) -> pd.Series:
    flattened = pd.Series()
    preprints = hard_coded_numbers_of_papers()["preprints"]
    for k, v in s.items():
        if isinstance(v, Tuple):
            flattened[k] = v[0]
            flattened = pd.concat([flattened, v[1]])
        else:
            flattened[k] = v
    
    # This one is a bit of anomaly so just add it 
    flattened["preprints"] = preprints

    return '\n'.join([latex_macro(latex_macro_name(k), v) for k,v in flattened.items()])


def calculate_flow_diagram_data(
    cleaned: pd.DataFrame, 
    reasons: pd.Series,
) -> pd.Series:
    def _n_records_from_each_database(df):
        vals = df["db"].value_counts()
        return len(df), vals

    def _n_duplicates(df):
        removed = df[df.reject.isin(reasons["removed_before_screening"])].reject.value_counts().sort_values(ascending=False)
        return sum(removed), removed
    
    def _n_studies_from_other_sources():
        other_sources = pd.Series(hard_coded_numbers_of_papers().drop("preprints"))
        return sum(other_sources), other_sources
    
    def _n_reports_excluded(df):
        consolidated_reasons = {
            'full_no_spatial_descriptor': 'no_spatial_attribute',
            'm_full_no_spatial_descriptor': 'no_spatial_attribute',
            'full_stems_required': 'no_spatial_attribute',
            'm_full_mono': 'mono_audio',
            'full_mono': 'mono_audio',
            'm_full_duplicate': 'duplicate',
            'full_duplicate': 'duplicate',
            'full_not_music': 'not_music',
            'full_no_audio_signal': 'no_audio_signal',
            'full_not_audio': 'no_audio_signal',
            'm_full_book_review': 'not_research',
            'full_only_implementation': 'not_research',
            'full_patent': 'not_research',
            'full_only_subjective': 'only_subjective',
            'full_subjective': 'only_subjective',
            'm_full_not_english': 'not_english',
            'full_not_english': 'not_english',
            'full_english': 'not_english',
        }
        
        out = pd.Series()
        for r in reasons["excluded_after_assessment"]:
            rr = consolidated_reasons[r]
            if rr not in out:
                out[rr] = 0
            out[rr] += num_studies(df, set([r]))

        out.sort_values(ascending=False, inplace=True)
        return out.sum(), out
    
    return pd.Series({
        # These are the boxes that require lists. Each one is Tuple[total, Dict[str, int]].
        # The total value should equal the sum of the ints in the dict.
        "records_identified": _n_records_from_each_database(cleaned),
        "records_removed_before_screening": _n_duplicates(cleaned),
        "studies_from_other_sources": _n_studies_from_other_sources(),
        "studies_excluded": _n_reports_excluded(cleaned),

        # These are boxes that just require 1 number
        "records_screened": num_studies(cleaned, reasons["screened"]),
        "records_excluded": num_studies(cleaned, reasons["excluded_after_screening"]),
        "studies_sought_for_retrieval": num_studies(cleaned, reasons["sought_for_retrieval"]),
        "studies_not_retrieved": num_studies(cleaned, reasons["not_retrieved"]),
        "studies_assessed_for_eligibility": num_studies(cleaned, reasons["assessed_for_eligibility"]),
        "studies_included": num_studies(cleaned, reasons["included"]),
        "studies_included_very_relevant": num_studies(cleaned, reasons["included_very_relevant"]),
    })
    

def draw_flow_diagram(data: pd.Series):
    right_col_xshift = 6
    identified_height = 2
    blue_rect_yshift = 4

    def _latex_list(d: pd.Series):
        s = r'\begin{itemize}\small'
        for k, v in d.items():
            s += f'\\item {_printable_text(k)}: (n={v})'
        s += r'\end{itemize}'
        return s

    def _printable_text(s: str) -> str:
        out = s.replace('_', ' ')
        out = out[0].upper() + out[1:]
        return out

    def _box_list(name: str) -> str:
        total, breakdown = data[name]
        breakdown.index = breakdown.index.map(_printable_text)
        return f"{_printable_text(name)}: (n={total}){_latex_list(breakdown)}"
    
    def _box(name: str) -> str:
        value = data[name]
        return f"{_printable_text(name)} (n={value})"

    base = (
        r'\begin{tikzpicture}[>=latex, font={\small}, node distance=2cm]' + '\n'

        r'\tikzstyle{textrect} = [rectangle, minimum width=6cm, text width=5.99cm, minimum height=1cm, draw=black]' + '\n'
        r'\tikzstyle{bluerect} = [rectangle, rounded corners, minimum width=1.5cm, minimum height=0.75cm, text centered, draw=black, fill=cyan!60!gray!45!white, rotate=90]' + '\n'
        r'\tikzstyle{arrow} = [thick,->,>=stealth]' + '\n'
        
        f'\\node (identification_section) [bluerect, minimum width={identified_height}cm, yshift={blue_rect_yshift}cm] {{Identification}};' + '\n'
        f'\\node (databases) [textrect, minimum height={identified_height}cm] {{{_box_list("records_identified")}}};' + '\n'
        f'\\node (removed_before_screening) [textrect, right of=databases, xshift={right_col_xshift}cm, minimum height={identified_height}cm] {{{_box_list("records_removed_before_screening")}}};' + '\n'

        f'\\node (screening_section) [bluerect, minimum width=9cm, yshift={blue_rect_yshift}cm, xshift=-6.5cm] {{Screening}};' + '\n'
        f'\\node (screened) [textrect, below of=databases, yshift=-0.5cm] {{{_box("records_screened")}}};' + '\n'
        f'\\node (excluded) [textrect, right of=screened, xshift={right_col_xshift}cm] {{{_box("records_excluded")}}};' + '\n'
        f'\\node (sought) [textrect, below of=screened] {{{_box("studies_sought_for_retrieval")}}};' + '\n'
        f'\\node (not_retrieved) [textrect, right of=sought, xshift={right_col_xshift}cm] {{{_box("studies_not_retrieved")}}};' + '\n'
        f'\\node (assessed) [textrect, below of=sought] {{{_box("studies_assessed_for_eligibility")}}};' + '\n'
        f'\\node (arrowanchor) [right of=assessed, xshift={right_col_xshift-3}cm] {{}};' + '\n'
        f'\\node (rep_excluded) [textrect, right of=assessed, xshift={right_col_xshift}cm, yshift=-2cm, minimum height=5cm] {{{_box_list("studies_excluded")}}};' + '\n'
        
        f'\\node (included) [textrect, below of=assessed, yshift=-4.25cm, minimum height=1.5cm] {{Studies included in review: (n={data["studies_included"]})\\\\Of which very relevant: (n={data["studies_included_very_relevant"]})}};' + '\n'
        f'\\node (included_section) [bluerect, left of=included, minimum width=4.5cm, yshift={blue_rect_yshift}cm, xshift=0.5cm] {{Included}};' + '\n'
        f'\\node (othersources) [textrect, below of=included, yshift=-0.5cm, minimum height=2.5cm] {{{_box_list("studies_from_other_sources")}}};' + '\n'

        r'\draw [arrow] (databases) -- (removed_before_screening);' + '\n'
        r'\draw [arrow] (databases) -- (screened);' + '\n'
        r'\draw [arrow] (screened) -- (excluded);' + '\n'
        r'\draw [arrow] (screened) -- (sought);' + '\n'
        r'\draw [arrow] (sought) -- (not_retrieved);' + '\n'
        r'\draw [arrow] (sought) -- (assessed);' + '\n'
        r'\draw [arrow] (assessed.east) -- (arrowanchor);' + '\n'
        r'\draw [arrow] (assessed) -- (included);' + '\n'
        r'\draw [arrow] (included) -- (othersources);' + '\n'
        
        r'\end{tikzpicture}' + '\n'
    )
    return base



def downstream_tasks_table(
    cleaned: pd.DataFrame,
    reasons_included: Set[str],
) -> pd.DataFrame:
    """
    Create appendix of downstream tasks explaining the very relevant ones
    """

    included_studies = cleaned.loc[cleaned.reject.isin(reasons_included)]
    tasks = unique_terms_and_counts_in_series_of_sets(included_studies["downstream task"])
    # very_relevant = {
    #     "MIR": "The information retrieved can be considered a description of the recording",
    #     "spatial analysis": "Spatial analysis techniques can be used as spatial descriptors",
    #     "musicology": "Concerned with patterns in musical corpora as opposed to low-level features",
    #     # "psychoacoustics": "Knowledge of how humans hear can be used to describe spatial features", 
    #     "visualization": "Visualization is condidered a form of high-level description",
    #     "classification": "Concerned with patterns in musical corpora as opposed to low-level features", 
    # }

    tasks_df = pd.DataFrame({
        "Task": tasks.index,
        "Count": tasks.values,
        "Very Relevant": ["yes" if t in very_relevant_tasks else "no" for t in tasks.index],
    })

    tasks_df.sort_values(by=["Very Relevant", "Count"], inplace=True, ascending=False)

    tasks_df.loc[tasks_df["Task"] == "MIR", "Task"] = "\\gls{mir}"
    tasks_df.loc[tasks_df["Task"] == "cross-modal ML", "Task"] = "cross-modal \\gls{ml}"
    return tasks_df


def downstream_tasks_table_latex(
    tasks_df: pd.DataFrame,
    tex_out: str,
):
    """
    Write a latex table for the dataframe of downstream tasks.
    Insert a mid rule between the yes's and no's.
    """
    text = tasks_df.to_latex(index=False, column_format="lcc").splitlines()
    first_no = np.min(np.argwhere([line.endswith("no \\\\") for line in text]))
    text.insert(first_no, "\\midrule")
    Path(tex_out).write_text('\n'.join(text))


@app.command()
def post_process(
    raw_data_tsv: str,
    inclusion_ratios_tex: str = "inclusion_ratios.tex",
    number_macros_tex: str = "number_macros.tex",
    flow_diagram_tex: str = "flow_diagram.tex",
    downstream_tasks_tex: str = "all_tasks.tex",
):
    # Organize the original data
    raw_data = pd.read_csv(raw_data_tsv, sep="\t")
    cleaned = clean_raw_data(raw_data)
    reasons = organize_rejection_reasons(cleaned)
    
    # Make table showing the ratios of "definitely" and "maybe" studies that were eventually included
    inclusion_ratios = calculate_inclusion_ratios(cleaned, reasons)
    print(f"Inclusion ratios:\n{inclusion_ratios}\n")
    inc_table_tex = inclusion_ratios.to_latex(column_format='rccc')
    inc_table_tex = inc_table_tex.splitlines()
    inc_table_tex.insert(-3, '\\midrule')
    inc_table_tex = '\n'.join(inc_table_tex)
    Path(inclusion_ratios_tex).write_text(inc_table_tex)

    # Calculate the numbers of papers that were rejected for specific reason and draw the PRISMA flow diagram
    flow_diagram_data = calculate_flow_diagram_data(cleaned, reasons)
    print(f"Flow diagram data:\n{flow_diagram_data}\n")

    # Write those numbers as latex macros so they can be referenced in the text...
    number_macros = latex_macros_for_flow_diagram(flow_diagram_data)
    Path(number_macros_tex).write_text(number_macros)
    
    # ... and draw the diagram
    flow_diagram_tikz = draw_flow_diagram(flow_diagram_data)
    Path(flow_diagram_tex).write_text(flow_diagram_tikz)
    
    # ... and an SVG for debugging
    Path(flow_diagram_tex).with_suffix('.svg').write_text(TexFragment(flow_diagram_tikz).run_latex().data)

    # Write table of downstream tasks, showing which were very relevant
    all_tasks = downstream_tasks_table(cleaned, reasons["included"])
    print(f"All downstream tasks:\n{all_tasks}\n")
    downstream_tasks_table_latex(all_tasks, downstream_tasks_tex)


@app.command()
def included_studies(
    raw_data_tsv: str,
    included_tsv: str,
    very_relevant_tsv: str,
    with_non_music_tsv: str,
):
    raw_data = pd.read_csv(raw_data_tsv, sep="\t")
    cleaned = clean_raw_data(raw_data)
    reasons = organize_rejection_reasons(cleaned)
    print(reasons)
    print(reasons["all"])

    included = cleaned[cleaned.reject.isin(reasons["included"])]
    very_relevant = cleaned[cleaned.reject.isin(reasons["included_very_relevant"])]
    with_non_music = cleaned[cleaned.reject.isin(reasons["included"] | {'ta_not_music', 'full_not_music'})]

    included.to_csv(included_tsv, sep='\t')
    very_relevant.to_csv(very_relevant_tsv, sep='\t')
    with_non_music.to_csv(with_non_music_tsv, sep='\t')

@app.command()
def random_sample(
    raw_data_tsv: str,
    sample_tsv: str,
    random_state: int = 0
):
    raw_data = pd.read_csv(raw_data_tsv, sep="\t")
    cleaned = clean_raw_data(raw_data)
    duplicate_reasons = [
        "duplicate_by_doi",
        "duplicate_by_title_and_year",
        "full_duplicate",
        "m_full_duplicate",
        "ta_duplicate_manual",
    ]
    no_duplicates = cleaned[~cleaned.reject.isin(duplicate_reasons)]
    random_sample = no_duplicates.sample(frac=0.05, random_state=random_state)
    random_sample.to_csv(sample_tsv, sep='\t', index=None)


# This command is basically unconnected to the other stuff, so keep it separate
@app.command()
def write_datasets_table(
    datasets_tsv: str = "datasets_from_review.tsv",
    latex_out: str = "datasets.tex",
):
    datasets = pd.read_csv(datasets_tsv, sep='\t')
    use = datasets["Use"].notna()
    datasets = datasets[[
        "Name", 
        "acronym", 
        "reference", 
        "Audio format", 
        "Size (number of music tracks)", 
        "Duration",
        "Multitrack", 
        "Stereo", 
        "Binaural", 
        "Availabilty of audio",
        "Notes", 
    ]][use]

    datasets.rename(columns={
        "Size (number of music tracks)": "Size",
        "Multitrack": "M",
        "Stereo": "S",
        "Binaural": "B",
        "Availabilty of audio": "Availability",
    }, inplace=True)
    datasets.fillna(value="", inplace=True)


    def _make_name(row):
        name, acr, ref = row
        a = f"\\glsxtrshort{{{acr}}}" if acr else name
        return a + ref

    datasets["reference"] = datasets["reference"].map(lambda r: f"\\cite{{{r}}}")
    short_names = datasets[["Name","acronym", "reference"]].apply(_make_name, axis=1)
    datasets["Name"] = short_names

    datasets[["M", "S", "B"]] = datasets[["M", "S", "B"]].map(lambda s: '\checkmark' if s == 'y' else "")


    def _maybe_int(s):
        just_digits = "".join([c for c in s if c in "0123456789"])
        try:
            return int(just_digits)
        except:
            return -1

    datasets["sort_order"] = datasets["Size"].map(_maybe_int)
    datasets.sort_values(by="sort_order", ascending=False, inplace=True)

    def replace_download_text_with_note(s):
        return s\
            .replace(" individual tracks", "\\textsuperscript{$\\star$}")\
            .replace(" individual files", "\\textsuperscript{$\\dagger$}")\
            .replace(" request access", "\\textsuperscript{$\\ddagger$}")\
            .replace(", contact admin", "\\textsuperscript{$\\ddagger$}")\
            .replace(", commercial", "")
    datasets["Availability"] = datasets["Availability"].map(replace_download_text_with_note)

    def replace_size_text_with_note(s):
        return s\
            .replace(" unclear", "\\textsuperscript{$\S$}")\
            .replace(" notracks", "\\textsuperscript{$\|$}")

    datasets["Size"] = datasets["Size"].map(replace_size_text_with_note)
    datasets["Duration"] = datasets["Duration"].map(replace_size_text_with_note)

    def _escape_chars(s):
        return s.replace("%", "\\%")

    datasets["Notes"] = datasets["Notes"].map(_escape_chars)

    datasets.drop(columns=[
        "acronym", 
        "reference", 
        "sort_order", 
    ], inplace=True)

    column_format = 'l' * (len(datasets.columns) - 1) + 'X'

    ltx = datasets.to_latex(index=False, column_format=column_format)\
        .replace('\\begin{tabular}{', '\\begin{tabularx}{\\textheight}{')\
        .replace('\\end{tabular}', '\\end{tabularx}')

    Path(latex_out).write_text(ltx)

@app.command()
def supplementary(
    all_data_tsv: Annotated[str, typer.Argument(help="File path of complete results, with or without annotations")],
    supplementary_data_csv: Annotated[str, typer.Argument(help="File path of output supplementary file")],
    appendix_table_tex: Annotated[str, typer.Argument(help="File path of appendix table tex file")],
):
    df = pd.read_csv(all_data_tsv, sep='\t').fillna("")
    df_out = pd.DataFrame()
    for db in ['scopus', 'web_of_science', 'semantic_scholar']:
        df_db = df[df.db == db]
        print(db, df_db.shape)
        df_out = pd.concat([df_out, df_db.sort_values("year", ascending=False)])
    want_colums = pd.Series({
        "url": "The \\gls{url} of the record within the database",
        "title": "The title of the article",
        "abstract": "The abstract of the article",
        "year": "The year of publication",
        "authors": "The authors of the article, in the raw format given by the search results",
        "source": "The publication venue",
        "DOI": "The \\gls{doi} of the article",
        "db": "The name of the database from which the record was extracted",
        "db_id": "The unique identifier within the database",
    })
    df_out[want_colums.index].to_csv(supplementary_data_csv, index=None)
    explanation_table = pd.DataFrame({"Header": want_colums.index, "Explanation": want_colums.values})
    
    ltx = explanation_table.to_latex(
        index=False,
        formatters = {
            "Header": lambda h: f"\\verb|{h}|"
        }
    ).replace("tabular", "tabularx").replace("{ll}", "{\\textwidth}{lX}")
    Path(appendix_table_tex).write_text(ltx)


@app.command()
def post_hoc(
    post_hoc_tsv: Annotated[str, typer.Argument(help="File path of post-hoc annotations")], 
    table_tex: Annotated[str, typer.Argument(help="File path of results table tex file")],
):
    df = pd.read_csv(post_hoc_tsv, sep='\t').fillna("")
    
    def _mapper(s: str) -> str:
        mapping = {
            "ta_not_audio": "not_audio",
            "full_not_audio": "not_audio",
            "ta_no_spatial_analysis": "no_spatial_analysis",
            "ta_no_spatial_descriptor": "no_spatial_analysis",
            "m_full_no_spatial_descriptor": "no_spatial_analysis",
            "full_no_spatial_descriptor": "no_spatial_analysis",
            "ta_not_music": "not_music",
            "full_not_music": "not_music",
            "n": "no",
            "m": "unclear_too_old",
            "m_recent": "unclear",
            "ta_not_english": "not_english",
            "ta_english": "not_english",
            "full_not_english": "not_english",
        }
        return mapping.get(s, s)

    # Map Richard's tags to the same text that Andreas was given in the dropdown menu
    df['reject'] = df["reject"].map(_mapper)

    # Blank fields required deiscussion. Mark them as unclear.
    df.loc[df['Reject Andreas'].isna(), 'Reject Andreas'] = 'unclear'

    # Reject Andreas' maybes that are too old.
    df.loc[(df.year < 2020) & (df['Reject Andreas'] == 'unclear'), 'Reject Andreas'] = 'unclear_too_old'
    
    outcomes = pd.DataFrame(
        [
            ("Both included", "OK"),
            ("Initially rejected, post-hoc included", "Researchers discuss"),
            ("Initially accepted, post-hoc rejected", "OK"),
            ("Rejected for same reason", "OK"),
            ("Rejected for different reasons","OK"),
        ],
        columns=["Outcome", "Treatment"]
    )

    def _decide_outcome(row: pd.Series):
        # Returns index into outcomes table
        if (row['reject'] == 'no' and row['Reject Andreas'] == 'no') or (row['reject'] == 'unclear' and row['Reject Andreas'] == 'unclear'):
            return outcomes.loc[0, "Outcome"]
        elif row['reject'] != 'no' and row['Reject Andreas'] == 'no':
            return outcomes.loc[1, "Outcome"]
        elif row['reject'] == 'no' and row['Reject Andreas'] != 'no':
            return outcomes.loc[2, "Outcome"]
        elif row['reject'] == row['Reject Andreas']:
            return outcomes.loc[3, "Outcome"]
        elif row['reject'] != row['Reject Andreas']:
            return outcomes.loc[4, "Outcome"]
        else:
            raise Exception("This shouldn't happen...")

    df["post_hoc_outcome"] = df.apply(_decide_outcome, axis=1)

    counts = df["post_hoc_outcome"].value_counts()

    outcomes["Count"] = outcomes["Outcome"].map(counts)
    outcomes = outcomes.iloc[:, [0,2,1]] # Reorder columns to get count in the middle
    outcomes.sort_values(by="Count", inplace=True)
    
    # append total
    outcomes.loc[len(outcomes)] = ["Total", outcomes.Count.sum(), "--"]

    # and put a midrule between the values and the total
    tex = outcomes.to_latex(index=False, column_format='lcl')
    tex = tex.splitlines()
    # tex.insert(-3, '\\cmidrule{1-2}')
    tex.insert(-3, '\\midrule')
    tex = '\n'.join(tex)

    Path(table_tex).write_text(tex)
    print(outcomes)