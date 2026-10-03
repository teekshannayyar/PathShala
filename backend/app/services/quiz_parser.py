"""Validate and normalise the quiz JSON returned by the LLM."""
import json
from typing import Any, Optional

QUIZ_NUM_QUESTIONS = 10
QUIZ_MIN_VALID = 8

NUM_OPTIONS = 4
# Answers are stored in String(255) columns (questions.correct_answer,
# question_attempts.user_answer), so longer options can't be saved.
MAX_OPTION_LENGTH = 255
MAX_TOPIC_LENGTH = 100
DEFAULT_TOPIC = "General"
LETTER_ANSWERS = "ABCD"


class QuizFormatError(ValueError):
    """The LLM output is not a usable quiz."""


def _parse_options(raw: Any) -> Optional[list[str]]:
    if not isinstance(raw, list) or len(raw) != NUM_OPTIONS:
        return None
    options = []
    for opt in raw:
        if not isinstance(opt, str):
            return None
        opt = opt.strip()
        if not opt or len(opt) > MAX_OPTION_LENGTH:
            return None
        options.append(opt)
    if len(set(options)) != NUM_OPTIONS:
        return None
    return options


def _parse_answer(raw: Any, options: list[str]) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    answer = raw.strip()
    if answer in options:
        return answer
    # Accept a bare letter ("B", "b") as an index into the options.
    if len(answer) == 1 and answer.upper() in LETTER_ANSWERS:
        return options[LETTER_ANSWERS.index(answer.upper())]
    return None


def _parse_item(item: Any) -> Optional[dict]:
    if not isinstance(item, dict):
        return None

    question = item.get("question")
    if not isinstance(question, str) or not question.strip():
        return None

    options = _parse_options(item.get("options"))
    if options is None:
        return None

    answer = _parse_answer(item.get("answer"), options)
    if answer is None:
        return None

    topic = item.get("topic", DEFAULT_TOPIC)
    if topic is None:
        topic = DEFAULT_TOPIC
    if not isinstance(topic, str) or len(topic.strip()) > MAX_TOPIC_LENGTH:
        return None
    topic = topic.strip() or DEFAULT_TOPIC

    explanation = item.get("explanation")
    if explanation is not None and not isinstance(explanation, str):
        return None

    return {
        "question": question.strip(),
        "options": options,
        "answer": answer,
        "topic": topic,
        "explanation": explanation.strip() if explanation else None,
    }


def parse_quiz_payload(raw: str) -> list[dict]:
    """Parse the LLM's JSON reply into a list of validated questions.

    Raises json.JSONDecodeError if raw isn't JSON, and QuizFormatError if the
    structure is wrong or fewer than QUIZ_MIN_VALID questions are usable.
    """
    data = json.loads(raw)

    if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
        raise QuizFormatError('Expected a JSON object with a "questions" list')

    questions = []
    for item in data["questions"]:
        parsed = _parse_item(item)
        if parsed is not None:
            questions.append(parsed)

    questions = questions[:QUIZ_NUM_QUESTIONS]
    if len(questions) < QUIZ_MIN_VALID:
        raise QuizFormatError(
            f"Only {len(questions)} valid questions; need at least {QUIZ_MIN_VALID}"
        )
    return questions
