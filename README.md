# Analysis-of-Argumentative-Political-Texts-Using-LLMs

## Models
1. Random Forest Model as Baseline
2. Closed source LLMs 
   - grok-4
   - grok-3-mini (partially in the Prototype Application)
   - gpt-5-2025-08-07 (partially in the Prototype Application)
   - gpt-5-mini-2025-08-07 (partially in the Prototype Application)
3. Open source LLMs 
   - Apertus-8B (only in Jupyter Notebook)
   - Apertus-70B (only in Jupyter Notebook)

## Prototype Application with GUI
Instructions to prepare your `.env` file and how the prototype can be started and used.

### Preparations
Create the `.env` file as followed in the `path/prototype` directory:

```
HUGGINFACE_TOKEN=[Your Token]
OPENAI_API_KEY=[Your Token]
XAI_API_KEY=[Your Token]
BK_API_VORLAGE=[API endpoint provided by the Swiss Federal Chancellary]
BK_API_ERLAEUTERUNGEN=[API endpoint provided by the Swiss Federal Chancellary]
MODEL_CONFIG=[{"provider": "OpenAI", "models": ["gpt-5", "gpt-5-mini"]}, {"provider": "xAI", "models": ["grok-4", "grok-3-mini"]}]
```

`BK_API_VORLAGE` and `BK_API_ERLAEUTERUNGEN` are not public and can be requested by [email](support@bk.admin.ch). 

Feel free to amend `MODEL_CONFIG` to your need or add future models. `gpt-5-nano` is not used due to the TPM limit of 200 000 token (as of 20.09.2025), see [API Documentation](https://platform.openai.com/docs/models/gpt-5-nano) for more details.

### Initialize Prototype
Run `prototype/app.py` and open [http://127.0.0.1:5000](http://127.0.0.1:5000) in browser. Multilanguage and one LLM is implemented. For demonstration and performance purposes, all necessary metadata is stored in `prototype/static/votes.json`. If you want to run the app from scratch you need to create a `.env` file in `prototype/agents/` and add your own API keys.

#### Test mode
The test mode can be set in `app.py` by `initialize_data(TESTMODE=True)`. This limits the number of votes to 1 to 5 elements, instead of loading and processing all 380 popular votes, which are currently available.

### Docker Container on HSG Infrastructure
Let's configure the app with docker as followed:
- Container name: `christoph-zweifel-container`
- App name: `smart-voting-booklet-app`

To start the docker container run the following commands:

Build the app
```
docker build -t smart-voting-booklet-app .
```
Start the Docker container with the app
```
docker run -d -p 5000:5000 --name christoph-zweifel-container smart-voting-booklet-app
```

To check if things are running smoothly or debug:
```
docker ps
docker logs christoph-zweifel-container
```

To stop and remove both the container and the built app:
```
docker stop christoph-zweifel-container
docker rm christoph-zweifel-container
docker rmi smart-voting-booklet-app
```

## Acknowledgement
The Federal Chancellery ([Bundeskanzlei](https://www.bk.admin.ch/bk/en/home.html)) kindly provided two endpoints to 
fetch data about past Popular Votes and their respective information (Erläuterungen).

The module [swissparlpy](https://github.com/metaodi/swissparlpy) is used to fetch information about parlamentary votes to enrich the data in the protopye.

All .txt files in `data/srfArena` have been accessed by 
[Digital Democracy Lab](https://digdemlab.io/eye/2019/04/27/srfarena.html), a Swiss 
organization concerned with X. In April 2019, they have published a study how much gender, individuals and 
political parties are represented in Switzerland best known debating shown. The same dataset, contained of transcribed 
and annotated subtitles of the debates could be used for argumentation mining and later be assessed for the degree of
polarization, populism or other properties of the statement.