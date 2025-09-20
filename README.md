# Analysis-of-Argumentative-Political-Texts-Using-LLMs

## Models
1. Random Forest Model as Baseline
2. Closed source LLMs 
   - grok-4
   - grok-3-mini (partially in the Prototype Application)
   - gpt-5-2025-08-07 (partially in the Prototype Application)
   - gpt-5-mini-2025-08-07 (partially in the Prototype Application)
   - gpt-5-nano-2025-08-07 (removed, controlling for TPM limit add unnecessary complexity)
3. Open source LLMs 
   - Apertus-70B (only in Jupyter Notebook)
   - Apertus-8B (only in Jupyter Notebook)

## Prototype Application with GUI
Run `prototype/app.py` and open `http://127.0.0.1:5000` in browser. Multilanguage and one LLM is implemented. For demonstration and performance purposes, all necessary metadata is stored in `prototype/static/votes.json`. If you want to run the app from scratch you need to create a `.env` file in `prototype/agents/` and add your own API keys.

## Acknowledgement
The Federal Chancellery ([Bundeskanzlei](`https://www.bk.admin.ch/bk/en/home.html`)) kindly provided two endpoints to 
fetch data about past and future Popular Votes and their respective information (Erläuterungen).

All .txt files in `data/srfArena` have been accessed by 
[Digital Democracy Lab](`https://digdemlab.io/eye/2019/04/27/srfarena.html`), a Swiss 
organization concerned with X. In April 2019, they have published a study how much gender, individuals and 
political parties are represented in Switzerland best known debating shown. The same dataset, contained of transcribed 
and annotated subtitles of the debates could be used for argumentation mining and later be assessed for the degree of
polarization, populism or other properties of the statement.