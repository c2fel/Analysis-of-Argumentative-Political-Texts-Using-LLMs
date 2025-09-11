import inspect
import json
import os

import tiktoken
from dotenv import load_dotenv
from xai_sdk import Client
from xai_sdk.chat import system, user

load_dotenv()


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

    # Create a warning if context window too high
    encoding = tiktoken.get_encoding("cl100k_base")

    # Tokens zählen
    tokens = len(encoding.encode(prompt))

    # Check gegen Limit
    # limit = 131072 # grok 3 mini
    limit = 256000 # grok 4
    if tokens > limit:
        print(f"Context Window überschritten in {inspect.currentframe().f_code.co_name}")
    elif tokens > limit * 0.8:  # 80% Puffer für Response
        print(f"Context Window nahe am Limit (80%) in {inspect.currentframe().f_code.co_name}")

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