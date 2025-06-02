from anthropic import Anthropic
from anthropic import APIConnectionError, RateLimitError, APIStatusError
import json # Import the json module

def conforms_to_guidelines(llm_response: str) -> bool:
    """
    Checks if the LLM response conforms to the specified guidelines.

    Args:
        llm_response: The response from the LLM to be validated.

    Returns:
        True if the response conforms to all guidelines, False otherwise.
    """
    try:
        # Parse the JSON response
        response_json = json.loads(llm_response)

        # Check each guideline
        return all(response_json.values())
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response as JSON: {e}")
        return False
    except Exception as e:
        print(f"Error processing LLM response: {e}")
        return False

def validate_data_with_claude(
    user_data_text: str,
    api_key: str = None,
    model_name: str = "claude-3-5-sonnet-20240620",
    max_tokens: int = 1024
) -> str:
    try:
        client = Anthropic(api_key = api_key)

        policies_text = """
        1. The user data must not contain any personally identifiable information (PII).
        2. Speaks with a professional tone.
        3. The user data must be relevant to the task at hand.
        4. The user data must not contain any offensive or inappropriate content.
        5. The user data must only have information related to Zededa, Zedcloud or Edge Management.
        6. The user data must not contain any confidential or sensitive information.
        7. The user data must only have content to Zededa, Zedcloud specific objects like application instances, device, edge nodes, eve images, metrics etc.
        8. The user data must not contain any information that is not related to Zededa, Zedcloud or Edge Management.
        """

        systemprompt_text = f"""CONTEXT: You are a supervisor tasked with validating user data against specific policies.
Your role is to ensure that the user data adheres to the provided policies between the <policies></policies> tags.

<policies>
{policies_text}
</policies>

INSRUCTION: ONLY output a JSON object indicating whether the response message is compliant with each of the guidelines. Each of the keys in the JSON object corresponds to the guidelines mentioned above. The JSON object should follow the format of this example:
{{
  "not-personally-identifiable": < true/false >,
  "professional-tone": < true/false >,
  "relevant-to-task-at-hand": < true/false >,
  "not-offensive-or-inappropriate": < true/false >,
  "related-to-zededa-zedcloud": < true/false >,
  "not-confidential": < true/false >,
  "zededa-zedcloud-specific-objects": < true/false >,
  "not-unrelated-to-zededa-zedcloud": < true/false >
}}
        """

        full_prompt = f"""
{user_data_text}
        """

        message = client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "assistant",
                    "content": systemprompt_text
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]
        )

        if message.content and len(message.content) > 0:
            print(f"Claude response: {message.content[0].text}")
            return message.content[0].text
        else:
            return "Error: No content in response from Claude."

    except APIConnectionError as e:
        # Log the error or handle it as per your application's needs
        print(f"Anthropic API connection error: {e}")
        raise
    except RateLimitError as e:
        print(f"Anthropic API rate limit exceeded: {e}")
        raise
    except APIStatusError as e:
        print(f"Anthropic API status error: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise