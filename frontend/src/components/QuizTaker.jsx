import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getQuiz, submitQuiz } from '../api';
import { Loader2, ArrowLeft, CheckCircle2, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import './QuizTaker.css';

export default function QuizTaker() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [quiz, setQuiz] = useState(null);
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [userAnswers, setUserAnswers] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [results, setResults] = useState(null);

  useEffect(() => {
    const fetchQuiz = async () => {
      try {
        const data = await getQuiz(id);
        setQuiz(data);
      } catch (error) {
        console.error("Failed to load quiz", error);
        toast.error("Failed to load quiz");
        navigate('/quizzes');
      } finally {
        setIsLoading(false);
      }
    };
    fetchQuiz();
  }, [id, navigate]);

  const handleSelectOption = (option) => {
    if (results) return; // Prevent changing answers after submission
    setUserAnswers(prev => ({
      ...prev,
      [quiz.questions[currentQuestionIdx].id]: option
    }));
  };

  const handleNext = () => {
    if (currentQuestionIdx < quiz.questions.length - 1) {
      setCurrentQuestionIdx(prev => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentQuestionIdx > 0) {
      setCurrentQuestionIdx(prev => prev - 1);
    }
  };

  const handleSubmit = async () => {
    const formattedAnswers = Object.entries(userAnswers).map(([qId, ans]) => ({
      question_id: parseInt(qId),
      user_answer: ans
    }));

    setIsSubmitting(true);
    toast.loading("Grading quiz...", { id: 'submit' });
    try {
      const resultData = await submitQuiz(id, formattedAnswers);
      setResults(resultData);
      toast.success("Quiz graded!", { id: 'submit' });
    } catch (error) {
      console.error(error);
      toast.error("Failed to submit quiz", { id: 'submit' });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="quiz-taker-container centered">
        <Loader2 size={48} className="spin text-accent" />
        <p>Loading Quiz...</p>
      </div>
    );
  }

  if (!quiz) return null;

  // Render Results View
  if (results) {
    const percentage = Math.round((results.score / results.total) * 100);
    return (
      <div className="quiz-taker-container animate-fade-in">
        <div className="quiz-results-header glass">
          <h1>Quiz Complete!</h1>
          <div className="score-circle">
            <svg viewBox="0 0 36 36" className="circular-chart orange">
              <path className="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              <path className="circle" strokeDasharray={`${percentage}, 100`} d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              <text x="18" y="20.35" className="percentage">{percentage}%</text>
            </svg>
          </div>
          <p>You scored {results.score} out of {results.total}.</p>
          <button className="btn-primary" onClick={() => navigate('/quizzes')}>Return to Quiz Hub</button>
        </div>

        <div className="quiz-results-details">
          <h3>Question Review</h3>
          {quiz.questions.map((q, idx) => {
            const res = results.results.find(r => r.question_id === q.id);
            const userAns = userAnswers[q.id];
            
            return (
              <div key={q.id} className={`result-card glass ${res?.is_correct ? 'correct' : 'incorrect'}`}>
                <div className="result-card-header">
                  <h4>Question {idx + 1}</h4>
                  {res?.is_correct ? <CheckCircle2 className="text-success" /> : <XCircle className="text-danger" />}
                </div>
                <p className="q-text">{q.text}</p>
                <div className="res-options">
                  {q.options.map((opt, i) => {
                    let className = "res-opt";
                    if (opt === res?.correct_answer) className += " correct-ans";
                    else if (opt === userAns && !res?.is_correct) className += " wrong-ans";
                    
                    return (
                      <div key={i} className={className}>
                        {opt}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Render Quiz Taking View
  const currentQ = quiz.questions[currentQuestionIdx];
  const isLastQuestion = currentQuestionIdx === quiz.questions.length - 1;
  const progress = ((currentQuestionIdx + 1) / quiz.questions.length) * 100;

  return (
    <div className="quiz-taker-container animate-fade-in">
      <div className="quiz-taker-header">
        <button className="back-btn" onClick={() => navigate('/quizzes')}>
          <ArrowLeft size={18} /> Exit
        </button>
        <h2>{quiz.title}</h2>
        <span className="q-count">{currentQuestionIdx + 1} of {quiz.questions.length}</span>
      </div>

      <div className="progress-bar-container">
        <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
      </div>

      <div className="question-card glass animate-slide-up" key={currentQ.id}>
        <div className="question-topic">{currentQ.topic}</div>
        <h3 className="question-text">{currentQ.text}</h3>
        
        <div className="options-grid">
          {currentQ.options.map((option, idx) => {
            const isSelected = userAnswers[currentQ.id] === option;
            return (
              <div 
                key={idx} 
                className={`option-btn ${isSelected ? 'selected' : ''}`}
                onClick={() => handleSelectOption(option)}
              >
                <div className="option-marker">{String.fromCharCode(65 + idx)}</div>
                <div className="option-text">{option}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="quiz-taker-footer">
        <button 
          className="nav-btn prev" 
          disabled={currentQuestionIdx === 0} 
          onClick={handlePrev}
        >
          Previous
        </button>
        
        {isLastQuestion ? (
          <button 
            className="btn-primary submit-btn" 
            disabled={Object.keys(userAnswers).length !== quiz.questions.length || isSubmitting}
            onClick={handleSubmit}
          >
            {isSubmitting ? <Loader2 size={18} className="spin" /> : "Submit Quiz"}
          </button>
        ) : (
          <button 
            className="nav-btn next" 
            onClick={handleNext}
          >
            Next
          </button>
        )}
      </div>
    </div>
  );
}
