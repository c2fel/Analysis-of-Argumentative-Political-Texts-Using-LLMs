import inspect
import json
import os
import hashlib
import sys

import tiktoken
from datetime import datetime, time
import time

from dotenv import load_dotenv
from enum import Enum, IntEnum
from typing import List, Optional, Any
from pydantic import BaseModel, Field, computed_field, validator

import openai
from xai_sdk import Client
from xai_sdk.search import SearchParameters, web_source
from xai_sdk.chat import system, user

load_dotenv()

# TODO: This is depreciated, model configs are saved in .env
MODELS = {'grok-4-0709': {'context_window': 256000, 'cost_per_M_input_tokens': 3, 'cost_per_M_output_tokens': 15},
          'grok-3-mini': {'context_window': 131072, 'cost_per_M_input_tokens': 0.30, 'cost_per_M_output_tokens': 0.50},
          'gpt-5-2025-08-07': {'context_window': 400000, 'cost_per_M_input_tokens': 1.25, 'cost_per_M_output_tokens': 10},
          'gpt-5-mini-2025-08-07': {'context_window': 400000, 'cost_per_M_input_tokens': 0.25, 'cost_per_M_output_tokens': 2},
          'gpt-5-nano-2025-08-07': {'context_window': 400000, 'cost_per_M_input_tokens': 0.05, 'cost_per_M_output_tokens': 0.40},
          'Apertus-70B': {'context_window': 65536, 'cost_per_M_input_tokens': 0, 'cost_per_M_output_tokens': 0},
          'Apertus-8B': {'context_window': 65536, 'cost_per_M_input_tokens': 0, 'cost_per_M_output_tokens': 0}
          }

MAX_RETRIES = 3 # TODO: This is not implemented yet


def classify_topic_by_title(client, title="Bundesbeschluss über den Ausbauschritt 2023 für die Nationalstrassen"):
    # TODO reference this in the Thesis https://www.arxiv.org/pdf/2508.03181
    prompt = f"""Given the classes Environment, Social Affairs and Education, Economy and Finance, Foreign and Security Policy, Infrastructure and Transportation, Health and Other, classify the following popular vote in Switzerland by its title: {title}. Only output the class label, no reasoning at all."""

    try:
        classification_chat = client.chat.create(
            model="grok-4",
            messages=[
                system(
                    "You are a highly intelligent AI assistant helping Swiss citizens to freely form an opinion on their own by adding context to their questions and task."),
                user(prompt)
            ]
        )
        response = classification_chat.sample()

        if not response.content or not response.content.strip():
            print(f"Fehler: Leere Antwort für Vorlagentitel: '{title}'")
            return "Error"

        content_list = response.content.split()
        if not content_list:
            print(f"Fehler: Keine gültigen Token in der Antwort für '{title}'")
            return "Error"

        return content_list[0]
    except IndexError:
        print(f"IndexError: Keine gültigen Daten in der Antwort für '{title}'")
        return "Error"
    except Exception as e:
        print(f"Fehler bei der Verarbeitung von Vorlagentitel: '{title}': {e}")
        return "Error"


def score_complexity_by_markdown(client, path_to_markdown="../markdown_output/erlaeuterungen_6770_de.md", retry=""):
    model = 'grok-4-0709' # change this later when multiple models are implemented
    try:
        with open(path_to_markdown, "r", encoding="utf-8") as f:
            markdown_content = f.read()
    except FileNotFoundError:
        print(f"Error: Markdown file {path_to_markdown} not found")
        return "Error"
    except Exception as e:
        print(f"Error reading Markdown file {path_to_markdown}: {e}")
        return "Error"

    prompt = f"""{retry} The attached markdown file contains all the information that was given to Swiss citizens to vote on this topic. Score the complexity by easy, normal, or difficult. Consider that this score needs to apply for an average citizen. Only output the label of the score, no reasoning at all.

    ```markdown
    {markdown_content}
    ```"""

    evaluate_context_window(prompt, model, MODELS)

    try:
        complexity_chat = client.chat.create(
            model="grok-4",
            messages=[
                system(
                    "You are a highly intelligent AI assistant helping Swiss citizens to freely form an opinion on their own by adding context to their questions and task."),
                user(prompt)
            ]
        )
        response = complexity_chat.sample()

        if not response.content or not response.content.strip():
            print(f"Fehler: Leere Antwort für Markdown-Datei '{path_to_markdown}'")
            return "Error"

        content_list = response.content.split()
        if not content_list:
            print(f"Fehler: Keine gültigen Token in der Antwort für Markdown-Datei '{path_to_markdown}'")
            return "Error"
        if content_list[0]=="error":
            # wahrscheinlich wirft API einen Fehler aus, weil gewisse Markdown Files zu viel Text enthalten
            print(response.content)

        return content_list[0]
    except IndexError:
        print(f"IndexError: Keine gültigen Daten in der Antwort für Markdown-Datei '{path_to_markdown}'")
        return "Error"
    except Exception as e:
        print(f"Fehler bei der Verarbeitung von Markdown-Datei '{path_to_markdown}': {e}")
        return "Error"

