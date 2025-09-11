import time
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
import requests
import os
from functions import load_votes, load_vote, count_votes, classify_vote, parse_votes, initialize_data
import json
from xai_sdk import Client

app = Flask(__name__)

# This is currently not used, but prepared if eventually a UI based on Next.JS with SSR will be developed
@app.route('/api/get-votes')
def api_get_votes():
    return load_votes('de')


# This is currently not used, but prepared if eventually a UI based on Next.JS with SSR will be developed
@app.route('/api/get-votes/<int:voteId>')
def api_get_vote(voteId):
    language = request.args.get('language', 'de')
    vote = load_vote(voteId, language)

    contents = next((e for e in vote["erlaeuterungen"] if e["langKey"] == language), None)
    # print(contents['erlaeuterung'])

    return contents['erlaeuterung']


@app.route('/')
def home():
    a, b = count_votes()
    return render_template('index.html', tracked_votes=a, total_votes=b)


@app.route('/votes')
def votes():
    language = request.args.get('language', 'de')
    abstimmungstage = load_votes(language)
    # print(abstimmungstage)
    return render_template("votes.html", abstimmungstage=abstimmungstage, language=language)


@app.route('/votes/<int:voteId>')
def vote(voteId):
    language = request.args.get('language', 'de')
    vote = load_vote(voteId, language)

    contents = next((e for e in vote["erlaeuterungen"] if e["langKey"] == language), None)
    # print(contents['erlaeuterung'])

    return render_template('vote.html', vote_date=vote['abstimmtag'], vote_id=voteId,
                           erlaeuterung=contents['erlaeuterung'], vote_type=classify_vote(voteId))


@app.route('/test')
def test():
    return render_template('test_template.html')


@app.route('/vorlage.html')
def vorlage_html():
    return render_template('vorlage_old.html')


@app.route('/api/votes')
def api_votes():
    url = "https://app-prod-ws.voteinfo-app.ch/v1/archive/vorlagen?searchTerm=&geoLevelNummer=0&geoLevelLevel=0"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        vorlagen_liste = []
        for region in data.get("regionen", []):
            for abstimmtage in region.get("abstimmtage", []):
                datum = abstimmtage.get("abstimmtag", None)
                if not datum or len(datum) != 8:
                    continue
                iso_date = f"{datum[:4]}-{datum[4:6]}-{datum[6:]}"
                for gruppe in abstimmtage.get("vorlagenGruppen", []):
                    for vorlage in gruppe.get("vorlagen", []):
                        titel_de = None
                        titel_feld = vorlage.get("vorlagenTitel", [])
                        if isinstance(titel_feld, list):
                            for t in titel_feld:
                                if t.get("langKey") == "de":
                                    titel_de = t.get("text", "")
                                    break
                        if not titel_de:
                            titel_de = "(Kein Titel gefunden)"
                        vorlagen_liste.append({
                            "abstimmungDatum": iso_date,
                            "titel": titel_de,
                            "vorlagenId": vorlage.get("vorlagenId")
                        })
        return jsonify(vorlagen_liste)
    except Exception as e:
        print("FEHLER:", e)
        return jsonify([])


@app.route('/api/erlaeuterung/<int:vorlagen_id>')
def api_erlaeuterung(vorlagen_id):
    url = f"https://app-static.voteinfo-app.ch/v5/{vorlagen_id}/erlaeuterung.json"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        print(f"Proxy call: {url} | Status: {resp.status_code}")
        print("Preview:", resp.text[:200])
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        print("FEHLER:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    s = time.time()
    load_dotenv()
    client = Client(
        api_key=os.getenv("XAI_API_KEY"),
        timeout=3600,  # change for longer timeout when submitting large prompts
    )
    initialize_data()
    print((time.time() - s) / 60, "minutes")
    app.run(debug=True) # for later: debug=False or at least: use_reloader=False (better performance at start up)
