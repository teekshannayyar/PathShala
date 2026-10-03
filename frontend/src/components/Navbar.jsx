import { useRef, useState } from 'react';
import { Plus, Settings, LogOut, BookOpen, Loader2, Menu, X } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { uploadDocument, errorMessage } from '../api';
import toast from 'react-hot-toast';
import './Navbar.css';

const MAX_UPLOAD_MB = 50;

export default function Navbar({ onLogout, setActiveDocument, chatPath = '/chat' }) {
  const navigate = useNavigate();
  const location = useLocation();
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  // Phones only: the links collapse into a menu behind a toggle (see Navbar.css).
  const [menuOpen, setMenuOpen] = useState(false);

  const handleNewChat = () => {
    // Instead of just navigating, we can directly prompt for a file upload
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      toast.error(`File is too large! Please upload a PDF smaller than ${MAX_UPLOAD_MB}MB.`);
      return;
    }

    setIsUploading(true);
    toast.loading("Uploading and processing PDF...", { id: 'upload' });
    try {
      const newDoc = await uploadDocument(file);
      // Opens the new document in /chat.
      setActiveDocument(newDoc);
      toast.success("PDF uploaded successfully!", { id: 'upload' });
    } catch (error) {
      console.error("Upload failed", error);
      toast.error(errorMessage(error, "Failed to upload document"), { id: 'upload' });
    } finally {
      setIsUploading(false);
      if (e.target) e.target.value = null;
    }
  };

  return (
    <>
      <nav className={`top-navbar glass ${menuOpen ? 'menu-open' : ''}`}>
        <div className="navbar-brand" onClick={() => { setMenuOpen(false); navigate('/dashboard'); }}>
          <BookOpen size={24} className="brand-icon" />
          <h2>PathShala</h2>
        </div>

        <button
          className="nav-menu-toggle"
          onClick={() => setMenuOpen(open => !open)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>

        {/* Any button pressed in the menu also closes it. */}
        <div className="navbar-right" onClick={(e) => { if (e.target.closest('button')) setMenuOpen(false); }}>
          <div className="navbar-links">
            <button 
              className={`nav-link ${location.pathname === '/dashboard' ? 'active' : ''}`}
              onClick={() => navigate('/dashboard')}
            >
              Dashboard
            </button>
            <button 
              className={`nav-link ${location.pathname === '/documents' ? 'active' : ''}`}
              onClick={() => navigate('/documents')}
            >
              Documents
            </button>
            <button 
              className={`nav-link ${location.pathname === '/chat' ? 'active' : ''}`}
              onClick={() => navigate(chatPath)}
            >
              Chat
            </button>
            <button 
              className={`nav-link ${location.pathname.startsWith('/quizzes') ? 'active' : ''}`}
              onClick={() => navigate('/quizzes')}
            >
              Quizzes
            </button>
          </div>

          <div className="navbar-divider"></div>

          <input 
            type="file" 
            accept=".pdf" 
            ref={fileInputRef} 
            style={{ display: 'none' }} 
            onChange={handleFileChange}
          />

          <button className="nav-new-chat-btn" onClick={handleNewChat} disabled={isUploading}>
            {isUploading ? <Loader2 size={16} className="spin" /> : <Plus size={16} />}
            {isUploading ? 'Uploading...' : 'Add'}
          </button>

          <button 
            className={`nav-icon-btn ${location.pathname === '/settings' ? 'active' : ''}`} 
            onClick={() => navigate('/settings')} 
            title="Settings"
          >
            <Settings size={20} />
          </button>

          <button className="nav-icon-btn" onClick={onLogout} title="Logout">
            <LogOut size={20} />
          </button>
        </div>
      </nav>
      {menuOpen && <div className="nav-menu-backdrop" onClick={() => setMenuOpen(false)} />}
    </>
  );
}
