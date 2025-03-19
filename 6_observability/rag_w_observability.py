import openai
import json
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor

# Set up OpenTelemetry tracing infrastructure
# TracerProvider is the core component that creates and manages traces
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure where traces should be exported
# In production, you might send to Jaeger, Zipkin, or other tracing backends
# ConsoleSpanExporter just prints to console for demo purposes
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)

client = openai.Client()

def search_movies(about=None, title=None):
    """Search for movies based on the given criteria."""
    # Create a new span for the search function
    # This allows us to track timing and metadata for this specific operation
    with tracer.start_span("search_movies") as search_func_span:
        # Log important search parameters as span attributes
        search_func_span.set_attribute("search_type", "title" if title else "about")
        
        # Record specific search criteria
        if title:
            search_func_span.set_attribute("search_title", title)
            results = [{
                "title": "The Best Years of Our Lives",
                "description": "Three World War II veterans return home to small-town America to discover that they and their families have been irreparably changed"
            }, {
                "title": "The Best Exotic Marigold Hotel",
                "description": "British retirees travel to India to take up residence in what they believe is a newly restored hotel. Less luxurious than advertised, the Marigold Hotel nevertheless slowly begins to charm in unexpected ways"
            }, {
                "title": "The Best of Everything",
                "description": "An expose of the lives and loves of Madison Avenue working girls and their high-powered career struggles"
            }]
        elif about:
            search_func_span.set_attribute("search_about", about)
            results = [{
                "title": "The Good, the Bad and the Ugly",
                "description": "Three gunslingers compete to find a fortune in buried Confederate gold amid the violent chaos of the American Civil War"
            }, {
                "title": "Once Upon a Time in the West",
                "description": "A mysterious harmonica-playing gunslinger joins forces with a notorious desperado to protect a beautiful widow from a ruthless assassin working for the railroad"
            }, {
                "title": "Unforgiven",
                "description": "An aging outlaw and killer-turned-farmer reluctantly takes on one last job, confronting the brutal realities of his past in a corrupt frontier town"
            }]
        else:
            # Log errors using span status
            search_func_span.set_status(Status(StatusCode.ERROR, "No criteria provided"))
            results = "Error: No criteria provided"
        
        # Track the size of result set
        if isinstance(results, list):
            search_func_span.set_attribute("results_count", len(results))
        return str(results)

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

def execute_tools(tool_calls, messages, model, tracer):
    """Execute tool calls and return tool messages for further processing."""
    # Create span for overall tool execution
    with tracer.start_span("execute_tools") as tools_span:
        tool_messages = []
        
        for tool_call in tool_calls:
            # Create nested span for each individual tool execution
            with tracer.start_span("tool_execution") as tool_span:
                # Track which function is being called
                function_name = tool_call.function.name
                tool_span.set_attribute("function_name", function_name)
                
                # Separate span for argument parsing to track potential issues
                with tracer.start_span("parse_arguments") as parse_span:
                    function_args = json.loads(tool_call.function.arguments)
                    parse_span.set_attribute("arguments", str(function_args))
                
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
                    error_msg = f"Unknown function: {function_name}"
                    tool_span.set_status(Status(StatusCode.ERROR, error_msg))
                    raise ValueError(error_msg)
        
        # Critical span for tracking LLM final response
        with tracer.start_span("llm_final_call") as final_llm_span:
            # Log model and message context
            final_llm_span.set_attribute("model", model)
            final_llm_span.set_attribute("message_count", len(messages + tool_messages))
            final_llm_span.set_attribute("messages", str(messages + tool_messages))
            
            response = client.chat.completions.create(
                model=model,
                messages=messages + tool_messages,
                max_tokens=200,
                temperature=0.7
            )
            # Log important LLM metrics
            final_llm_span.set_attribute("completion_tokens", response.usage.completion_tokens)
            final_llm_span.set_attribute("prompt_tokens", response.usage.prompt_tokens)
            final_llm_span.set_attribute("completion", response.choices[0].message.content)
            
        return response, tool_messages

def movie_search(user_message):
    # Create root span for entire search operation
    with tracer.start_as_current_span("movie_search") as search_span:
        # Log the initial user input
        search_span.set_attribute("user_message", user_message)
        search_span.add_event("user_message_received")
        print("User: ", user_message)

        messages = [{
            "role": "user",
            "content": user_message,
        }]
        
        model = "gpt-4o-mini"
        # Track initial LLM call
        with tracer.start_span("llm_initial_call") as llm_span:
            # Log model configuration and context
            llm_span.set_attribute("model", model)
            llm_span.set_attribute("message_count", len(messages))
            llm_span.set_attribute("messages", str(messages))
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=200,
                temperature=0.7,
                tools=[movie_search_schema], 
                tool_choice="auto"
            )
            # Log LLM performance metrics
            llm_span.set_attribute("completion_tokens", response.usage.completion_tokens)
            llm_span.set_attribute("prompt_tokens", response.usage.prompt_tokens)
            llm_span.set_attribute("completion", response.choices[0].message.content)

        message = response.choices[0].message

        if message.tool_calls:
            search_span.add_event("tool_calls_detected")
            response, _ = execute_tools(message.tool_calls, messages + [message], model, tracer)

        final_response = response.choices[0].message.content
        search_span.add_event("response_generated", {"response_length": len(final_response)})
        print("Assistant: ", final_response)

if __name__ == "__main__":
    movie_search("Do you have any good gun slinger movies?")
    print("\n\n\n\n")