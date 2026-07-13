
import argparse
import json
import sys
import os
import requests # Для взаимодействия с Ollama API

# Default Ollama API endpoint
OLLAMA_API_URL = "http://localhost:11434/api/chat"

def call_ollama_for_tool_prediction(query: str, tools_json_string: str, model_name: str,
                                     temperature: float = 0.7,
                                     num_predict: int = -1):
    """
    Calls the Ollama API to get a tool call prediction from the specified model.
    This function orchestrates the interaction with Ollama for tool calling.
    """
    try:
        # 1. Преобразование наших определений инструментов в формат, ожидаемый Ollama API.
        # Ollama ожидает список словарей с ключами 'type' (function) и 'function' (с name, description, parameters).
        tools_for_ollama = []
        tool_definitions = json.loads(tools_json_string)
        for tool in tool_definitions:
            if 'name' in tool and 'description' in tool and 'parameters' in tool and isinstance(tool['parameters'], dict):
                tools_for_ollama.append({
                    'type': 'function',
                    'function': {
                        'name': tool['name'],
                        'description': tool['description'],
                        'parameters': tool['parameters'] # Предполагаем, что OpenAPI spec совместима
                    }
                })
            else:
                # Handle tools without parameters or with incorrect structure if necessary
                # For simplicity, we'll skip malformed tool definitions for now.
                print(f"Warning: Skipping tool '{tool.get('name', 'unknown')}' due to missing or invalid parameters.", file=sys.stderr)

        # 2. Формирование сообщений для Ollama Chat API.
        # Системное сообщение инструктирует модель использовать инструменты и выводить результат в нужном формате.
        # Запрос пользователя включает задачу и список доступных инструментов.
        messages = [
            {
                "role": "system",
                "content": f"You are a helpful assistant designed to call tools. Given a user query and a list of available tools, you must determine which tool to call. Output the tool call in the following JSON format: {{ \"name\": \"tool_name\", \"arguments\": {{ \"arg1\": \"value1\", ... }} }}. Only output the JSON for the tool call. Do not include any other text, explanations, or markdown formatting. If multiple tools can be used, pick the most appropriate one. If no tool is appropriate, respond with an empty JSON object {{}}."
            },
            {
                "role": "user",
                "content": f"Task: {query}\nTools: {json.dumps(tools_for_ollama)}"
            }
        ]

        payload = {
            "model": model_name,
            "messages": messages,
            "tools": tools_for_ollama, # Pass tools directly to Ollama API
            "stream": False, 
            "options": {
                "temperature": temperature,
                "num_predict": num_predict, # -1 means default (often max tokens)
                "stop": ["}}", "]", "{{"] # Попытка остановить генерацию после JSON объекта, может потребовать тюнинга.
            }
        }

        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status() # Raise an exception for bad status codes

        response_data = response.json()

        # Ollama's response for tool calls might be in 'content' or 'tool_calls'
        # We need to parse this to get the structured tool call.
        if response_data.get('tool_calls'):
            # Ollama >= 0.1.34 has the tool_calls field
            tool_calls = response_data['tool_calls']
            if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
                # Ollama's tool call structure might be like: [{\'id\': '...', \'type\': 'function', \'function': {'name': '...', 'arguments': {...}}}] 
                # We need to extract the function name and arguments
                ollama_tool = tool_calls[0]
                if ollama_tool.get('type') == 'function':
                    function_info = ollama_tool.get('function', {})
                    # Ensure arguments is a dictionary before loading JSON
                    arguments_str = function_info.get('arguments', '{}')
                    try:
                        arguments_dict = json.loads(arguments_str)
                    except json.JSONDecodeError:
                        arguments_dict = {"error": f"Invalid JSON in arguments: {arguments_str}"}
                        
                    return {
                        "name": function_info.get('name'),
                        "arguments": arguments_dict
                    }
                else:
                    return {"error": "Ollama returned a non-function tool call type."}
            else:
                return {"error": "No valid tool calls found in Ollama response."}
        elif response_data.get('message', {}).get('content'):
            # If no 'tool_calls', try to parse 'message.content' as JSON
            # Some models might output the tool call directly in content.
            content = response_data['message']['content'].strip()
            try:
                parsed_content = json.loads(content)
                # Check if it matches the expected tool call structure
                if isinstance(parsed_content, dict) and "name" in parsed_content and "arguments" in parsed_content:
                    return parsed_content
                else:
                    # If not JSON or not expected structure, it might be plain text or an error message.
                    return {"error": f"Ollama response content was not a valid tool call JSON. Content: {content}"}
            except json.JSONDecodeError:
                # If it's not JSON, it's likely a regular text response.
                return {"error": f"Ollama response content was not JSON. Content: {content}"}
        else:
            return {"error": "Unexpected response structure from Ollama API."}

    except requests.exceptions.ConnectionError:
        print(f"Error: Ollama server is not running or not accessible at {OLLAMA_API_URL}. Please ensure Ollama is installed and running.", file=sys.stderr)
        return {"error": "Ollama server connection failed."}
    except requests.exceptions.Timeout:
        print(f"Error: Ollama server timed out at {OLLAMA_API_URL}.", file=sys.stderr)
        return {"error": "Ollama API request timed out."}
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}", file=sys.stderr)
        return {"error": f"Ollama API request failed: {e}"}
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}", file=sys.stderr)
        return {"error": f"Failed to parse Ollama API response: {e}"}
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return {"error": f"An unexpected error occurred: {e}"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Qwen LLM via Ollama for tool call prediction.")
    parser.add_argument("--query", type=str, required=True,
                        help="The natural language query for the junior LLM.")
    parser.add_argument("--tools", type=str, required=True,
                        help="A JSON string representing a list of available tools (OpenAPI spec).")
    parser.add_argument("--model-name", type=str, default="qwen:0.5b",
                        help="The Ollama model name (e.g., 'qwen:0.5b').")
    parser.add_argument("--temperature", type=float, default=0.7,
                        help="Sampling temperature for generation.")
    parser.add_argument("--num-predict", type=int, default=-1,
                        help="Number of tokens to predict. -1 for default.")

    args = parser.parse_args()

    # Проверяем, запущен ли Ollama сервер
    try:
        # Using a small timeout to quickly check connectivity without hanging
        requests.get("http://localhost:11434", timeout=1)
    except requests.exceptions.ConnectionError:
        print("Error: Ollama server is not running or not accessible at http://localhost:11434.", file=sys.stderr)
        print("Please ensure Ollama is installed and running.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"Error: Ollama server did not respond within the timeout period at http://localhost:11434.", file=sys.stderr)
        sys.exit(1)

    prediction = call_ollama_for_tool_prediction(
        query=args.query,
        tools_json_string=args.tools,
        model_name=args.model_name,
        temperature=args.temperature,
        num_predict=args.num_predict
    )
    print(json.dumps(prediction))
