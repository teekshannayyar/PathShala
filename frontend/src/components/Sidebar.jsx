import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { MessageSquare, Loader2, Trash2, PlusCircle, PanelLeftOpen } from 'lucide-react';
import { getDocuments, deleteDocument, errorMessage } from '../api';
import toast from 'react-hot-toast';
import './Sidebar.css';

export default function Sidebar({ activeDocument, setActiveDocument, onDocumentsLoaded, user, onLogout }) {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [dontAskAgain, setDontAskAgain] = useState(false);
  // Phones only: the sidebar is a drawer opened by a toggle (see Sidebar.css).
  const [isOpen, setIsOpen] = useState(false);

  const executeDeleteLogic = async (docId) => {
    try {
      await deleteDocument(docId);
      setDocuments(prevDocs => prevDocs.filter(d => d.id !== docId));
      if (activeDocument?.id === docId) {
        setActiveDocument(null);
      }
      toast.success("Chat deleted successfully");
    } catch (error) {
      toast.error(errorMessage(error, "Failed to delete chat"));
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
    // Load now, then poll every 5 s so processing status updates on its own.
    // State is only set after the await, and not at all once unmounted.
    let ignore = false;
    const loadDocuments = async () => {
      try {
        const docs = await getDocuments();
        if (!ignore) {
          setDocuments(docs);
          onDocumentsLoaded?.(docs);
        }
      } catch (error) {
        console.error("Failed to load documents", error);
      } finally {
        if (!ignore) setIsLoading(false);
      }
    };
    loadDocuments();
    const interval = setInterval(loadDocuments, 5000);
    return () => {
      ignore = true;
      clearInterval(interval);
    };
    // Reload when another document is opened, e.g. right after an upload.
  }, [activeDocument?.id, onDocumentsLoaded]);

  // setActiveDocument(null) also navigates to a fresh /chat.
  const handleNewChat = () => {
    setIsOpen(false);
    setActiveDocument(null);
  };

  return (
    <>
    <button className="sidebar-toggle" onClick={() => setIsOpen(true)} aria-label="Show chats" title="Show chats">
      <PanelLeftOpen size={20} />
    </button>
    {isOpen && <div className="sidebar-backdrop" onClick={() => setIsOpen(false)} />}
    <div className={`sidebar ${isOpen ? 'open' : ''}`}>
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
              onClick={() => { setActiveDocument(doc); setIsOpen(false); }}
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
    </>
  );
}
