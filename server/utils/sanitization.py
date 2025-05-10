import re

import markdown
import demoji
from bs4 import BeautifulSoup


def clean_text_for_tts(text):
    """
    Removes Markdown, specific content (links, tables, etc.), and emojis
    from a string for text-to-speech.
    """
    # 1. Remove Emojis
    cleaned_text = demoji.replace(text, "")

    # 2. Convert Markdown to HTML (helps handle links, tables, etc.)
    #    We use a liberal approach here, letting markdown convert as much as possible
    #    before stripping HTML.
    html_text = markdown.markdown(cleaned_text)

    # 3. Remove HTML Tags and Extract Text using BeautifulSoup
    soup = BeautifulSoup(html_text, "html.parser")
    cleaned_text = soup.get_text()

    # 4. Clean up remaining simple Markdown artifacts and excessive whitespace
    # Remove common Markdown symbols that might persist
    cleaned_text = re.sub(r'[*_`]', '', cleaned_text) # Bold, italics, inline code
    cleaned_text = re.sub(r'^#+\s', '', cleaned_text, flags=re.MULTILINE) # Headers

    # Remove URLs that might not have been in Markdown link format
    cleaned_text = re.sub(r'http[s]?://\S+', '', cleaned_text)

    # Replace multiple newlines with a single newline
    cleaned_text = re.sub(r'\n\s*\n', '\n', cleaned_text)

    # Remove leading/trailing whitespace from each line and the whole text
    cleaned_text = '\n'.join(line.strip() for line in cleaned_text.split('\n'))
    cleaned_text = cleaned_text.strip()

    # Replace multiple spaces with a single space
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)


    return cleaned_text