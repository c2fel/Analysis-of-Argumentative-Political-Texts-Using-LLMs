""" This module provides all necessary functions
    to load data from local sources
    to request data from external sources
    and to process them """

import json
import os
from itertools import islice
import hashlib

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
import requests
from dotenv import load_dotenv
from xai_sdk import Client
import tiktoken

from prototype.agents.llm_functions import classify_topic_by_title, score_complexity_by_markdown, \
    search_news_articles, classify_arguments_by_markdown


def initialize_data(TESTMODE=None):
    """ This method tries to load data from local JSON file
        and if not possible, requests data directly from the Bundeskanzlei API """
    # During development: Purge any content from votes.json at the start
    file_path = "static/votes.json"
    if TESTMODE:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print("File deleted successfully")
        except FileNotFoundError:
            print(f"File '{file_path}' does not exist")

    # Greife auf des existierende JSON file zurück
    # Prüfe, ob die Datei existiert

    # TODO diese file macht im Moment gar nichts
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            # Öffne und lade die Datei
            with open(file_path, 'r', encoding='utf-8') as file:
                voting_data = json.load(file)
                # if voting_data has been successfully parsed,
                # we return 1 as all necessary data exists for UI
            return True, "OK"

        except json.JSONDecodeError as e:
            return False, f"Ungültiges JSON in '{file_path}': {str(e)}"
        except PermissionError:
            return False, f"Keine Leseberechtigung für '{file_path}'."
        except Exception as e:
            return False, f"Fehler beim Lesen von '{file_path}': {str(e)}"


    # else, we are going to load the voting data from source again and process it later
    # Fetch all voting dates and the respective votes
    voting_data = parse_votes()

    # FIXME: Only for small test:
    # Limit # of votes to decrease load time, when testing llm labeling

    #print(voting_data)
    if TESTMODE:
        voting_data = dict(islice(voting_data.items(), 1))

    # print(type(voting_data))

    # Funktion zum Verarbeiten einer einzelnen Abstimmung
    def process_vote(vote, vote_date, vote_index):
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
                return {
                    "vote_date": vote_date,
                    "vote_index": vote_index,
                    "vote_data": {"voteId": vote['voteId'], "status": 0, "error": str(vote_details)}
                }

            # Update vote with details
            vote.update(vote_details)

            # vote_details['status'] beschreibt, die Verfügbarkeit von Erläuterungen:
            # 0 = keine
            # 1 = sehr beschränkt
            # 2 = detailliert
            if vote_details['status'] > 0:
                # Rebuild all "typ": "text" in the chapters, only for language "de" at the moment
                for erlaeuterung in vote_details['erlaeuterungen']:
                    if erlaeuterung['langKey'] == "de":
                        i = 1
                        for chapter in erlaeuterung['erlaeuterung']['kapitel']:
                            # print(chapter)
                            for komponente in chapter['komponenten']:
                                # print(komponente)
                                if komponente['typ'] == "text":
                                    # print(chapter['komponenten']['typ'])
                                    komponente['sentence_list'] = []
                                    sentences = komponente['text']['text'].split(". ")
                                    for sentence in sentences:
                                        hash_result = hashlib.md5(sentence.encode())
                                        komponente['sentence_list'].append(
                                            {
                                                "id": i,
                                                "hash": hash_result.hexdigest(),
                                                "text": sentence
                                            }
                                        )
                                        i += 1
                            # del chapter['text'] # FIXME to save space, we could delete this key
                print("JSON processed.")

                # Generate markdown files
                markdown_files = generate_markdowns(vote['voteId'], vote_details)
                vote['markdown_files'] = markdown_files

                # Classify vote type
                vote['voteType'] = classify_vote_by_vorlagenArtId(vote['vorlagenArtId'])
                # TODO assess this output and try _by_title_with_llm with some retries.

                # LLM-based classification
                vote['voteTopic'] = classify_topic_by_title(client, vote['voteTitle']['de'])
                vote['voteNewsArticles'] = search_news_articles(
                    vote['voteTitle']['de'],
                    vote_date, vote['voteId']
                )

                if vote_details['status'] > 1:
                    # LLM-based complexity score
                    vote['voteComplexity'] = score_complexity_by_markdown(
                        client,
                        vote['markdown_files']['de']
                    )
                    # Assess if llm output label is in pre-defined range of label:
                    range_complexity_score = ["easy", "normal", "difficult"]
                    if vote['voteComplexity'] not in range_complexity_score:
                        # retry the same prompt
                        vote['voteComplexity'] = score_complexity_by_markdown(
                            client,
                            vote['markdown_files']['de'],
                            f"The last output from the same prompt was not as expected. "
                            f"Your last output: {vote['voteComplexity']}. "
                            f"Expected output should be one of these labels: {range_complexity_score}. "
                            f"Thus, evaluate again:")

                    # LLM-based
                    vote['argumentationAssessment'] = classify_arguments_by_markdown(vote['markdown_files']['de'])

                    # Add LLM-based summary as introduction
                    # vote['voteSummary'] = write_summary_by_markdown(vote['markdown_files']['de'])
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
            return {
                "vote_date": vote_date,
                "vote_index": vote_index,
                "vote_data": {"voteId": vote['voteId'], "status": 0, "error": str(e)}
            }

    # Parallelisiere die Verarbeitung der Abstimmungen
    results = []
    if TESTMODE:
        number_of_workers = 4
    else:
        number_of_workers = 50 # works with 30

    with ThreadPoolExecutor(max_workers=number_of_workers) as executor: # funktioniert mit 30
        future_to_vote = []
        for vote_date, votes in voting_data.items():
            for vote_index, vote in enumerate(votes):  # Verwende enumerate für den Index
                future = executor.submit(process_vote, vote, vote_date, vote_index)
                future_to_vote.append((future, vote_date, vote_index))

        for future, vote_date, vote_index in future_to_vote:
            try:
                result = future.result()
                results.append(result)
                voting_data[vote_date][vote_index] = result['vote_data']
                print(f"Abstimmung {result['vote_data']['voteId']} verarbeitet")
            except Exception as e:
                print(f"Fehler bei der parallelen Verarbeitung für voteId {vote_date}/{vote_index}: {e}")
                voting_data[vote_date][vote_index] = {
                    "voteId": voting_data[vote_date][vote_index]['voteId'],
                    "status": 0,
                    "error": str(e)
                }

    # Speichere die aktualisierten Daten
    with open("static/votes.json", "w", encoding="utf-8") as f:
        json.dump(voting_data, f, indent=2, ensure_ascii=False)

    return True, "OK"


