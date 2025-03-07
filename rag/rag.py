import openai
import json
client = openai.Client()

def search_movies(about=None, title=None):
    """
    Search for movies based on the given criteria.

    Args:
        about (str): The description of the movie (semantic search)
        title (str): The title of the movie (lexical search)

    Returns:
        list: A list of movies that match the given criteria.
    """

    if title:
        return str([{
            "title": "The Best Years of Our Lives",
            "description": "Three World War II veterans return home to small-town America to discover that they and their families have been irreparably changed"
        }, {
            "title": "The Best Exotic Marigold Hotel",
            "description": "British retirees travel to India to take up residence in what they believe is a newly restored hotel. Less luxurious than advertised, the Marigold Hotel nevertheless slowly begins to charm in unexpected ways"
        }, {
            "title": "The Best of Everything",
            "description": "An expose of the lives and loves of Madison Avenue working girls and their high-powered career struggles"
        }])
    elif about:
        return str([{
            "title": "The Good, the Bad and the Ugly",
            "description": "Three gunslingers compete to find a fortune in buried Confederate gold amid the violent chaos of the American Civil War"
        }, {
            "title": "Once Upon a Time in the West",
            "description": "A mysterious harmonica-playing gunslinger joins forces with a notorious desperado to protect a beautiful widow from a ruthless assassin working for the railroad"
        }, {
            "title": "Unforgiven",
            "description": "An aging outlaw and killer-turned-farmer reluctantly takes on one last job, confronting the brutal realities of his past in a corrupt frontier town"
        }])
    else:
        return "Error: No criteria provided"

movie_search_schema = {
    "type": "function",
    "function": {
        "name": "search_movies",
        "description": "Search for movies based on title or description",
        "parameters": {
            "type": "object",
            "properties": {
                "about": {
                    "type": "string",
                    "description": "Description of the movie."
                },
                "title": {
                    "type": "string",
                    "description": "Title of the movie (or partial title). Must be exact match."
                }
            },
            "required": []
        }
    }
}


def movie_search(user_message):
    print("User: ", user_message)

    messages = [{
        "role": "user",
        "content": user_message,
    }]

    model = "gpt-4o-mini"
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=200,
        temperature=0.7,
        tools=[movie_search_schema],
        tool_choice="auto"
    )

    message = response.choices[0].message

    # Handle tool calls if present
    if message.tool_calls:
        tool_messages = [message]
        
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            print(f"Function: {function_name}({function_args})")
            
            # Call the appropriate function
            if function_name == "search_movies":
                function_response = search_movies(**function_args)
                print("Function response: ", function_response)
                tool_messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response
                })
            else:
                raise ValueError(f"Unknown function: {function_name}")
        
        # Get final response with tool outputs
        response = client.chat.completions.create(
            model=model,
            messages=messages + tool_messages,
            max_tokens=200,
            temperature=0.7
        )
        
    final_response = response.choices[0].message.content

    print("Assistant: ", final_response)

if __name__ == "__main__":
    print("\n\n\n1 – expect it to call `search_movies(about='gun slinger')`\n===================================\n")
    movie_search("Do you have any good gun slinger movies?")
    print("\n\n\n2 – expect it to call `search_movies(title='the best')`\n===================================\n")
    movie_search("I'm looking for a movie that has \"the best\" in the title, but I can't remember the rest of the title.")
    print("\n\n\n3 – expect it to not use any tools\n===================================\n")
    movie_search("Tell me a joke about a chicken")
    print("\n\n\n4 – expect it to print out an error and tell you about it\n===================================\n")
    movie_search("Get a random movie unqualified by title or description")
    
    