def related_news_articles(client, vote_tile, retry=""):
    client = Client(api_key=os.getenv("XAI_API_KEY"))

    chat = client.chat.create(
        model="grok-4",
        search_parameters=SearchParameters(mode="auto"),
    )

    chat.append(user("Provide me a digest of world news of the week before July 9, 2025."))

    response = chat.sample()
    print(response.content)

def evaluate_context_window(prompt, model, models):
    # check inputs
    if model not in models:
        return f"WARNING: Undefined model '{model}'"

    # Create a warning if context window too high
    encoding = tiktoken.get_encoding("cl100k_base")

    # Tokens zählen
    tokens = len(encoding.encode(prompt))

    # Check gegen Limit
    limit = models[model]['context_window']
    result = tokens / limit
    if tokens > limit:
        print(f"ERROR: Context Window überschritten in {inspect.currentframe().f_code.co_name}. ({result/100}%)")
    elif tokens > limit * 0.8:  # 80% Puffer für Response
        print(f"WARNING: Context Window nahe am Limit (80%) in {inspect.currentframe().f_code.co_name}. ({result/100}%)")
    else:
        print(f"OK, proceed with prompting LLM. ({result/100}%)")


# --- Pydantic Schemas ---
class Article(BaseModel):
    title: str = Field(description="Title of the article")
    summary: str = Field(description="Brief summary of the article")
    publisher: str = Field(description="Publisher of the article")
    url: str = Field(description="URL of the article")
    label: str = Field(description="Label the political leaning of the article")

class News(BaseModel):
    title: Optional[str] = Field(default=None, description="Title of the article")
    vote_id: Optional[int] = Field(default=None, description="Vote ID of the article")
    article_list: List[Article] = Field(description="List of articles")

# --- Funktion zum Abruf ---
def search_news_articles(vote_title: str, vote_date: str, vote_id: int) -> dict[str, Any]:
    # Prompt
    user_message = (
        "You are a highly intelligent AI assistant helping Swiss citizens "
        "to freely form an opinion on their own by adding context to their questions and tasks."
    )
    system_message = (
        f"Suche Zeitungsartikel, die die Abstimmung zur {vote_title} diskutieren, "
        f"welche vor dem {vote_date} publiziert wurden. "
        "Achte darauf, dass du Schweizer Zeitungen mit verschiedenen politischen Ausrichtungen "
        "berücksichtigst, wie beispielsweise die WOZ (links/ökologisch), Tagesanzeiger (zentristisch-links), "
        "NZZ (konservativ), und Weltwoche (rechts)."
    )

    # Umgebungsvariablen laden
    load_dotenv()
    model_config = json.loads(os.environ['MODEL_CONFIG'])

    # OpenAI Client initialisieren
    openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]

    # Natives xAI Client initialisieren
    xai_client = Client(api_key=os.getenv("XAI_API_KEY"))

    # Parse vote_date to datetime
    vote_date_dt = datetime.strptime(vote_date, "%Y-%m-%d")

    # Search parameters für Live Search
    search_params = SearchParameters(
        mode="on",  # Force live search
        return_citations=True,  # Für URLs und Quellen
        # from_date=datetime(2022, 1, 1), # TODO is this necessary? 6-12 months prior
        to_date=vote_date_dt,  # Articles before vote_date
        max_search_results=20,
        sources=[web_source(country="CH")]
    )

    result = {}

    for provider in model_config:
        for model in provider["models"]:
            if provider["provider"] == 'OpenAI':
                #  GPT Request mit Web Search
                try:
                    openai_response = openai_client.responses.parse(
                        model=model,
                        tools=[{"type": "web_search"}],  # Web Search aktivieren
                        input=messages,
                        text_format=News,  # Pydantic Schema
                    )
                    if model == "gpt-5-nano": # tpm limit of 200 000, one markdown request has ca 80% of that
                        # warte einige Sekunden um bei gpt-5 nano eine rate limit zu erreichen
                        time.sleep(60)

                    news_obj_openai: News = openai_response.output_parsed
                    news_obj_openai.title = vote_title
                    news_obj_openai.vote_id = vote_id

                    result[model] = news_obj_openai.model_dump()

                except Exception as e:
                    print(f"Fehler beim OpenAI API-Aufruf {sys._getframe().f_code.co_name}: {e}")
                    # news_obj_openai = News(title=vote_title, vote_id=vote_id, article_list=[])
            elif provider["provider"] == 'xAI':
                try:
                    # xAI Request mit SearchParameters und response_model für Parsing
                    xai_chat = xai_client.chat.create(
                        model=model,
                        messages=[system(system_message)],
                        search_parameters=search_params
                    )
                    xai_chat.append(user(user_message))

                    # The parse method returns pydantic object
                    xai_response, xai_news = xai_chat.parse(News)
                    assert isinstance(xai_news, News)

                    # Add variables
                    xai_news.title = vote_title
                    xai_news.vote_id = vote_id

                    result[model] = xai_news.model_dump()

                except Exception as e:
                    print(f"Fehler beim xAI API-Aufruf {sys._getframe().f_code.co_name}: {e}")
                    # news_obj_xai = News(title=vote_title, vote_id=vote_id, article_list=[])

    # FIXME Usage:
    # news = search_news_articles("Umweltverantwortungsinitiative", "2025-02-09", 6770)
    # print(news)
    return result


