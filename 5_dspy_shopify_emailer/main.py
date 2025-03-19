import os
import sys
import dspy
from bs4 import BeautifulSoup
import re

def simplify_html(html):
    # Parse the HTML
    soup = BeautifulSoup(html, 'html.parser')

    # Remove all ids and classes
    for tag in soup():
        del tag['id']
        del tag['class']

    # Remove all scripts and styles
    for script in soup(["script", "style"]):
        script.extract()

    # Replace images with placeholders containing alt text
    for img in soup.find_all('img'):
        img.replace_with('[' + img.get('alt', '') + ']')

    # Remove any remaining HTML tags attributes
    for tag in soup.find_all(True):
        for attribute in tag.attrs:
            tag.attrs[attribute] = ''

    # Get the simplified HTML
    simplified_html = str(soup)

    # Remove extra whitespace
    simplified_html = re.sub(r'\s+', ' ', simplified_html).strip()

    return simplified_html


class SummarizeSignature(dspy.Signature):
    """Review storefront website and summarize it"""
    storefront = dspy.InputField(desc="Simplified HTML of storefront.")

    selling = dspy.OutputField(desc="What types of products are being sold?")
    principles = dspy.OutputField(desc="What principles do they uphold as important?")
    tone = dspy.OutputField(desc="What is their overall tone (e.g. playful, formal, adventurous, relaxing)?")
    themes = dspy.OutputField(desc="Do you see any themes (travel, productivity, exercise)?")
    praiseworthy = dspy.OutputField(desc="What do you find praiseworthy and timely? Is there any news that this store would be proud of?")
    observations = dspy.OutputField(desc="What else do you see that is noteworthy?")
    
class Summarize(dspy.Module):
    def __init__(self):
        super().__init__()
        self.summarizer = dspy.Predict(SummarizeSignature)
    
    def forward(self, storefront_html):
        resp = self.summarizer(storefront=simplify_html(storefront_html))
        summary='\n'.join([f"{k}: {resp[k]}" for k in resp.keys()])
        return summary

class BrainstormSignature(dspy.Signature):
    """Toss out a few ideas for plugins. Then identify the best one in terms of impact to customer, match with their brand, and ease of implementation."""
    store_summary = dspy.InputField(desc="Information about how the storefront")
    
    brainstorm_result = dspy.OutputField(desc="A list of ideas and then an explanation of which idea is best and why.")

    
class IdeateSignature(dspy.Signature):
    """Take the best plugin idea, restate the name of the idea, and create an in-depth analysis of just that idea. Explain the idea in detail. How would it look? How would the store's users interact with it? How would is make money for the store? At a high level, how would it be implemented?"""
    store_summary = dspy.InputField(desc="Information about how the storefront")
    brainstorm_result = dspy.InputField(desc="A list of ideas and then an explanation of which idea is best and why.")

    idea_description = dspy.OutputField(desc="The details about an idea.")


class Ideate(dspy.Module):
    def __init__(self):
        super().__init__()
        self.brainstormer = dspy.Predict(BrainstormSignature)
        self.ideator = dspy.Predict(IdeateSignature)
    
    def forward(self, store_summary):
        brainstorm_result = self.brainstormer(store_summary=store_summary).brainstorm_result
        idea_description = self.ideator(store_summary=store_summary, brainstorm_result=brainstorm_result).idea_description
        return idea_description

from textwrap import dedent 
class GenerateEmailSignature(dspy.Signature):
    """You are a copywriter for JivePlugins.
    
    Initially consider your rationale for writing the email. What is the strategy that will best attract a new customer?

    Then write an email promoting our plugin idea.
        - It should be in a style that matches the vibe of the website.
        - If possible, give a genuine compliment that links back to something we found on the website.
        - It should make use of our earlier discussion about strategy - selling them on the highlights and practicality of the plugin concept.
        - It should include a description of the plugin idea:
        - Help them understand what it will look like.
        - Help them understand how the users will engage.
        - Help them understand the bottom line for business.
        - It should have a call to action to reach out to JivePlugins for further conversation.
        - Address the "${store_name} Team" in the salutation
        - The signature should be from "Albert Berryman" the "Director of Innovation" of JivePlugins Inc."""
    store_name = dspy.InputField()
    store_summary = dspy.InputField()
    idea_description = dspy.InputField()

    email_subject = dspy.OutputField()
    email_body = dspy.OutputField()

class GenerateEmail(dspy.Module):
    def __init__(self):
        super().__init__()
        self.email_generator = dspy.ChainOfThought(GenerateEmailSignature)
    
    def forward(self, store_name, store_summary, idea_description):
        email = self.email_generator(store_name=store_name, store_summary=store_summary, idea_description=idea_description)
        return {
            'subject': email.email_subject,
            'body': email.email_body,
        }

class SummarizeIdeateEmail(dspy.Module):
    def __init__(self):
        super().__init__()
    
    def forward(self, store_name, storefront_html):
        store_summary = Summarize()(storefront_html=storefront_html)
        idea = Ideate()(store_summary=store_summary)
        email = GenerateEmail()(store_name=store_name, store_summary=store_summary, idea_description=idea)
        return email

def list_storefronts(directory):
    # List all HTML files in the directory
    files = os.listdir(directory)
    html_files = [f.replace('.html', '') for f in files if f.endswith('.html')]
    return html_files


if __name__ == "__main__":
    # Set up the LM
    model = dspy.LM('openai/gpt-4o-mini', api_key=os.environ['OPENAI_API_KEY'])
    dspy.settings.configure(lm=model)

    # Directory containing the HTML files
    directory = 'storefronts'

    # Check for command-line arguments
    if len(sys.argv) > 1:
        # Get the storefront name from the argument
        storefront_name = sys.argv[1]
        html_file = os.path.join(directory, f"{storefront_name}.html")

        # Read the HTML content from the file
        with open(html_file, 'r') as file:
            storefront_html = file.read()

        # Generate the email
        email = SummarizeIdeateEmail()(store_name=storefront_name, storefront_html=storefront_html)
        print(f"Subject: {email['subject']}")
        print(f"Body: {email['body']}")
    else:
        # List available storefronts
        storefronts = list_storefronts(directory)
        print("Available storefronts:")
        for name in storefronts:
            print(name)
