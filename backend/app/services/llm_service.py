import json
import logging
from typing import List, Dict

from groq import Groq

from app.core.config import settings
from app.services.quiz_parser import QUIZ_NUM_QUESTIONS, QuizFormatError, parse_quiz_payload

logger = logging.getLogger(__name__)

QUIZ_MAX_INPUT_CHARS = 15000

class LLMService:
    def __init__(self):
        # Connect to Groq using the API key from .env
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL

    def generate_response(self, prompt: str, context_chunks: List[Dict] = None, history: List[Dict] = None) -> str:
        """Takes a question and relevant context, and asks Groq for an answer."""
        
        system_prompt = (
            "You are PathShala, a friendly and intelligent AI tutor. "
            "If the user asks a basic conversational question (like greetings, 'hi', 'how are you?', or 'who are you?'), answer naturally and politely as a helpful tutor. "
            "HOWEVER, if the user asks a factual question or something about a specific topic, you must ONLY answer based on the provided context from their document. "
            "If their factual question cannot be answered from the context, you must say 'I cannot find the answer in this document.' "
            "Always be helpful, encouraging, and clear."
        )
        
        user_prompt = ""
        # If we found relevant text in the PDF, inject it into the prompt!
        if context_chunks:
            user_prompt += "Here is some context from the student's study material:\n\n"
            for chunk in context_chunks:
                user_prompt += f"- {chunk['text']}\n"
            user_prompt += "\n"
            
        user_prompt += f"Student's Question: {prompt}"

        # Construct messages array with history
        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            messages.extend(history)
            
        messages.append({"role": "user", "content": user_prompt})

        # Send the request to Groq (this takes less than a second!)
        chat_completion = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            temperature=0.3, # Low temperature = less hallucinations
        )
        
        return chat_completion.choices[0].message.content

    def _request_quiz(self, messages: List[Dict]) -> str:
        chat_completion = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        return chat_completion.choices[0].message.content or ""

    def generate_quiz(self, document_text: str) -> List[Dict]:
        """Generate a validated multiple-choice quiz from document text.

        Retries once if the first reply isn't a usable quiz. Raises ValueError
        (without calling the LLM) for empty text, and QuizFormatError if both
        attempts fail.
        """
        if not document_text or not document_text.strip():
            raise ValueError("document_text is empty")

        system_prompt = (
            f"You are a quiz generator. Based on the provided document text, create exactly "
            f"{QUIZ_NUM_QUESTIONS} multiple-choice questions that test understanding of that text. "
            "Return ONLY a JSON object with this exact shape, and nothing else:\n"
            '{"questions": [{"question": "Question text", '
            '"options": ["option 1", "option 2", "option 3", "option 4"], '
            '"answer": "the exact text of the correct option", '
            '"explanation": "one or two sentences on why it is correct", '
            '"topic": "a 1-3 word subject area, e.g. Physics"}]}\n'
            "Each question must have exactly 4 distinct options, and \"answer\" must be copied "
            "exactly from \"options\"."
        )
        truncated_text = document_text[:QUIZ_MAX_INPUT_CHARS]
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Document text:\n{truncated_text}\n\nGenerate the JSON quiz now."},
        ]

        raw = self._request_quiz(messages)
        try:
            return parse_quiz_payload(raw)
        except (QuizFormatError, json.JSONDecodeError) as e:
            logger.warning("Quiz output invalid, retrying once: %s", e)
            messages = messages + [
                {
                    "role": "user",
                    "content": f"Your previous output was invalid: {e}. Return only the JSON object.",
                },
            ]

        raw = self._request_quiz(messages)
        try:
            return parse_quiz_payload(raw)
        except (QuizFormatError, json.JSONDecodeError) as e:
            logger.warning("Quiz output invalid after retry: %s", e)
            raise QuizFormatError(f"Quiz generation failed after retry: {e}") from e

# Create a single instance
llm_service = LLMService()
