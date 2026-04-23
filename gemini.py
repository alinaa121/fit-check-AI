from google.genai import types
from google.genai import client
import os
from config import *
from dotenv import load_dotenv
import logging
from typing import Any, List, Optional

logging.basicConfig(
        format='%(asctime)s %(filename)s %(levelname)s: %(message)s',
        level=logging.INFO)

class GeminiClient:
    def __init__(self) -> None:
        """
        Initializes the GeminiClient by loading environment variables and creating a Gemini client instance.
        """
        load_dotenv()
        self.client = client.Client(api_key=os.getenv("gemini"))

    def call_gemini(self, content_parts: List[Any], model: str, config: Optional[Any] = None) -> Optional[Any]:
        """
        Calls the Gemini API to generate content based on the provided content parts and model.

        Args:
            content_parts (List[Any]): List of content parts (e.g., text, image) to send to Gemini.
            model (str): The model name to use for content generation.
            config (Optional[Any]): Optional configuration for the request (e.g., tools, functions).

        Returns:
            Optional[Any]: The response from the Gemini API, or None if an error occurred.
        """
        logging.info(f"Calling gemini with model: {model} and content_parts: {content_parts}")
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=[
                    types.Content(parts=content_parts)
                ],
                config=config
            )
            logging.info(f"Gemini API response: {response}")
            return response
        
        except Exception as e:
            logging.error(f"Error calling Gemini API: {e}")
            return None