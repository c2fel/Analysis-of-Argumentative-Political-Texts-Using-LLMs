import os
import sys
import time

from xai_sdk import Client
from xai_sdk.search import SearchParameters, web_source
from xai_sdk.chat import system, user

from llm_files.clients import get_openai_client, get_xai_client
from flask import Flask, jsonify, render_template, request

from functions import load_votes, load_vote, count_votes, classify_vote, parse_votes, initialize_data

app = Flask(__name__)

# for llm call at run time
@app.route('/llm-interactions', methods=['POST'])
def llm_actions():
    data = request.get_json(force=True)  # force=True ensures it parses even without correct header

    # Access fields
    highlighted_text = data.get("highlighted_text", None)
    markdown_path = data.get("markdown_path", None)
    with open(markdown_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()
    prompt = f"Explain the following quote from a Swiss popular vote information text:\n{highlighted_text} \n\nTo give you additional context about the quote, here is the full voting booklet where the quote originated: \n{markdown_text}"

    model = data.get("model", "grok-4")
    xai_client = get_xai_client()
    chat = xai_client.chat.create(model=model)
    chat.append(system("You are a highly intelligent AI assistant helping Swiss citizens to freely form an opinion on their own by adding context to their questions and task."))
    chat.append(user(prompt))
    response = chat.sample()

    # Do something with it
    output = {
        "message": "Hello World",
        "highlighted_text": highlighted_text,
        "markdown_path": markdown_path,
        "model": model,
        "prompt": prompt,
        "output": response.content
    }

    return jsonify(output), 200

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
    success, return_string = initialize_data() # TESTMODE=True
    if not success:
        print(f"Failed to initialize data: {return_string}")
        sys.exit(0)

    print("Time of Initialization: ", (time.time() - s) / 60, "minutes")
    # app.run(debug=True, use_reloader=False) # for later: debug=False or at least: use_reloader=False (better performance at start up)

    # Docker version
    app.run(host='0.0.0.0', port=10002, debug=False)
