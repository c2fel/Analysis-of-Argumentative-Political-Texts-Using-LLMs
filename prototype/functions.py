import random
import requests
from datetime import datetime, date

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
            # Anzahl Vorlagen = 0 und trotzdem fand eine Abstimmung statt, bedeutet, dass es eine Parlamentswahl war.
            if votegroup_per_vote_date != 0:
                for votegroup in vote_date["vorlagenGruppen"]:
                    total_count = total_count + len(votegroup["vorlagen"])

                # Datestring  in ein datetime-Objekt umwandeln
                vote_datetime = datetime.strptime(vote_date["abstimmtag"], "%Y%m%d")
                # Abstimmungen vor 1.1.19 enthalten nur PDF Doks mit Texten
                cutoff = datetime(2019, 1, 1)

                # Unterteilung in aktuelle und vergangene Abstimmungen
                today = date.today()

                if vote_datetime > cutoff:
                    for votegroup in vote_date["vorlagenGruppen"]:
                        active_count = active_count + len(votegroup["vorlagen"])
                # elif vote_datetime >= today:
                    # TODO Dieser Abschnitt wird relevant sobald die nächsten Abstimmungen aufgeschaltet werden

        return active_count, total_count

def load_votes(lang):
    r = requests.get(
        "https://app-prod-ws.voteinfo-app.ch/v1/archive/vorlagen?searchTerm=&geoLevelNummer=0&geoLevelLevel=0",
        headers={"User-Agent": "Mozilla/5.0"})
    votes_json = r.json()

    if lang != "de" and lang != "fr" and lang != "it" and lang != "rm":
        print("Selected language is not available")
        return -1
    else:
        votes = []
        for vote_date in votes_json["regionen"][0]["abstimmtage"]:
            votegroup_per_vote_date = len(vote_date["vorlagenGruppen"])
            # Anzahl Vorlagen = 0 und trotzdem fand eine Abstimmung statt, bedeutet, dass es eine Parlamentswahl war.
            if votegroup_per_vote_date != 0:
                # Datestring  in ein datetime-Objekt umwandeln
                vote_datetime = datetime.strptime(vote_date["abstimmtag"], "%Y%m%d")
                # Abstimmungen vor 1.1.19 enthalten nur PDF Doks mit Texten
                cutoff = datetime(2019, 1, 1)

                # Unterteilung in aktuelle und vergangene Abstimmungen
                today = date.today()

                if vote_datetime < cutoff:
                    continue
                # elif dt >= today:
                # TODO Dieser Abschnitt wird relevant sobald die nächsten Abstimmungen aufgeschaltet werden
                else:
                    #print()
                    #print(vote_datetime.strftime("%d.%m.%Y"), " - ", votegroup_per_vote_date)

                    voting_date = {'voting_date': vote_datetime.strftime("%d.%m.%Y"), 'votes': []}

                    for votegroup in vote_date["vorlagenGruppen"]:
                        votes_per_votegroup = len(votegroup["vorlagen"])
                        if votes_per_votegroup == 1:  # Schliesst Abstimmungen mit gegensätzlich Vorlagen aus: 19821128 und 20020922
                            lang_title = next(
                                (t["text"] for t in votegroup["vorlagen"][0]["vorlagenTitel"] if t["langKey"] == lang),
                                None)
                            #print(votegroup["vorlagen"][0]["vorlagenId"], " - ", lang_title)

                            vote = {'voteId': votegroup["vorlagen"][0]["vorlagenId"], 'voteTitle': lang_title, 'voteTopic': classify_topic(lang_title)}
                            voting_date['votes'].append(vote)

                    votes.append(voting_date)
        return votes

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
    topics = ["Foreign Affairs", "Home Affairs", "Justice and Police", "Defence, Civil Protection and Sport", "Finance", "Economic Affairs, Education and Research", "Environment, Transport, Energy and Communications"]
    return topics[random.randint(1, len(topics))-1]