# Pydantic Schemas for Argumentation Analysis
class ChapterType(str, Enum):
    NEUTRAL = "NEUTRAL"
    PRO = "PRO"
    CONTRA = "CONTRA"


class Score(IntEnum):
    Nothing = 0
    Low = 1
    Medium = 2
    High = 3


class Toulmin(IntEnum):
    Claim = 1
    Data = 2
    Warrant = 3
    Backing = 4
    Qualifier = 5
    Rebuttal = 6
    # Qualitätsbewertung: Prüfen Sie auf Stärke (stark vs. schwach):
    # Starke Argumente haben verifizierbare Daten und klare Verbindungen;
    # schwache sind vage oder emotional.


class Aristoteles(IntEnum):
    Logos = 1
    Pathos = 2
    Ethos = 3
    # Es wäre eine Überlegung wert, hier gleich eine ganze Klasse daraus zu machen, dann kann man gleich noch
    # Qualitätsbewertung durchführen:
    # Hohe Qualität zeigt Balance zwischen Logos und Pathos; niedrige, wenn Pathos dominiert und Fakten fehlen.


class Fallacies(IntEnum):
    Adhominem = 1
    AppealToFear = 2
    HastyGeneralization = 3
    FalseDichotomy = 4
    Evidence = 5


class Sentence(BaseModel):
    _id_counter: int = 0  # Klassenvariablen-Zähler

    sentence: str = Field(description="The text content of the sentence.")
    id: int = Field(default_factory=lambda: Sentence._increment_id(), description="Unique identifier for the sentence.")
    argument_type: Toulmin = Field(description="The type of argument")
    parent_id: Optional[int] = Field(default=None,
                                     description="The ID of the parent sentence this sentence references in the context of the argument, when the Toulmin model is applied")  # Wenn ein Satz beispielsweise ein Rebuttal (Gegeneinwand) darstellt, dann gibt es möglcherweise 2 parents
    # TODO oder auch nicht? Drüber nachdenken und besprechen
    polarization_score: Score = Field(description="The amount of Polarization found in the given sentence")
    populism_score: Score = Field(description="The amount of Populism found in the given sentence")
    fallacy_list: List[Fallacies] = Field("Wähle von allen passenden aus")  # Choices!

    @classmethod
    def _increment_id(cls) -> int:
        cls._id_counter += 1  # Zähler erhöhen
        return cls._id_counter

    @computed_field(description="MD5 hash of the sentence text.")
    @property
    def text_hash(self) -> str:
        return hashlib.md5(self.text.encode('utf-8')).hexdigest()


class Argument(BaseModel):
    argument_title: str = Field(description="Title of the argument")
    sentence_list: List[Sentence] = Field(description="List of all sentences belonging to the argument")
    polarization_score: Score = Field(description="The amount of Polarization found in the given argumentation")
    populism_score: Score = Field(description="The amount of Populism found in the given argumentation")


class Chapter(BaseModel):
    chapter_type: ChapterType = Field(description="Type of the chapter")
    argument_list: List[Argument] = Field(description="List of pro and contra arguments")
    populism_detection: bool = Field(
        description="Boolean detection flag. Addresses to overall context of the argument_list, whether it contains Populism")
    polarization_detection: bool = Field(
        description="Boolean detection flag. Addresses to overall context of the argument_list, whether it contains Polarization")


class Vote(BaseModel):
    vote_title: str = Field(description="Title of the vote")
    erlaeuterungen: List[Chapter] = Field(description="List of Chapters")


def classify_arguments_by_markdown(markdown_path):
    # Lade Markdown file
    # markdown_path = "../markdown_output/erlaeuterungen_6770_de.md"  # Ersetze durch deinen Pfad
    with open(markdown_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    # Bereite LLM API vor
    load_dotenv()
    client = Client(api_key=os.getenv("XAI_API_KEY"))
    chat = client.chat.create(model="grok-4")

    chat.append(system(
        "Given a markdown file containing facts and pro and contra argumentation about an popular vote, carefully analyze the text and extract the data into JSON format."))
    chat.append(user(markdown_text))

    # The parse method returns a tuple of the full response object as well as the parsed pydantic object.
    response, vote = chat.parse(Vote)
    assert isinstance(vote, Vote)

    print(vote.vote_title)
    print(response.content)

    return response.content

def write_summary_by_markdown(markdown_path):
    return "Lorem ipsum"

# print(search_news_articles("Umweltverantwortungsinitiative", "2025-02-09", 6770))