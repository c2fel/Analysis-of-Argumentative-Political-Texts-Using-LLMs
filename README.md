# Analysis-of-Argumentative-Political-Texts-Using-LLMs

## Models
1. Random Forest Model as Baseline
2. Comparison of open and closed LLM models

## UI
Run `prototype/app.py` and open `http://127.0.0.1:5000` in browser. There are currently no LLM functions in this prototype.

## Acknowledgement
The Federal Chancellery ([Bundeskanzlei](`https://www.bk.admin.ch/bk/en/home.html`)) kindly provided two endpoints to 
fetch data about past and future Popular Votes and their respective information (Erläuterungen).

All .txt files in `data/srfArena` have been accessed by 
[Digital Democracy Lab](`https://digdemlab.io/eye/2019/04/27/srfarena.html`), a Swiss 
organization concerned with X. In April 2019, they have published a study how much gender, individuals and 
political parties are represented in Switzerland best known debating shown. The same dataset, contained of transcribed 
and annotated subtitles of the debates could be used for argumentation mining and later be assessed for the degree of
polarization, populism or other properties of the statement.