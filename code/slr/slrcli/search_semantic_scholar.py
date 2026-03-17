import requests
import json
from requests.adapters import HTTPAdapter  # type: ignore
from urllib3.util import Retry
import pandas as pd
from io import StringIO
from typing import Annotated

import typer

app = typer.Typer()

# semantic scholar API
class SemanticScholar:

    API_BASE = "https://api.semanticscholar.org"
    GRAPH_BASE = f"{API_BASE}/graph"
    RECOMMENDATION_BASE = f"{API_BASE}/recommendations"

    def __init__(self):
        self.session = requests.Session()
        retries = Retry(
            total=4,
            backoff_factor=0.3,
            status_forcelist=[429],
            allowed_methods={"GET"},
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def paper_details(self, ids):
        fields = [
            "influentialCitationCount",
            "citationCount",
            "title",
            "venue",
            "publicationVenue",
            "abstract",
            "tldr",
            "referenceCount",
            "citationStyles",
            "year",
            "openAccessPdf",
            "authors",
            "embedding.specter_v2",
            "url",
            "fieldsOfStudy",
            "s2FieldsOfStudy",
            "publicationTypes",
            "embedding",
            "journal",
        ]
        params = {"limit": 200, "fields": ",".join(fields)}
        url = f"{self.GRAPH_BASE}/v1/paper/batch"
        response = self.session.post(
            url,
            params=params,
            json={"ids": ids}
        ).json()
        return response

    @staticmethod
    def _search_params(query, year):
        fields = [
            "influentialCitationCount",
            "citationCount",
            "title",
            "venue",
            "abstract",
            "referenceCount",
            "citationStyles",
            "year",
            "openAccessPdf",
            "authors",
            "url",
            "fieldsOfStudy",
            "s2FieldsOfStudy",
            "externalIds",
        ]
        fieldsOfStudy = [
            "Computer Science",
            "Mathematics",
            "Engineering",
        ]
        return {
            "query": query,
            "limit": 20000,
            "fields": ",".join(fields),
            "fieldsOfStudy": fieldsOfStudy,
            "token": None,
            "year": year,
        }
    
    def search(self, query, year):
        params = self._search_params(query, year)
        data = []
        while True:
            response = self.session.get(f"{self.GRAPH_BASE}/v1/paper/search/bulk", params=params)
            try:
                response.raise_for_status()
            except Exception as e:
                print(response.json())
                raise e
            response = response.json()
            print(f"got {response['total']} results with token {response['token']}")
            data += response['data']
            params["token"] = response.get("token", None)
            if params["token"] is None:
                break
        
        return pd.read_json(StringIO(json.dumps(data)))
            

@app.command()
def search_ss(
    year: Annotated[str, typer.Argument(help="Year range to search. Use e.g. 2024- to search for 2024 onwards")],
    out: Annotated[str, typer.Argument(help="Output file path")],
    outsep: Annotated[str, typer.Argument(help="Output file separator")] = '\t',
):
    query = '''(("music" | "musical" | "audio" | "sound") + ("stereo" | "stereophonic" | "binaural" | "spatial audio" | "ambisonic" | "ambisonics" | "b-format" | "multi-channel") + ("panning" | "information retrieval" | "spaciousness" | "descriptors" | "spatial image" | "stereo image" | "spatial cues" | "disentangle" | "disentangling" | "disentanglement" | "spatial decomposition" | "spatial information" | "spatial descriptors" | "spatial quality" | "spatial analysis" | "binaural model" | "goniometer" | "lissajous plot" | "systematic review")) | ("spatial audio coding" | "spatial audio object coding" | "directional audio coding" | "binaural cue coding" | "panning spectrogram" | "stereo panning spectrum" | "object-based audio" | "mpeg-h audio" | "mpeg-h 3D audio" | "dolby atmos" | "sony 360 audio" | "sony 360 RA" | "360 reality audio" | "QESTRAL")
    '''
    ss = SemanticScholar()
    papers = ss.search(query, year)
    papers.to_csv(out, sep=outsep)

