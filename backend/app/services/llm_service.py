from groq import Groq
from app.core.config import settings
from typing import List, Dict

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

    def generate_quiz(self, document_text: str) -> str:
        """Generates a multiple choice quiz based on the document text, strictly returning JSON."""
        system_prompt = (
            "You are a quiz generator. Based on the provided document text, create a 5-question multiple-choice quiz. "
            "You MUST return ONLY a valid JSON array of objects, with no markdown formatting, no backticks, and no introductory text. "
            "Each object must have the following structure: "
            "{ 'question': 'Question text', 'options': ['A', 'B', 'C', 'D'], 'answer': 'The exact string from options that is correct', 'explanation': 'Short explanation', 'topic': 'A 1-3 word broad subject area for this question (e.g. Physics, History, Database)' }"
        )
        
        # We might want to truncate document_text if it's too long, but we'll let Groq handle reasonable sizes.
        truncated_text = document_text[:15000] if document_text else "No content."
        user_prompt = f"Document text:\n{truncated_text}\n\nGenerate the JSON quiz now."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        chat_completion = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            temperature=0.4,
            # response_format={"type": "json_object"} # Groq supports json mode on some models, but plain prompting usually works fine too
        )
        
        return chat_completion.choices[0].message.content

# Create a single instance
llm_service = LLMService()
