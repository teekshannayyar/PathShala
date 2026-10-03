import json

import pytest

from app.services.quiz_parser import QUIZ_MIN_VALID, QuizFormatError, parse_quiz_payload


def item(i=0, **overrides):
    base = {
        "question": f"Q{i}?",
        "options": [f"a{i}", f"b{i}", f"c{i}", f"d{i}"],
        "answer": f"b{i}",
        "explanation": "why",
        "topic": "Physics",
    }
    base.update(overrides)
    return base


def payload(items):
    return json.dumps({"questions": items})


def test_valid_ten_questions():
    result = parse_quiz_payload(payload([item(i) for i in range(10)]))
    assert len(result) == 10
    assert result[0] == {
        "question": "Q0?",
        "options": ["a0", "b0", "c0", "d0"],
        "answer": "b0",
        "topic": "Physics",
        "explanation": "why",
    }


def test_caps_at_ten():
    assert len(parse_quiz_payload(payload([item(i) for i in range(12)]))) == 10


def test_letter_answer_maps_to_option():
    result = parse_quiz_payload(payload([item(i, answer="c") for i in range(8)]))
    assert result[0]["answer"] == "c0"


def test_options_and_question_are_stripped():
    items = [item(i, question=f"  Q{i}?  ", options=[f" a{i} ", f"b{i}", f"c{i}", f"d{i}"], answer=f"a{i}") for i in range(8)]
    result = parse_quiz_payload(payload(items))
    assert result[0]["question"] == "Q0?"
    assert result[0]["options"][0] == "a0"
    assert result[0]["answer"] == "a0"


def test_missing_topic_defaults_to_general_and_explanation_optional():
    items = [item(i) for i in range(8)]
    for it in items:
        del it["topic"]
        del it["explanation"]
    result = parse_quiz_payload(payload(items))
    assert result[0]["topic"] == "General"
    assert result[0]["explanation"] is None


@pytest.mark.parametrize(
    "bad",
    [
        {"question": ""},
        {"question": 5},
        {"options": ["a", "b", "c"]},
        {"options": ["a", "a", "c", "d"], "answer": "a"},
        {"options": ["a", "", "c", "d"], "answer": "a"},
        {"answer": "not an option"},
        {"answer": "E"},
        {"topic": "x" * 101},
        {"explanation": 42},
    ],
)
def test_invalid_items_are_dropped(bad):
    items = [item(i) for i in range(QUIZ_MIN_VALID)] + [item(99, **bad)]
    result = parse_quiz_payload(payload(items))
    assert len(result) == QUIZ_MIN_VALID
    assert all(q["question"] != "Q99?" for q in result)


def test_too_few_valid_questions_raises():
    with pytest.raises(QuizFormatError):
        parse_quiz_payload(payload([item(i) for i in range(QUIZ_MIN_VALID - 1)]))


@pytest.mark.parametrize("raw", ['[{"question": "x"}]', '{"items": []}', '{"questions": "nope"}'])
def test_wrong_top_level_shape_raises(raw):
    with pytest.raises(QuizFormatError):
        parse_quiz_payload(raw)


def test_non_json_raises_decode_error():
    with pytest.raises(json.JSONDecodeError):
        parse_quiz_payload("Here is your quiz: ...")
