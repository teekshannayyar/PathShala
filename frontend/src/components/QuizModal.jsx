import React, { useState } from 'react';
import { X, CheckCircle, XCircle } from 'lucide-react';
import './QuizModal.css';

export default function QuizModal({ quizData, onClose }) {
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [isAnswerChecked, setIsAnswerChecked] = useState(false);
  const [score, setScore] = useState(0);
  const [quizFinished, setQuizFinished] = useState(false);

  const question = quizData[currentQuestionIdx];

  const handleOptionSelect = (opt) => {
    if (!isAnswerChecked) {
      setSelectedOption(opt);
    }
  };

  const checkAnswer = () => {
    if (!selectedOption) return;
    
    setIsAnswerChecked(true);
    if (selectedOption === question.answer) {
      setScore(prev => prev + 1);
    }
  };

  const nextQuestion = () => {
    if (currentQuestionIdx < quizData.length - 1) {
      setCurrentQuestionIdx(prev => prev + 1);
      setSelectedOption(null);
      setIsAnswerChecked(false);
    } else {
      setQuizFinished(true);
    }
  };

  return (
    <div className="quiz-modal-overlay animate-fade-in">
      <div className="quiz-modal glass animate-slide-up">
        <div className="quiz-header">
          <h2>Knowledge Check</h2>
          <button className="close-btn" onClick={onClose}><X size={20} /></button>
        </div>

        <div className="quiz-content">
          {quizFinished ? (
            <div className="quiz-results">
              <h3>Quiz Complete!</h3>
              <div className="score-display">
                <span className="score-number">{score}</span>
                <span className="score-total">/ {quizData.length}</span>
              </div>
              <p>You scored {Math.round((score / quizData.length) * 100)}%</p>
              <button className="quiz-btn primary" onClick={onClose}>Back to Study</button>
            </div>
          ) : (
            <div className="quiz-question-container">
              <div className="quiz-progress">Question {currentQuestionIdx + 1} of {quizData.length}</div>
              <h3 className="quiz-question">{question.question}</h3>
              
              <div className="quiz-options">
                {question.options.map((opt, idx) => {
                  let className = "quiz-option";
                  if (selectedOption === opt) className += " selected";
                  if (isAnswerChecked) {
                    if (opt === question.answer) className += " correct";
                    else if (selectedOption === opt && opt !== question.answer) className += " incorrect";
                  }
                  
                  return (
                    <button 
                      key={idx} 
                      className={className} 
                      onClick={() => handleOptionSelect(opt)}
                      disabled={isAnswerChecked}
                    >
                      {opt}
                      {isAnswerChecked && opt === question.answer && <CheckCircle size={18} className="icon-correct" />}
                      {isAnswerChecked && selectedOption === opt && opt !== question.answer && <XCircle size={18} className="icon-incorrect" />}
                    </button>
                  );
                })}
              </div>

              {isAnswerChecked && (
                <div className={`quiz-explanation ${selectedOption === question.answer ? 'correct-bg' : 'incorrect-bg'}`}>
                  <strong>{selectedOption === question.answer ? "Correct!" : "Incorrect."}</strong> {question.explanation}
                </div>
              )}
            </div>
          )}
        </div>

        {!quizFinished && (
          <div className="quiz-footer">
            {!isAnswerChecked ? (
              <button 
                className="quiz-btn primary" 
                disabled={!selectedOption} 
                onClick={checkAnswer}
              >
                Check Answer
              </button>
            ) : (
              <button 
                className="quiz-btn primary" 
                onClick={nextQuestion}
              >
                {currentQuestionIdx < quizData.length - 1 ? 'Next Question' : 'View Results'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
