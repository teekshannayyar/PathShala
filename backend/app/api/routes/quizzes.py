from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import json
import logging
import os

from app.api.deps import get_owned_document
from app.models.database import get_db
from app.models.models import Quiz, Question, QuizAttempt, QuestionAttempt
from app.api.routes.auth import get_current_user
from app.services.llm_service import LLMService, get_llm_service
from app.services.quiz_parser import QuizFormatError

logger = logging.getLogger(__name__)

router = APIRouter()

class QuizGenerationResponse(BaseModel):
    quiz_id: int
    title: str

class SubmitAnswerRequest(BaseModel):
    question_id: int
    user_answer: str

class SubmitQuizRequest(BaseModel):
    answers: List[SubmitAnswerRequest]

@router.post("/generate/{document_id}", response_model=QuizGenerationResponse)
def generate_and_save_quiz(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
    llm_service: LLMService = Depends(get_llm_service),
):
    doc = get_owned_document(db, document_id, current_user)

    if doc.processing_status == "processing":
        raise HTTPException(status_code=409, detail="Document is still processing")
    if doc.processing_status == "failed" or not (doc.original_text or "").strip():
        raise HTTPException(status_code=422, detail="Document has no extracted text; try reprocessing")

    text = doc.summary or doc.original_text

    try:
        questions = llm_service.generate_quiz(text)
    except QuizFormatError:
        raise HTTPException(status_code=502, detail="Quiz generation failed, please try again")
    except Exception:
        logger.exception("Quiz generation failed for document %s", document_id)
        raise HTTPException(status_code=502, detail="Quiz generation failed, please try again")

    # Save the quiz and all of its questions in one transaction.
    try:
        new_quiz = Quiz(
            document_id=doc.id,
            user_id=current_user,
            title=os.path.splitext(doc.filename)[0],
        )
        db.add(new_quiz)
        db.flush()

        for q in questions:
            db.add(Question(
                quiz_id=new_quiz.id,
                text=q["question"],
                options=json.dumps(q["options"]),
                correct_answer=q["answer"],
                topic=q["topic"],
            ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to save quiz for document %s", document_id)
        raise HTTPException(status_code=500, detail="Could not save quiz")

    return {"quiz_id": new_quiz.id, "title": new_quiz.title}

@router.get("/")
def get_all_quizzes(db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    quizzes = db.query(Quiz).filter(Quiz.user_id == current_user).order_by(Quiz.created_at.desc()).all()
    results = []
    for q in quizzes:
        results.append({
            "id": q.id,
            "title": q.title,
            "created_at": q.created_at,
            "document_id": q.document_id,
            "attempts": db.query(QuizAttempt).filter(QuizAttempt.quiz_id == q.id).count()
        })
    return results

@router.get("/{quiz_id}")
def get_quiz(quiz_id: int, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == current_user).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
        
    questions = db.query(Question).filter(Question.quiz_id == quiz_id).all()
    
    q_data = []
    for q in questions:
        q_data.append({
            "id": q.id,
            "text": q.text,
            "options": json.loads(q.options),
            "topic": q.topic
            # Not sending correct_answer to the client!
        })
        
    return {
        "id": quiz.id,
        "title": quiz.title,
        "questions": q_data
    }

@router.post("/{quiz_id}/submit")
def submit_quiz(quiz_id: int, request: SubmitQuizRequest, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == current_user).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
        
    questions = db.query(Question).filter(Question.quiz_id == quiz_id).all()
    question_map = {q.id: q for q in questions}
    
    correct_count = 0
    total_questions = len(questions)
    
    # Create attempt
    attempt = QuizAttempt(quiz_id=quiz_id, user_id=current_user, score=0, total_questions=total_questions)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    
    results = []
    
    for ans in request.answers:
        q = question_map.get(ans.question_id)
        if not q: continue
        
        is_correct = (q.correct_answer == ans.user_answer)
        if is_correct:
            correct_count += 1
            
        q_attempt = QuestionAttempt(
            attempt_id=attempt.id,
            question_id=q.id,
            user_answer=ans.user_answer,
            is_correct=is_correct
        )
        db.add(q_attempt)
        
        results.append({
            "question_id": q.id,
            "is_correct": is_correct,
            "correct_answer": q.correct_answer,
            "explanation": f"The correct answer was {q.correct_answer}."
        })
        
    attempt.score = correct_count
    db.commit()
    
    # Also record ActivityLog for streak
    from app.models.models import ActivityLog
    import datetime
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    if not db.query(ActivityLog).filter(ActivityLog.user_id == current_user, ActivityLog.date_string == today_str).first():
        db.add(ActivityLog(user_id=current_user, date_string=today_str))
        db.commit()
        
    return {
        "attempt_id": attempt.id,
        "score": correct_count,
        "total": total_questions,
        "results": results
    }

@router.get("/analytics/weak-topics")
def get_weak_topics(db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    # Get all question attempts for this user
    attempts = db.query(QuestionAttempt, Question.topic).join(Question).join(QuizAttempt).filter(QuizAttempt.user_id == current_user).all()
    
    topic_stats = {}
    for qa, topic in attempts:
        if topic not in topic_stats:
            topic_stats[topic] = {"correct": 0, "total": 0}
        
        topic_stats[topic]["total"] += 1
        if qa.is_correct:
            topic_stats[topic]["correct"] += 1
            
    weak_topics = []
    for topic, stats in topic_stats.items():
        if stats["total"] > 0:
            accuracy = (stats["correct"] / stats["total"]) * 100
            if accuracy < 60: # Threshold for "weak"
                weak_topics.append({
                    "topic": topic,
                    "accuracy": round(accuracy, 1),
                    "total_questions": stats["total"]
                })
                
    weak_topics.sort(key=lambda x: x["accuracy"])
    return {"weak_topics": weak_topics}