# Rest der Datei bleibt unverändert
def parse_votes():
    # url = "https://app-prod-ws.voteinfo-app.ch/v1/archive/vorlagen?searchTerm=&geoLevelNummer=0&geoLevelLevel=0"
    try:
        resp = requests.get(build_votes_url(), timeout=10, headers={"User-Agent": "Mozilla/5.0"})
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

    # base_url = "https://app-static.voteinfo-app.ch/v5/" # delete later

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
                            img_url = build_vote_url(voteId, img_url, "agents/.env")
                            # img_url = f"{base_url}{voteId}/{img_url}"
                        alt_text = img_info.get("altText", "")
                        markdown_content += f"![{alt_text}]({img_url})\n\n"

                    elif comp_type == "pdf":
                        pdf_info = component.get("pdf", {})
                        name = pdf_info.get("name", "")
                        url = pdf_info.get("url", "")
                        if url:
                            url = build_vote_url(voteId, url, "agents/.env")
                            # url = f"{base_url}{voteId}/{url}"
                        markdown_content += f"[{name} (PDF)]({url})\n\n"

                    elif comp_type == "vote":
                        vote_info = component.get("vote", {})
                        titel = vote_info.get("titel", "")
                        markdown_content += f"### {titel}\n\n"
                        for result_type in vote_info.get("balken", []):
                            label = result_type.get("label", "")
                            value = result_type.get("value", "")
                            markdown_content += f"- {label}: {value}\n"
                        markdown_content += "\n"

            filename = f"{output_dir}/erlaeuterungen_{voteId}_{lang_key}.md"
            result[lang_key] = filename

            with open(filename, "w", encoding="utf-8") as f:
                f.write(markdown_content)

    print(f"Markdown file generation complete. {len(result)}")
    return result


