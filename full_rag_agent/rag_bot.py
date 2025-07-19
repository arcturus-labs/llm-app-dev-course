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

    model = "gpt-4.1"

    system = """You are a helpful assistant that can the user find products from the catalog of furniture, home décor, bedding & bath, and kitchen & dining.

    The user will discuss what they are looking for and it is your job to research the catalog and find the best matches.

    When it's unclear what the user is looking for, you should ask them for more information.

    When you have an idea of what the user is looking for, you should make parallel searches covering different interpretations of the user's request and different wordings of the same request.

    When you see the results, make one more round of clarifying searches based upon the results you've found to this point.

    Finally, report back to the user about all that you've discovered.
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