import random
import time
import json
import os
import sys
import requests
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from xai_sdk import Client
from transformers.models.xlm.tokenization_xlm import lowercase_and_remove_accent
import logging
import tiktoken

from prototype.agents.llm_functions import classify_topic_by_title, score_complexity_by_markdown

# Konfiguriere Logging
logging.basicConfig(
    filename="initialize_data.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def initialize_data(TESTMODE=None):
    # During development: Purge any content from votes.json at the start
    file_path = "static/votes.json"
    #try:
    #    with open(file_path, 'w') as file:
    #        print(f"File '{file_path}' has been emptied")
    #        pass
    #except FileNotFoundError:
    #    print(f"File '{file_path}' has been created")

    # Greife auf des existierende JSON file zurück
    # Prüfe, ob die Datei existiert

    # TODO diese file macht im Moment gar nichts
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            # Öffne und lade die Datei
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            return 1

        except json.JSONDecodeError as e:
            return False, f"Ungültiges JSON in '{file_path}': {str(e)}"
        except PermissionError:
            return False, f"Keine Leseberechtigung für '{file_path}'."
        except Exception as e:
            return False, f"Fehler beim Lesen von '{file_path}': {str(e)}"



    # Fetch all voting dates and the respective votes
    voting_data = parse_votes()

    # FIXME: Only for small test:
    # Annahme: Struktur wie data["regionen"][0]["abstimmtage"]
    if TESTMODE:
        regionen = voting_data.get("regionen", [])
        if regionen and "abstimmtage" in regionen[0]:
            abstimmtage = regionen[0]["abstimmtage"]
            gekuerzt = abstimmtage[:2]  # nur die ersten zwei
        else:
            gekuerzt = []

        # neues Dict mit derselben Struktur, aber gekürzt
        voting_data = {
            "regionen": [
                {
                    "abstimmtage": gekuerzt
                }
            ]
        }

    # Funktion zum Verarbeiten einer einzelnen Abstimmung
    def process_vote(vote_id, vote, vote_date, vote_index):
        try:
            # Initialisiere den Client für diesen Thread
            load_dotenv()
            client = Client(
                api_key=os.getenv("XAI_API_KEY"),
                timeout=3600,
            )

            # Fetch vote details
            vote_details = parse_vote(vote['voteId'])

            if not isinstance(vote_details, dict):
                print(f"Fehler: Ungültige Daten für voteId {vote['voteId']}")
                logging.error(f"Ungültige Daten für voteId {vote['voteId']}: {vote_details}")
                return {
                    "vote_date": vote_date,
                    "vote_index": vote_index,
                    "vote_data": {"voteId": vote['voteId'], "status": 0, "error": str(vote_details)}
                }

            # Update vote with details
            vote.update(vote_details)

            if vote_details['status'] > 0:
                # Generate markdown files
                markdown_files = generate_markdowns(vote['voteId'], vote_details)
                vote['markdown_files'] = markdown_files

                # Classify vote type
                vote['voteType'] = classify_vote_by_vorlagenArtId(vote['vorlagenArtId'])
                # TODO assess this output and try _by_title_with_llm with some retries.

                # LLM-based classification
                vote['voteTopic'] = classify_topic_by_title(client, vote['voteTitle']['de'])

                if vote_details['status'] > 1:
                    # LLM-based complexity score
                    vote['voteComplexity'] = score_complexity_by_markdown(client, vote['markdown_files']['de'])
                    # Assess if llm output label is in pre-defined range of label:
                    range_complexity_score = ["easy", "normal", "difficult"]
                    if vote['voteComplexity'] not in range_complexity_score:
                        # retry the same prompt
                        vote['voteComplexity'] = score_complexity_by_markdown(client, vote['markdown_files']['de'], f"The last output from the same prompt was not as expected. Your last output: {vote['voteComplexity']}. Expected output should be one of these labels: {print(repr(range_complexity_score))}. Thus, eveluate again:")

                else:
                    vote['voteComplexity'] = 0

                print(f"LLM labeling completed for voteId {vote['voteId']}")

            return {
                "vote_date": vote_date,
                "vote_index": vote_index,
                "vote_data": vote
            }

        except Exception as e:
            print(f"Fehler bei der Verarbeitung von voteId {vote['voteId']}: {e}")
            logging.error(f"Fehler bei voteId {vote['voteId']}: {e}")
            return {
                "vote_date": vote_date,
                "vote_index": vote_index,
                "vote_data": {"voteId": vote['voteId'], "status": 0, "error": str(e)}
            }

    # Parallelisiere die Verarbeitung der Abstimmungen
    results = []
    with ThreadPoolExecutor(max_workers=50) as executor: # funktioniert mit 30
        future_to_vote = []
        for vote_date, votes in voting_data.items():
            for vote_index, vote in enumerate(votes):  # Verwende enumerate für den Index
                future = executor.submit(process_vote, vote['voteId'], vote, vote_date, vote_index)
                future_to_vote.append((future, vote_date, vote_index))

        for future, vote_date, vote_index in future_to_vote:
            try:
                result = future.result()
                results.append(result)
                voting_data[vote_date][vote_index] = result['vote_data']
                print(f"Abstimmung {result['vote_data']['voteId']} verarbeitet")
            except Exception as e:
                print(f"Fehler bei der parallelen Verarbeitung für voteId {vote_date}/{vote_index}: {e}")
                logging.error(f"Paralleler Fehler für voteId {vote_date}/{vote_index}: {e}")
                voting_data[vote_date][vote_index] = {
                    "voteId": voting_data[vote_date][vote_index]['voteId'],
                    "status": 0,
                    "error": str(e)
                }

    # Speichere die aktualisierten Daten
    with open("static/votes.json", "w", encoding="utf-8") as f:
        json.dump(voting_data, f, indent=2, ensure_ascii=False)

    return 1


# Rest der Datei bleibt unverändert
def parse_votes():
    # url = "https://app-prod-ws.voteinfo-app.ch/v1/archive/vorlagen?searchTerm=&geoLevelNummer=0&geoLevelLevel=0"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print("Error:", e)
        return 0

    try:
        data = resp.json()
    except (requests.exceptions.JSONDecodeError, json.JSONDecodeError, ValueError) as e:
        print(f"Invalid JSON: {type(e).__name__} - {str(e)}")
        return 0

    result = {}
    abstimmtage = data['regionen'][0]['abstimmtage']

    for tag in abstimmtage:
        date = tag['abstimmtag']
        if not date or len(date) != 8:
            continue
        iso_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        votes = []

        for gruppe in tag.get('vorlagenGruppen', []):
            for vorlage in gruppe.get('vorlagen', []):
                vote_id = vorlage['vorlagenId']
                title = {}

                for titel in vorlage.get('vorlagenTitel', []):
                    lang = titel['langKey']
                    text = titel['text']
                    title[lang] = text

                votes.append({
                    "voteId": vote_id,
                    "voteTitle": title
                })

        if votes:
            result[iso_date] = votes

    return result


def parse_vote(voteId):
    try:
        voteId = int(voteId)
        if voteId != float(voteId):
            raise ValueError("voteId must be an integer")
        if voteId <= 0:
            raise ValueError("voteId must be a positive integer")
    except (ValueError, TypeError):
        raise ValueError("voteId must be a valid positive integer")

    url = f"https://app-static.voteinfo-app.ch/v5/{voteId}/erlaeuterung.json"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            try:
                data = resp.json()
            except (requests.exceptions.JSONDecodeError, json.JSONDecodeError, ValueError) as e:
                print(f"Invalid JSON for {voteId}: {type(e).__name__} - {str(e)}")
                return {'vorlagenId': voteId, 'status': 0, 'error': str(e), 'data': resp.text}
        else:
            print(f"Error: for {voteId} received status code {resp.status_code}")
            return {'vorlagenId': voteId, 'status': 0, 'error': resp.status_code}
    except Exception as e:
        print(f"Request failed for {voteId}: {type(e).__name__} - {str(e)}")
        return {'vorlagenId': voteId, 'status': 0, 'error': str(e)}

    if "abstimmtag" in data:
        del data["abstimmtag"]
    if "publikation" in data:
        del data["publikation"]
    if "timestamp" in data:
        del data["timestamp"]
    if "geoLevelLevel" in data:
        del data["geoLevelLevel"]
    if "geoLevelnummer" in data:
        del data["geoLevelnummer"]
    if "geoLevelname" in data:
        del data["geoLevelname"]
    if "hauptvorlagenId" in data:
        del data["hauptvorlagenId"]

    if len(data["erlaeuterungen"][0]["erlaeuterung"]["kapitel"]) == 1:
        data["status"] = 1
    else:
        data["status"] = 2

    return data


def generate_markdowns(voteId, data):
    result = {}
    output_dir = "markdown_output"
    os.makedirs(output_dir, exist_ok=True)

    base_url = "https://app-static.voteinfo-app.ch/v5/"

    for entry in data.get("erlaeuterungen", []):
        lang_key = entry.get("langKey")
        content_dict = entry.get("erlaeuterung", {})

        if lang_key and content_dict:
            markdown_content = f"# {content_dict.get('vorlagenTitel', 'Explanation')}\n\n"

            for chapter in content_dict.get("kapitel", []):
                markdown_content += f"## {chapter.get('text', '')}\n\n"

                for component in chapter.get("komponenten", []):
                    comp_type = component.get("typ")

                    if comp_type == "title":
                        title_info = component.get("title", {})
                        title_text = title_info.get("text", "")
                        if title_info.get("isSubtitle", False):
                            markdown_content += f"### {title_text}\n\n"
                        else:
                            markdown_content += f"## {title_text}\n\n"

                    elif comp_type == "text":
                        text_info = component.get("text", {})
                        markdown_content += text_info.get("text", "") + "\n\n"

                    elif comp_type == "link":
                        link_info = component.get("link", {})
                        name = link_info.get("name", "")
                        url = link_info.get("url", "")
                        markdown_content += f"[{name}]({url})\n\n"

                    elif comp_type == "youtube":
                        yt_info = component.get("youtube", {})
                        yt_id = yt_info.get("youtubeId")
                        if yt_id:
                            markdown_content += f"[YouTube Video](https://www.youtube.com/watch?v={yt_id})\n\n"
                        gehoerlos_id = yt_info.get("youtubeIdGehoerlos")
                        if gehoerlos_id:
                            markdown_content += f"[YouTube Video for Hearing Impaired](https://www.youtube.com/watch?v={gehoerlos_id})\n\n"

                    elif comp_type == "image":
                        img_info = component.get("image", {})
                        img_url = img_info.get("url", "")
                        if img_url:
                            img_url = f"{base_url}{voteId}/{img_url}"
                        alt_text = img_info.get("altText", "")
                        markdown_content += f"![{alt_text}]({img_url})\n\n"

                    elif comp_type == "pdf":
                        pdf_info = component.get("pdf", {})
                        name = pdf_info.get("name", "")
                        url = pdf_info.get("url", "")
                        if url:
                            url = f"{base_url}{voteId}/{url}"
                        markdown_content += f"[{name} (PDF)]({url})\n\n"

                    elif comp_type == "vote":
                        vote_info = component.get("vote", {})
                        titel = vote_info.get("titel", "")
                        markdown_content += f"### {titel}\n\n"
                        for bar in vote_info.get("balken", []):
                            label = bar.get("label", "")
                            value = bar.get("value", "")
                            markdown_content += f"- {label}: {value}\n"
                        markdown_content += "\n"

            filename = f"{output_dir}/erlaeuterungen_{voteId}_{lang_key}.md"
            result[lang_key] = filename

            with open(filename, "w", encoding="utf-8") as f:
                f.write(markdown_content)

    print(f"Markdown file generation complete. {len(result)}")
    return result


def count_votes():
    try:
        r = requests.get(
            "https://app-prod-ws.voteinfo-app.ch/v1/archive/vorlagen?searchTerm=&geoLevelNummer=0&geoLevelLevel=0",
            headers={"User-Agent": "Mozilla/5.0"})
        votes_json = r.json()
    except Exception as e:
        print("Error:", e)
        return "Error:", e

    if r.status_code == 200:
        total_count = 0
        active_count = 0
        for vote_date in votes_json["regionen"][0]["abstimmtage"]:
            votegroup_per_vote_date = len(vote_date["vorlagenGruppen"])
            if votegroup_per_vote_date != 0:
                for votegroup in vote_date["vorlagenGruppen"]:
                    total_count = total_count + len(votegroup["vorlagen"])

                vote_datetime = datetime.strptime(vote_date["abstimmtag"], "%Y%m%d")
                cutoff = datetime(2019, 1, 1)

                today = date.today()

                if vote_datetime > cutoff:
                    for votegroup in vote_date["vorlagenGruppen"]:
                        active_count = active_count + len(votegroup["vorlagen"])

        return active_count, total_count


def load_votes(lang):
    path_votes_json = 'static/votes.json'
    try:
        with open(path_votes_json, 'r', encoding='utf-8') as file:
            votes_json = json.load(file)
    except FileNotFoundError:
        print(f"Fehler: Die Datei {path_votes_json} wurde nicht gefunden.")
    except json.JSONDecodeError:
        print(f"Fehler: Die Datei {path_votes_json} enthält ungültiges JSON-Format.")
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

    if lang != "de" and lang != "fr" and lang != "it" and lang != "rm":
        print("Selected language is not available")
        return -1
    else:
        return votes_json


def load_vote(voteId, language):
    url = f"https://app-static.voteinfo-app.ch/v5/{voteId}/erlaeuterung.json"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print("Error:", e)
        return "Error:", e

    vote_json = r.json()
    return vote_json


def classify_topic(title):
    topics = ["Foreign Affairs", "Home Affairs", "Justice and Police", "Defence, Civil Protection and Sport", "Finance",
              "Economic Affairs, Education and Research", "Environment, Transport, Energy and Communications"]
    return topics[random.randint(0, len(topics)) - 1]


def classify_vote_by_vorlagenArtId(vorlagenArtId):
    if vorlagenArtId in [1, 3, 10102]:
        return "Initiative"
    elif vorlagenArtId in [2, 10106, 10107]:
        return "Referendum"
    else:
        return "Other"


def classify_vote(voteId):
    if not isinstance(voteId, int):
        raise TypeError("voteId must be an integer")

    try:
        file_path = 'static/votes.json'
        with open(file_path, 'r') as file:
            data = json.load(file)

        key_to_check = "6710"
        if voteId in data:
            return data[key_to_check]['voteCategory']
        else:
            print(f"Key '{voteId}' does not exist in '{file_path}', trying to fetch from API.")

    except FileNotFoundError:
        print("Die Datei wurde nicht gefunden.")
    except json.JSONDecodeError:
        print("Die Datei enthält kein valides JSON.")
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {str(e)}")

    url = f"https://app-static.voteinfo-app.ch/v5/{voteId}/erlaeuterung.json"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print("Error:", e)
        return "Error:", e

    try:
        vote_json = r.json()
    except requests.exceptions.JSONDecodeError:
        print(f"Invalid JSON for voteId {voteId}: {r.text}")
        return 'Missing data'

    vorlagenArtId = vote_json["vorlagenArtId"]

    if vorlagenArtId in [1, 3, 10102]:
        return "Initiative"
    elif vorlagenArtId in [2, 10106, 10107]:
        return "Referendum"
    else:
        return "Other"

def build_vote_url(vote_id: int, file_name: str = "erlaeuterung.json", dotenv_path="agents/.env") -> str:
    # TODO this code needs to be implemented in functions.py
    load_dotenv(dotenv_path=dotenv_path)
    template = os.getenv("BK_API_ERLAEUTERUNGEN")
    url = template.format(vote_id=vote_id, file_name=file_name)
    return url

def build_votes_url(dotenv_path="agents/.env") -> str:
    # TODO this code needs to be implemented in functions.py
    load_dotenv(dotenv_path=dotenv_path)
    template = os.getenv("BK_API_VORLAGE")
    return template

def evaluate_context_window(prompt: str, encoding_type: str = "cl100k_base", limit: int = 131072):
    # Encoder für Grok-Modelle (cl100k_base)
    encoding = tiktoken.get_encoding(encoding_type)

    # Tokens zählen
    tokens = len(encoding.encode(prompt))
    print(f"Anzahl Tokens im Prompt: {tokens}")

    # Check gegen Limit
    if tokens > limit:
        return "⚠️ Überschreitet das Limit! Kürze den Prompt."
    elif tokens > limit * 0.8:  # 80% Puffer für Response
        return "️⚠️ Nah am Limit – prüfe mit Response-Schätzung."
    else:
        return "✅ Sicher unter dem Limit."