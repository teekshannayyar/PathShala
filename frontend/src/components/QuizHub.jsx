import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Target, AlertTriangle, Play, BookOpen, Clock, CheckCircle2, ChevronRight, Loader2, BookA } from 'lucide-react';
import { getQuizzes, getWeakTopics, generateQuiz, getDocuments, errorMessage } from '../api';
import toast from 'react-hot-toast';
import './QuizHub.css';

export default function QuizHub() {
  const navigate = useNavigate();
  const location = useLocation();
  const [quizzes, setQuizzes] = useState([]);
  const [weakTopics, setWeakTopics] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [quizzesData, topicsData, docsData] = await Promise.all([
          getQuizzes(),
          getWeakTopics(),
          getDocuments()
        ]);
        setQuizzes(quizzesData);
        setWeakTopics(topicsData.weak_topics || []);
        
        // Only keep documents that finished processing successfully
        const readyDocs = docsData.filter(d => d.processing_status === 'ready');
        setDocuments(readyDocs);
        
        // Pre-select document if navigated with ?generate=docId, but don't auto-generate
        const params = new URLSearchParams(location.search);
        const generateId = params.get('generate');
        if (generateId) {
          setSelectedDocId(generateId);
        } else if (readyDocs.length > 0) {
          setSelectedDocId(readyDocs[0].id.toString());
        }

      } catch (error) {
        console.error("Failed to load quiz data", error);
        toast.error("Failed to load quiz dashboard");
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [location.search]);

  const handleGenerateNew = async (docIdToUse) => {
    const docId = docIdToUse || parseInt(selectedDocId);
    if (!docId) return toast.error("Please select a document first");

    setIsGenerating(true);
    toast.loading("AI is generating a new quiz...", { id: 'quiz' });
    try {
      const response = await generateQuiz(docId);
      toast.success("Quiz generated successfully!", { id: 'quiz' });
      // Redirect to the actual quiz taker
      navigate(`/quizzes/take/${response.quiz_id}`);
    } catch (error) {
      console.error(error);
      toast.error(errorMessage(error, "Failed to generate quiz"), { id: 'quiz' });
      setIsGenerating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="quiz-hub-container centered">
        <Loader2 size={48} className="spin text-accent" />
        <p>Loading Quiz Dashboard...</p>
      </div>
    );
  }

  return (
    <div className="quiz-hub-container animate-fade-in">
      <div className="quiz-header">
        <div>
          <h1>Knowledge Hub</h1>
          <p>Test your retention, track your progress, and master your weak spots.</p>
        </div>
        
        <div className="quiz-generate-card glass">
          <div className="generate-input-group">
            <select 
              value={selectedDocId} 
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="doc-select"
            >
              {documents.length === 0 && <option value="">No ready documents available</option>}
              {documents.map(doc => (
                <option key={doc.id} value={doc.id}>{doc.filename.replace('.pdf', '')}</option>
              ))}
            </select>
            <button 
              className="generate-btn" 
              disabled={isGenerating || !selectedDocId}
              onClick={() => handleGenerateNew(null)}
            >
              {isGenerating ? <Loader2 size={16} className="spin" /> : <Play size={16} />}
              Generate Quiz
            </button>
          </div>
        </div>
      </div>

      <div className="quiz-main-grid">
        {/* Left Column: Weak Topics & Stats */}
        <div className="quiz-col-left">
          <div className="quiz-panel glass analytics-panel">
            <div className="panel-header">
              <h3><Target size={18} /> Weak Topics to Review</h3>
            </div>
            <div className="topics-list">
              {weakTopics.length === 0 ? (
                <div className="empty-topics">
                  <CheckCircle2 size={32} className="success-icon" />
                  <p>You have no weak topics right now. Keep up the great work!</p>
                </div>
              ) : (
                weakTopics.map((topic, idx) => (
                  <div key={idx} className="topic-card">
                    <div className="topic-header">
                      <span className="topic-name">{topic.topic}</span>
                      <span className={`topic-accuracy ${topic.accuracy < 50 ? 'danger' : 'warning'}`}>
                        {topic.accuracy}% accuracy
                      </span>
                    </div>
                    <div className="topic-progress-bar">
                      <div 
                        className={`topic-progress-fill ${topic.accuracy < 50 ? 'danger-bg' : 'warning-bg'}`} 
                        style={{width: `${topic.accuracy}%`}}
                      ></div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Recent Quizzes */}
        <div className="quiz-col-right">
          <div className="section-header">
            <h3>Recent Quizzes</h3>
          </div>
          
          <div className="quizzes-grid">
            {quizzes.length === 0 ? (
              <div className="empty-state glass">
                <BookA size={48} className="empty-icon" />
                <h4>No quizzes yet</h4>
                <p>Select a document above and generate your first quiz!</p>
              </div>
            ) : (
              quizzes.map(quiz => (
                <div key={quiz.id} className="quiz-card glass">
                  <div className="quiz-card-header">
                    <h4>{quiz.title}</h4>
                    <span className="quiz-attempts">{quiz.attempts} attempts</span>
                  </div>
                  <div className="quiz-card-footer">
                    <span className="quiz-date">
                      <Clock size={12} /> 
                      {new Date(quiz.created_at).toLocaleDateString()}
                    </span>
                    <button 
                      className="take-quiz-btn"
                      onClick={() => navigate(`/quizzes/take/${quiz.id}`)}
                    >
                      Take Again <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
