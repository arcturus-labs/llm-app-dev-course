import openai
import json
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor

# Initialize OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Add console exporter for demonstration
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)

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
    with tracer.start_as_current_span("movie_search") as search_span:
        search_span.set_attribute("user_message", user_message)
        search_span.add_event("user_message_received")
        print("User: ", user_message)

        messages = [{
            "role": "user",
            "content": user_message,
        }]
        # The 'messages' list is initialized with the user's message. This is
        # the input to the LLM.

        model = "gpt-4o-mini"
        with tracer.start_span("llm_initial_call") as llm_span:
            llm_span.set_attribute("model", model)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=200,
                temperature=0.7,
                tools=[movie_search_schema], 
                tool_choice="auto"
            )
            llm_span.set_attribute("completion_tokens", response.usage.completion_tokens)
            llm_span.set_attribute("prompt_tokens", response.usage.prompt_tokens)

        message = response.choices[0].message

        # Handle tool calls if present
        if message.tool_calls:
            search_span.add_event("tool_calls_detected")
            tool_messages = [message]
            
            for tool_call in message.tool_calls:
                with tracer.start_span("tool_execution") as tool_span:
                    function_name = tool_call.function.name
                    tool_span.set_attribute("function_name", function_name)
                    
                    with tracer.start_span("parse_arguments") as parse_span:
                        function_args = json.loads(tool_call.function.arguments)
                        parse_span.set_attribute("arguments", str(function_args))
                    
                    print(f"Function: {function_name}({function_args})")
                    # The 'function_name' and 'function_args' are extracted from the
                    # tool call. 'function_name' is the name of the function that the
                    # LLM has decided to call, and 'function_args' are the arguments
                    # for that function, parsed from JSON format.

                    # Call the appropriate function
                    if function_name == "search_movies":
                        with tracer.start_span("search_movies") as search_func_span:
                            search_func_span.set_attribute("search_type", "title" if "title" in function_args else "about")
                            for key, value in function_args.items():
                                search_func_span.set_attribute(f"search_{key}", value)
                            
                            function_response = search_movies(**function_args)
                            search_results = json.loads(function_response.replace("'", '"'))
                            search_func_span.set_attribute("results_count", len(search_results))
                            print("Function response: ", function_response)

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
                        error_msg = f"Unknown function: {function_name}"
                        tool_span.set_status(Status(StatusCode.ERROR, error_msg))
                        raise ValueError(error_msg)
            # If the LLM decides to use a tool, it will include 'tool_calls' in
            # its response. Each tool call is processed, and the corresponding
            # function is executed. The results are appended to 'tool_messages'.

            # Get final response with tool outputs
            with tracer.start_span("llm_final_call") as final_llm_span:
                final_llm_span.set_attribute("model", model)
                response = client.chat.completions.create(
                    model=model,
                    messages=messages + tool_messages,
                    max_tokens=200,
                    temperature=0.7
                )
                final_llm_span.set_attribute("completion_tokens", response.usage.completion_tokens)
                final_llm_span.set_attribute("prompt_tokens", response.usage.prompt_tokens)

        final_response = response.choices[0].message.content
        search_span.add_event("response_generated", {"response_length": len(final_response)})
        print("Assistant: ", final_response)

if __name__ == "__main__":
    movie_search("Do you have any good gun slinger movies?")