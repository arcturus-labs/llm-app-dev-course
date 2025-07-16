from chat_bot import Conversation
from search_docs import high_level_search, format_results_for_toolcall

        
def main():
    tools = [{
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": "Search for products in the catalog using various filters. Sometimes the results will be an imperfect match for the query. If you feel that the results can be improved, you should refine the query by adding a product_class filter or by modifying the query string to use different search terms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_string": {
                        "type": "string",
                        "description": "The search query to match against product names and descriptions"
                    },
                    "product_class": {
                        "type": "string",
                        "description": "Filter results by product class. It is important to use exact string matches from the product_class list, so only use this after making a preliminary query_string-only search and reviewing the product_class facet.",
                        "optional": True
                    },
                    "min_average_rating": {
                        "type": "number",
                        "description": "Filter results by minimum average rating - this should be a number between 0 and 5",
                        "optional": True
                    },
                },
                "required": ["query_string"]
            }
        }
    }]

    tool_lookup = {
        "search_catalog": lambda **x: format_results_for_toolcall(high_level_search(**x))
    }

    model = "gpt-4o"

    system = """
    You are a helpful assistant that can the user find products from the catalog.

    The user will discuss what they are looking for and it is your job to research the catalog and find the best matches. Research follows these steps:
    1. Make a preliminary search based on whatever the user says they want. Always start with a simple, general search, and then refine it based on the results and the values in the facet counts.
    2. Review the results in order to get a sense of what is available. Pay special attention to the product_classes and counts that are available.
    3. Prior to answering the user, make additional refined searches based on what you learned from the results of the preliminary search. If the results contain irrelevant items mixed in, then consider adding a product_class filter to narrow the scope.
    4. Finally, report back to the user about all that you've discovered.

    When reporting the results follow these steps:
    1. Start with a quick summary of the relevant results (across all searches) that is addresses how they will help the user based upon the context of the conversation.
    2. Describe the natural grouping of the results as represented by the product_classes Facet Counts. Then you should present the top most relevant results sorted by relevance. Make sure to manually filter out results that you deem irrelevant.
    3. At the end, make recommendations for further research that you can do to help the user find what they are looking for.

    In followup conversations, you should continue to refine the search until the user is satisfied. The user might add new criteria. Don't assume that the results you have already found are the most relevant. Instead add the new criteria to the search (product_class, min_average_rating) and search again.
    """

    c = Conversation(model, tools, tool_lookup, system)
    
    print("Hint: Try to get the assistant to exercist all the arguments of the search_catalog function: query_string, product_class, min_average_rating")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit']:
            break
        c.say(user_input)

if __name__ == "__main__":
    main()