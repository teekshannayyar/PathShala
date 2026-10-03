import React, { useState, useEffect } from 'react';
import { BookOpen, FileText, MessageSquare, Zap, Clock, ChevronRight, UploadCloud, Sparkles, TrendingUp } from 'lucide-react';
import { getDocuments, getUserStats } from '../api';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

export default function Dashboard({ onDocumentSelect }) {
  const [documents, setDocuments] = useState([]);
  const [userStats, setUserStats] = useState({
    total_documents: 0,
    active_chats: 0,
    current_streak: 0,
    highest_streak: 0
  });
  const navigate = useNavigate();

  useEffect(() => {
    getDocuments().then(docs => setDocuments(docs)).catch(err => console.error(err));
    getUserStats().then(stats => setUserStats(stats)).catch(err => console.error(err));
  }, []);

  const handleNewUploadClick = () => {
    onDocumentSelect(null);
    navigate('/chat');
  };

  return (
    <div className="dashboard-container animate-fade-in">
      <div className="dashboard-header">
        <h1>Welcome back! 👋</h1>
        <p>Here's a summary of your recent study materials and activity.</p>
      </div>

      {/* Top Stats Cards */}
      <div className="dashboard-stats-grid">
        <div className="stat-card glass">
          <div className="stat-header">
            <span className="stat-title">Documents Analyzed</span>
            <div className="stat-icon-box"><FileText size={18} /></div>
          </div>
          <div className="stat-value">{userStats.total_documents}</div>
          <div className="stat-footer">Ready in your library</div>
        </div>

        <div className="stat-card glass">
          <div className="stat-header">
            <span className="stat-title">Active Chats</span>
            <div className="stat-icon-box"><MessageSquare size={18} /></div>
          </div>
          <div className="stat-value">{userStats.active_chats}</div>
          <div className="stat-footer">Processed and ready</div>
        </div>

        <div className="stat-card glass">
          <div className="stat-header">
            <span className="stat-title">Study Streak</span>
            <div className="stat-icon-box"><Zap size={18} /></div>
          </div>
          <div className="stat-value">{userStats.current_streak} <span style={{fontSize: '20px'}}>Days</span></div>
          <div className="stat-footer" style={{display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-primary)'}}>
            <TrendingUp size={14} /> Highest Streak: {userStats.highest_streak}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="dashboard-main-grid">
        {/* Left Column: Recent Documents as Grid */}
        <div className="dashboard-col lg-col">
          <div className="section-header">
            <h3>Recent Documents</h3>
            <button className="view-all-btn" onClick={() => navigate('/documents')}>View all <ChevronRight size={14}/></button>
          </div>
          
          <div className="docs-grid">
            {documents && documents.length > 0 ? (
              documents.slice(0, 6).map(doc => (
                <div 
                  key={doc.id} 
                  className="doc-card glass"
                  onClick={() => onDocumentSelect && onDocumentSelect(doc)}
                >
                  <div className="doc-card-icon">
                    <FileText size={24} />
                  </div>
                  <div className="doc-card-info">
                    <span className="doc-name" title={doc.filename}>{doc.filename.replace('.pdf', '')}</span>
                    <span className="doc-status">
                      {doc.embedding_complete ? (
                        <><span className="status-dot ready"></span> Ready to chat</>
                      ) : (
                        <><span className="status-dot processing"></span> Processing...</>
                      )}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state glass">
                <UploadCloud size={48} className="empty-icon" />
                <h4>No documents yet</h4>
                <p>Upload a PDF to start asking questions and generating insights.</p>
                <button className="upload-prompt-btn" onClick={handleNewUploadClick}>
                  Upload PDF
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Quick Start */}
        <div className="dashboard-col sm-col">
          <div className="dashboard-panel glass quick-start-panel">
            <div className="panel-header">
              <h3>Quick Start</h3>
              <Sparkles size={16} className="panel-icon accent" />
            </div>
            
            <div className="quick-actions">
              <button className="action-btn" onClick={handleNewUploadClick}>
                <div className="action-icon"><UploadCloud size={18} /></div>
                <div className="action-text">
                  <span className="action-title">Analyze new PDF</span>
                  <span className="action-desc">Upload and extract insights</span>
                </div>
              </button>

              {documents && documents.length > 0 && documents[0].embedding_complete && (
                <button className="action-btn" onClick={() => onDocumentSelect(documents[0])}>
                  <div className="action-icon"><MessageSquare size={18} /></div>
                  <div className="action-text">
                    <span className="action-title">Continue Chat</span>
                    <span className="action-desc">{documents[0].filename.replace('.pdf', '')}</span>
                  </div>
                </button>
              )}
            </div>
            
            <div className="learning-tip">
              <div className="tip-header">
                <Clock size={14} /> <span>Pro Tip</span>
              </div>
              <p>Ask PathShala to "summarize the key points" of any document to quickly grasp the core concepts.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
