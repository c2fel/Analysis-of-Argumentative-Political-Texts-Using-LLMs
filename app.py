import sys
import time
from flask import Flask, jsonify, render_template, request

from functions import load_votes, load_vote, count_votes, classify_vote, parse_votes, initialize_data

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
    language = request.args.get('language', 'de')
    model = request.args.get('model', 'grok-4')

    a, b = count_votes()

    return render_template('index.html', tracked_votes=a, total_votes=b, language=language, model=model)


@app.route('/votes')
def votes():
    language = request.args.get('language', 'de')
    model = request.args.get('model', 'grok-4')

    abstimmungstage = load_votes(language)

    return render_template("votes.html", abstimmungstage=abstimmungstage, language=language, model=model)


@app.route('/votes/<int:voteId>')
def vote(voteId):
    language = request.args.get('language', 'de')
    model = request.args.get('model', 'grok-4')

    date, vote = load_vote(voteId, language)

    contents = next((e for e in vote["erlaeuterungen"] if e["langKey"] == language), None)

    return render_template('vote.html', vote_date=date, vote_id=voteId,
                           erlaeuterung=contents['erlaeuterung'], vote_type=classify_vote(voteId), model=model, newsArticles=vote['voteNewsArticles'], summary=vote['voteSummary'])


@app.route('/vorlage.html')
def vorlage_html():
    return render_template('vorlage_old.html')


if __name__ == '__main__':
    s = time.time()
    success, return_string = initialize_data(TESTMODE=True) # TESTMODE=True
    if not success:
        print(f"Failed to initialize data: {return_string}")
        sys.exit(0)

    print("Time of Initialization: ", (time.time() - s) / 60, "minutes")
    # app.run(debug=True, use_reloader=False) # for later: debug=False or at least: use_reloader=False (better performance at start up)

    # Docker version
    app.run(host='0.0.0.0', port=5000, debug=False)