def count_votes():
    """ This method compares the number of LLM-tracked votes
        against the total number of votes available. """
    # delete later
    # url = "https://app-prod-ws.voteinfo-app.ch/v1/archive/vorlagen?searchTerm=&geoLevelNummer=0&geoLevelLevel=0"
    try:
        r = requests.get(
            build_votes_url(),
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
    """ Depending on availability, this method loads data from popular votes
        which were held in Switzerland """
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

    if lang not in ('de', 'fr', 'it', 'rm'):
        print("Selected language is not available")
        return -1
    else:
        return votes_json


def load_vote(voteId, language):
    """ Depending on availability, this method loads data for a given popular vote """
    # first try to fetch data from local json
    path_votes_json = 'static/votes.json'
    try:
        with open(path_votes_json, 'r', encoding='utf-8') as file:
            votes_json = json.load(file)
            vote_json = next((vote for date in votes_json.values() for vote in date if vote["voteId"] == voteId), None)
            date, vote = next(((date, vote) for date, votes in votes_json.items() for vote in votes if vote["voteId"] == voteId),
                          (None, None))
            #print({date: vote})
            return date, vote

    except FileNotFoundError:
        print(f"Fehler: Die Datei {path_votes_json} wurde nicht gefunden.")
    except json.JSONDecodeError:
        print(f"Fehler: Die Datei {path_votes_json} enthält ungültiges JSON-Format.")
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

    # delete later
    # url = f"https://app-static.voteinfo-app.ch/v5/{voteId}/erlaeuterung.json"
    try:
        r = requests.get(build_vote_url(voteId), headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print("Error:", e)
        return "Error:", e

    vote_json = r.json()
    return vote_json


def classify_vote_by_vorlagenArtId(vorlagenArtId):
    """ Depending on `vorlagenArtId` in the vote dict,
        the string label "Initiative" or "Referendum" is matched """
    if vorlagenArtId in [1, 3, 10102]:
        return "Initiative"
    elif vorlagenArtId in [2, 10106, 10107]:
        return "Referendum"
    else:
        return "Other"

# FIXME: These two method do the same, one should be deleted

def classify_vote(voteId):
    """ Depending on `vorlagenArtId` in the vote dict,
        the string label "Initiative" or "Referendum" is matched """
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

    # delete later
    # url = f"https://app-static.voteinfo-app.ch/v5/{voteId}/erlaeuterung.json"
    try:
        r = requests.get(build_vote_url(voteId), headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print("Error:", e)
        return "Error:", e

    try:
        vote_json = r.json()
    except requests.exceptions.JSONDecodeError:
        print(f"Invalid JSON for voteId {voteId}: {r.text}")
        vote_json["vorlagenArtId"] = None

    finally:
        vorlagen_art_id = vote_json["vorlagenArtId"]
        if vorlagen_art_id in [1, 3, 10102]:
            return "Initiative"
        elif vorlagen_art_id in [2, 10106, 10107]:
            return "Referendum"
        elif vorlagen_art_id:
            return "Undefined"
        else:
            return "Missing data"

def build_vote_url(vote_id: int, file_name: str = "erlaeuterung.json", dotenv_path="agents/.env") -> str:
    """ Returns the url to request the list with popular votes.
        This method is used to keep API endpoints of the Bundeskanzlei the private """
    # TODO this code needs to be implemented in functions.py
    load_dotenv(dotenv_path=dotenv_path)
    template = os.getenv("BK_API_ERLAEUTERUNGEN")
    url = template.format(vote_id=vote_id, file_name=file_name)
    return url

def build_votes_url(dotenv_path="agents/.env") -> str:
    """ Returns the url to request the details for a given vote.
        This method is used to keep API endpoints of the Bundeskanzlei the private """
    # TODO this code needs to be implemented in functions.py
    load_dotenv(dotenv_path=dotenv_path)
    template = os.getenv("BK_API_VORLAGE")
    return template

def evaluate_context_window(prompt: str, encoding_type: str = "cl100k_base", limit: int = 131072):
    """ Evaluates the input size of a prompt """
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
