import { useState, useEffect, useCallback } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import { Routes, Route, Navigate, Link, useNavigate, useLocation } from 'react-router-dom';
import './App.css';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import Auth from './components/Auth';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';
import Navbar from './components/Navbar';
import ProfileSettings from './components/ProfileSettings';
import QuizHub from './components/QuizHub';
import QuizTaker from './components/QuizTaker';
import DocumentManager from './components/DocumentManager';

import { getCurrentUser, getDocuments, SESSION_EXPIRED_EVENT } from './api';

const sameDocument = (a, b) => JSON.stringify(a) === JSON.stringify(b);

function NotFound({ isLoggedIn }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: '12px', minHeight: '100vh', padding: '16px', textAlign: 'center', background: 'var(--bg-primary)' }}>
      <h1 style={{ margin: 0 }}>Page not found</h1>
      <p style={{ margin: 0, color: 'var(--text-secondary)' }}>The page you are looking for does not exist.</p>
      <Link to={isLoggedIn ? '/dashboard' : '/'} style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>
        {isLoggedIn ? 'Go to your dashboard' : 'Go to the home page'}
      </Link>
    </div>
  );
}

function App() {
  const [activeDocument, setActiveDocument] = useState(null);
  const [user, setUser] = useState(null);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  // On /chat the URL (?doc=<id>) says which document is open, so a reload
  // keeps it. activeDocument holds the latest copy of that document.
  const docParam = location.pathname === '/chat' ? new URLSearchParams(location.search).get('doc') : null;
  const wantedDocId = docParam && /^\d+$/.test(docParam) ? Number(docParam) : null;
  const chatDocument = wantedDocId !== null && activeDocument?.id === wantedDocId ? activeDocument : null;

  const openDocument = useCallback((doc) => {
    setActiveDocument(doc);
    navigate(doc ? `/chat?doc=${doc.id}` : '/chat');
  }, [navigate]);

  // Called with every fresh documents list (the chat sidebar polls): keeps
  // the open document's status current and drops it if it was deleted.
  const handleDocumentsLoaded = useCallback((docs) => {
    setActiveDocument(prev => {
      if (!prev) return prev;
      const fresh = docs.find(d => d.id === prev.id);
      if (!fresh) return null;
      return sameDocument(prev, fresh) ? prev : fresh;
    });
  }, []);

  // Any 401 outside login/register means the session is over.
  useEffect(() => {
    const onExpired = () => {
      setUser(null);
      setActiveDocument(null);
      toast.error('Your session has expired. Please log in again.', { id: 'session-expired' });
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, []);

  // Load the document named in the URL (reload, back/forward, shared link).
  const activeId = activeDocument?.id;
  useEffect(() => {
    if (!user || location.pathname !== '/chat') return;
    if (docParam === null) {
      // Coming back to /chat with a document open: put it in the URL.
      if (activeId !== undefined) navigate(`/chat?doc=${activeId}`, { replace: true });
      return;
    }
    if (wantedDocId !== null && activeId === wantedDocId) return;
    let ignore = false;
    const loadWanted = async () => {
      let doc;
      try {
        doc = wantedDocId === null ? undefined : (await getDocuments()).find(d => d.id === wantedDocId);
      } catch (error) {
        console.error("Failed to load document", error);
        return;
      }
      if (ignore) return;
      if (doc) {
        setActiveDocument(doc);
      } else {
        toast.error('That document no longer exists.', { id: 'doc-missing' });
        setActiveDocument(null);
        navigate('/chat', { replace: true });
      }
    };
    loadWanted();
    return () => { ignore = true; };
  }, [user, location.pathname, docParam, wantedDocId, activeId, navigate]);

  // On mount, check if token exists to restore session
  useEffect(() => {
    // Runs once on mount; the token is the only input. State is only set
    // after the await, and not at all once unmounted.
    let ignore = false;
    const validateSession = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const userData = await getCurrentUser();
          if (!ignore) setUser(userData);
        } catch (error) {
          console.error("Token validation failed:", error);
          localStorage.removeItem('token');
        }
      }
      if (!ignore) setIsLoadingAuth(false);
    };

    validateSession();
    return () => { ignore = true; };
  }, []);

  if (isLoadingAuth) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'var(--bg-primary)' }}>Loading PathShala...</div>;
  }

  const handleLogin = (userData, token) => {
    setUser(userData);
    localStorage.setItem('token', token);
    navigate('/chat');
  };

  const handleLogout = () => {
    setUser(null);
    setActiveDocument(null);
    localStorage.removeItem('token');
    navigate('/');
  };

  const getAuthenticatedLayout = (children) => (
    <div className="app-layout">
      <Navbar onLogout={handleLogout} setActiveDocument={openDocument} />
      <div className="app-main">
        {location.pathname === '/chat' && (
          <Sidebar 
            activeDocument={chatDocument} 
            setActiveDocument={openDocument}
            onDocumentsLoaded={handleDocumentsLoaded}
            user={user}
            onLogout={handleLogout}
          />
        )}
        {children}
      </div>
    </div>
  );

  return (
    <>
      <Toaster position="top-right" />
      <Routes>
        <Route 
          path="/" 
          element={!user ? <LandingPage onLogin={() => navigate('/login')} onSignup={() => navigate('/signup')} /> : <Navigate to="/chat" />} 
        />
        <Route 
          path="/login" 
          element={!user ? <Auth onLogin={handleLogin} defaultIsLogin={true} /> : <Navigate to="/chat" />} 
        />
        <Route 
          path="/signup" 
          element={!user ? <Auth onLogin={handleLogin} defaultIsLogin={false} /> : <Navigate to="/chat" />} 
        />
        <Route 
          path="/dashboard" 
          element={
            user ? getAuthenticatedLayout(
              <Dashboard onDocumentSelect={openDocument} />
            ) : <Navigate to="/login" />
          } 
        />
        <Route 
          path="/chat" 
          element={
            user ? getAuthenticatedLayout(
              <ChatInterface 
                activeDocument={chatDocument} 
                setActiveDocument={openDocument} 
              />
            ) : <Navigate to="/login" />
          } 
        />
        <Route 
          path="/documents" 
          element={
            user ? getAuthenticatedLayout(
              <DocumentManager onDocumentSelect={openDocument} />
            ) : <Navigate to="/login" />
          } 
        />
        <Route 
          path="/settings" 
          element={
            user ? getAuthenticatedLayout(
              <ProfileSettings user={user} onUserUpdate={setUser} onLogout={handleLogout} />
            ) : <Navigate to="/login" />
          } 
        />
        <Route 
          path="/quizzes" 
          element={
            user ? getAuthenticatedLayout(
              <QuizHub />
            ) : <Navigate to="/login" />
          } 
        />
        <Route 
          path="/quizzes/take/:id" 
          element={
            user ? getAuthenticatedLayout(
              <QuizTaker />
            ) : <Navigate to="/login" />
          } 
        />
        <Route path="*" element={<NotFound isLoggedIn={Boolean(user)} />} />
      </Routes>
    </>
  );
}

export default App;
