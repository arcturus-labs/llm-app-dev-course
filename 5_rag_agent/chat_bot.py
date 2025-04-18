from openai import OpenAI
import json

class Conversation:
    def __init__(self, model, tools, tool_lookup, system = None, messages=None):
        self.client = OpenAI()
        self.model = model
        self.messages = messages or []
        self.tools = tools
        self.tool_lookup = tool_lookup
        if system:
            if len(self.messages) > 0 and self.messages[0]["role"] != "system":
                self.messages.insert(0, {"role": "system", "content": system})
            if len(self.messages) == 0:
                self.messages.append({"role": "system", "content": system})

    def get_response(self, messages=None):
        kwargs = dict( model=self.model,
            messages=messages,
            max_tokens=3000,
            temperature=0.7,
        )
        if self.tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        return response
        
    def say(self, message):
        # Define color variables
        red = "\033[91m"
        green = "\033[92m"
        blue = "\033[94m"
        light_blue = "\033[96m"
        bold = "\033[1m"
        clear_color = "\033[0m"

        print(f"\n{bold}{red}User:{clear_color} {red}{message}{clear_color}")
        self.messages.append(
            {
                "role": "user",
                "content": message
            }
        )
        response = self.get_response(self.messages)
        response_message = response.choices[0].message
        
        # Handle tool calls if present
        while response_message.tool_calls:
            if response_message.content is not None:
                print(f"\n{bold}{green}Assistant (in tool call):{clear_color} {green}{response_message.content}{clear_color}")
            # Append the assistant's message requesting to use the tool
            self.messages.append(response_message)
            
            # Process each tool call
            for tool_call in response_message.tool_calls:
                # Parse the function arguments
                function_args = json.loads(tool_call.function.arguments)
                
                # Call the function and get the result
                print(f"\n{bold}{blue}Calling tool:{clear_color} {blue}{tool_call.function.name} with args: {function_args}{clear_color}")
                result = self.tool_lookup[tool_call.function.name](**function_args)
                
                # Append the function response to messages
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": str(result)
                })
                
                # Print the tool's response
                print(f"\n{bold}{light_blue}Tool response:{clear_color} {light_blue}{result[:200]}{clear_color}")
            
            # Get a new response from the assistant with the tool results
            response = self.get_response(self.messages)
            response_message = response.choices[0].message
        
        self.messages.append(response_message)
        if response_message.content is not None:
            print(f"\n{bold}{green}Assistant:{clear_color} {green}{response_message.content}{clear_color}")
        return response_message.content


if __name__ == "__main__":
      
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "get_stock_price",
                "description": "Get the current stock price for a given ticker symbol",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "The stock ticker symbol (e.g., AAPL, GOOGL)"
                        }
                    },
                    "required": ["ticker"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The location to get the weather for (e.g., New York, San Francisco)"
                        }
                    },
                    "required": ["location"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_clothing_recommendation",
                "description": "Get a clothing recommendation for a given weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "weather": {
                            "type": "string",
                            "enum": ["sunny", "cloudy", "rainy"],
                            "description": "The weather to get a clothing recommendation for"
                        }
                    },
                    "required": ["weather"]
                }
            }   
        }
    ]

    def get_stock_price(ticker):
        """Mock function to get stock price for a given ticker symbol"""
        mock_prices = {
            "AAPL": "150.00",
            "GOOGL": "2800.00",
            "MSFT": "300.00",
            "AMZN": "3500.00",
            "TSLA": "700.00"
        }
        return mock_prices.get(ticker, f"Price not found for {ticker}")

    def get_weather(location):
        """Mock function to get weather for a given location"""
        mock_weather = {
            "New York City": "20°C, sunny",
            "New York": "20°C, sunny",
            "San Francisco": "15°C, cloudy",
            "Miami": "25°C, rainy",
        }
        return mock_weather.get(location, f"Weather not found for {location}")

    def get_clothing_recommendation(weather):
        """Mock function to get clothing recommendation for a given weather"""
        mock_recommendations = {
            "sunny": "Wear a t-shirt and shorts",
            "cloudy": "Wear a light jacket",
            "rainy": "Wear a raincoat",
        }
        return mock_recommendations.get(weather, f"No recommendation found for {weather}")

    tool_lookup = {
        "get_stock_price": get_stock_price,
        "get_weather": get_weather,
        "get_clothing_recommendation": get_clothing_recommendation
    }
    # Create a conversation instance
    conv = Conversation(
        "gpt-4o", 
        tools=TOOLS, 
        tool_lookup=tool_lookup, 
        system="You are a helpful assistant that can answer questions and help with tasks. You talk like a pirate.",
    )
    
    # Ask about stock prices
    while True:
        # try:
        # "What should I wear in Miami today?"
        # "Is NY any better?"
        response = conv.say(input("User: "))
