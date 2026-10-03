import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { MessageSquare, Loader2, Trash2, PlusCircle } from 'lucide-react';
import { getDocuments, deleteDocument } from '../api';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import './Sidebar.css';

export default function Sidebar({ activeDocument, setActiveDocument, user, onLogout }) {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [dontAskAgain, setDontAskAgain] = useState(false);
  const navigate = useNavigate();

  const loadDocuments = async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (error) {
      console.error("Failed to load documents", error);
    } finally {
      setIsLoading(false);
    }
  };

  const executeDeleteLogic = async (docId) => {
    try {
      await deleteDocument(docId);
      setDocuments(prevDocs => prevDocs.filter(d => d.id !== docId));
      if (activeDocument?.id === docId) {
        setActiveDocument(null);
      }
      toast.success("Chat deleted successfully");
    } catch (err) {
      toast.error("Failed to delete chat");
    }
  };

  const confirmDelete = (e, docId) => {
    e.stopPropagation();
    const skipsLeft = parseInt(localStorage.getItem('skipDeleteConfirmCount') || '0', 10);
    if (skipsLeft > 0) {
      localStorage.setItem('skipDeleteConfirmCount', (skipsLeft - 1).toString());
      executeDeleteLogic(docId);
    } else {
      setDeleteConfirm(docId);
      setDontAskAgain(false);
    }
  };

  const handleModalConfirm = () => {
    if (!deleteConfirm) return;
    const docId = deleteConfirm;
    
    if (dontAskAgain) {
      localStorage.setItem('skipDeleteConfirmCount', '10');
    }

    setDeleteConfirm(null);
    executeDeleteLogic(docId);
  };

  useEffect(() => {
    loadDocuments();
    const interval = setInterval(loadDocuments, 5000);
    return () => clearInterval(interval);
  }, [activeDocument]);

  const handleNewChat = () => {
    setActiveDocument(null);
    navigate('/chat');
  };

  return (
    <div className="sidebar">
      <div className="sidebar-top-actions">
        <button className="new-chat-btn" onClick={handleNewChat}>
          <PlusCircle size={18} />
          <span>New Chat</span>
        </button>
      </div>

      <div className="doc-list">
        <h3 className="doc-list-title">Recent Chats</h3>
        {isLoading && documents.length === 0 ? (
          <div className="loading-chats"><Loader2 size={16} className="spin" /> Loading...</div>
        ) : documents.length === 0 ? (
          <div className="no-chats">No previous chats</div>
        ) : (
          documents.map((doc) => (
            <div 
              key={doc.id}
              className={`doc-item ${activeDocument?.id === doc.id ? 'active' : ''}`}
              onClick={() => setActiveDocument(doc)}
            >
              <MessageSquare size={16} className="doc-icon" />
              <div className="doc-info">
                <span className="doc-name">{doc.filename.replace('.pdf', '')}</span>
              </div>
              {doc.processing_status === 'failed' && (
                <span className="doc-failed-badge" title={doc.processing_error || 'Processing failed'}>
                  Failed
                </span>
              )}
              <button 
                className="delete-doc-btn" 
                onClick={(e) => confirmDelete(e, doc.id)}
                title="Delete Chat"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))
        )}
      </div>

      {user && (
        <div className="user-profile">
          {user.picture ? (
            <img src={user.picture} alt="Profile" className="user-avatar" />
          ) : (
            <div className="user-avatar-placeholder">{user.name?.charAt(0) || 'U'}</div>
          )}
          <div className="user-details">
            <span className="user-name">{user.name}</span>
            <button className="logout-btn" onClick={onLogout}>Sign Out</button>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {deleteConfirm && createPortal(
        <div className="confirm-modal-overlay">
          <div className="confirm-modal glass">
            <h3>Delete Chat?</h3>
            <p>Are you sure you want to delete this chat and its PDF? This cannot be undone.</p>
            
            <label className="dont-ask-label">
              <input 
                type="checkbox" 
                checked={dontAskAgain}
                onChange={(e) => setDontAskAgain(e.target.checked)}
              />
              Don't ask me again for the next 10 deletes
            </label>

            <div className="confirm-modal-actions">
              <button className="cancel-btn" onClick={() => setDeleteConfirm(null)}>Cancel</button>
              <button className="confirm-delete-btn" onClick={handleModalConfirm}>Delete</button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
