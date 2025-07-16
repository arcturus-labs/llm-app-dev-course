# python 4_rag/rag.py
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
    # This function simulates a movie search. It returns hardcoded movie data
    # based on whether the 'title' or 'about' parameter is provided.
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
# The 'movie_search_schema' defines a tool schema for the LLM. It describes
# the 'search_movies' function, including its parameters and their types.
# This schema is used by the LLM to understand how to call the function.

def movie_search(user_message):
    # Define color variables
    red = "\033[91m"
    green = "\033[92m"
    blue = "\033[94m"
    light_blue = "\033[96m"
    bold = "\033[1m"
    clear_color = "\033[0m"

    print(f"\n{bold}{red}User:{clear_color} {red}{user_message}{clear_color}")

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that can search for movies based on title or description. If you can't find the movie, just say so.",
        },
        {
            "role": "user",
            "content": user_message,
        }
    ]
    # The 'messages' list is initialized with the user's message. This is
    # the input to the LLM.

    model = "gpt-4.1-mini"
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=200,
        temperature=0.7,
        tools=[movie_search_schema], 
        tool_choice="auto"
    )
    # The LLM is called with the user's message. The 'tools' parameter
    # includes the 'movie_search_schema', allowing the LLM to use the
    # 'search_movies' function if needed.

    message = response.choices[0].message

    # Handle tool calls if present
    if message.tool_calls:
        if message.content is not None:
            print(f"\n{bold}{green}Assistant (in tool call):{clear_color} {green}{message.content}{clear_color}")
            
        tool_messages = [message]
        
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            print(f"\n{bold}{blue}Calling tool:{clear_color} {blue}{function_name}({function_args}){clear_color}")
            # The 'function_name' and 'function_args' are extracted from the
            # tool call. 'function_name' is the name of the function that the
            # LLM has decided to call, and 'function_args' are the arguments
            # for that function, parsed from JSON format.

            # Call the appropriate function
            if function_name == "search_movies":
                function_response = search_movies(**function_args)
                print(f"\n{bold}{light_blue}Tool response:{clear_color} {light_blue}{function_response}{clear_color}")
                # If the function name is "search_movies", the 'search_movies'
                # function is called with the provided arguments. The response
                # from this function call is stored in 'function_response'.

                tool_messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response
                })
                # The result of the function call is appended to 'tool_messages'.
                # This dictionary includes the 'tool_call_id' to track which tool
                # call this response corresponds to, the 'role' indicating this
                # is a tool response, the 'name' of the function, and the 'content'
                # which is the actual response from the function. This allows the
                # LLM to incorporate the tool's output into its final response.
            else:
                raise ValueError(f"Unknown function: {function_name}")
        # If the LLM decides to use a tool, it will include 'tool_calls' in
        # its response. Each tool call is processed, and the corresponding
        # function is executed. The results are appended to 'tool_messages'.

        # Get final response with tool outputs
        response = client.chat.completions.create(
            model=model,
            messages=messages + tool_messages,
            max_tokens=200,
            temperature=0.7
        )
        # A second call to the LLM is made, now including the tool outputs
        # in the 'messages'. This allows the LLM to generate a final response
        # that incorporates the results of the tool calls.

    final_response = response.choices[0].message.content
    print(f"\n{bold}{green}Assistant:{clear_color} {green}{final_response}{clear_color}")
    # The final response from the LLM is printed.

if __name__ == "__main__":
    
    print("\n\n\n1 – expect it to call `search_movies(about='gun slinger')`\n===================================\n")
    movie_search("Do you have any good gun slinger movies?")
    
    print("\n\n\n2 – expect it to call `search_movies(title='the best')`\n===================================\n")
    movie_search("I'm looking for a movie that has \"the best\" in the title, but I can't remember the rest of the title.")
    
    print("\n\n\n3 – expect it to not use any tools\n===================================\n")
    movie_search("Tell me a joke about a chicken")
    
    print("\n\n\n4 – expect it to print out an error and tell you about it\n===================================\n")
    movie_search("Get a random movie unqualified by title or description")
# The main block tests the 'movie_search' function with different inputs.
# It demonstrates how the LLM decides whether to use the 'search_movies'
# tool based on the user's message.
    
    