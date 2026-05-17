import logging
from typing import Generator, List, Dict, Optional
import openai
from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from config import Config
from database import get_conversation_messages, save_message, get_db

logger = logging.getLogger(__name__)

class AIHandler:
    """Handles communication with the DeepSeek API, including chat history management and streaming."""

    def __init__(self) -> None:
        """Initializes the AI handler with configuration from Config."""
        self.api_key: str = Config.DEEPSEEK_API_KEY
        self.base_url: str = Config.DEEPSEEK_BASE_URL
        self.model: str = Config.DEEPSEEK_MODEL
        self.max_tokens: int = Config.DEEPSEEK_MAX_TOKENS
        self.temperature: float = Config.DEEPSEEK_TEMPERATURE
        self.client: Optional[OpenAI] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Creates the OpenAI client with DeepSeek configuration."""
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except Exception as e:
            logger.error("Failed to initialize OpenAI client: %s", e)
            self.client = None

    def _build_messages(self, conversation_id: int, user_message: str) -> List[Dict[str, str]]:
        """Constructs the message list for the API call from conversation history.

        Args:
            conversation_id: The ID of the conversation.
            user_message: The new user message to append.

        Returns:
            A list of message dictionaries for the API.
        """
        try:
            history = get_conversation_messages(conversation_id)
        except Exception as e:
            logger.error("Error fetching conversation history: %s", e)
            history = []

        messages: List[Dict[str, str]] = []
        for msg in history:
            # Each msg is expected to be a dict with keys 'role' and 'content'
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})
        return messages

    def send_message(self, conversation_id: int, user_message: str) -> str:
        """Sends a message to DeepSeek API and returns the response (non-streaming).

        Args:
            conversation_id: The conversation ID for context.
            user_message: The user's message.

        Returns:
            The assistant's response text.

        Raises:
            RuntimeError: If API call fails.
        """
        if not self.client:
            raise RuntimeError("AI client not initialized.")

        messages = self._build_messages(conversation_id, user_message)

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=False
            )
            response_text: str = completion.choices[0].message.content.strip()
            # Save both user and assistant messages
            self._save_exchange(conversation_id, user_message, response_text)
            return response_text
        except APIError as e:
            logger.error("DeepSeek API error: %s", e)
            raise RuntimeError(f"API returned an error: {e}")
        except RateLimitError as e:
            logger.error("Rate limit exceeded: %s", e)
            raise RuntimeError("Rate limit exceeded. Please wait and try again.")
        except APITimeoutError as e:
            logger.error("API timeout: %s", e)
            raise RuntimeError("The request timed out. Please try again.")
        except Exception as e:
            logger.error("Unexpected error during API call: %s", e)
            raise RuntimeError("An unexpected error occurred while processing your request.")

    def stream_response(self, conversation_id: int, user_message: str) -> Generator[str, None, None]:
        """Sends a message to DeepSeek API and yields streamed response chunks.

        Args:
            conversation_id: The conversation ID for context.
            user_message: The user's message.

        Yields:
            Chunks of the assistant's response text.

        Raises:
            RuntimeError: If API call fails.
        """
        if not self.client:
            raise RuntimeError("AI client not initialized.")

        messages = self._build_messages(conversation_id, user_message)
        full_response: List[str] = []

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content_chunk = chunk.choices[0].delta.content
                    full_response.append(content_chunk)
                    yield content_chunk
            # Save the complete exchange
            assistant_response = ''.join(full_response).strip()
            self._save_exchange(conversation_id, user_message, assistant_response)
        except APIError as e:
            logger.error("DeepSeek streaming API error: %s", e)
            yield f"API error: {e}"
        except RateLimitError as e:
            logger.error("Rate limit during streaming: %s", e)
            yield "Rate limit exceeded. Please wait and try again."
        except APITimeoutError as e:
            logger.error("Streaming timeout: %s", e)
            yield "The request timed out. Please try again."
        except Exception as e:
            logger.error("Unexpected streaming error: %s", e)
            yield "An unexpected error occurred during streaming."

    def _save_exchange(self, conversation_id: int, user_message: str, assistant_message: str) -> None:
        """Saves the user and assistant messages to the database.

        Args:
            conversation_id: The conversation ID.
            user_message: User's message content.
            assistant_message: Assistant's response content.
        """
        try:
            save_message(conversation_id, "user", user_message)
            save_message(conversation_id, "assistant", assistant_message)
        except Exception as e:
            logger.error("Failed to save messages to database: %s", e)

# Singleton instance for easy import
ai_handler = AIHandler()