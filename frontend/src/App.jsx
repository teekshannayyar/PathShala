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

// A message to show once after a full page load (e.g. after deleting the account).
const FLASH_KEY = 'pathshala:flash';
const popFlash = () => {
  try {
    const message = sessionStorage.getItem(FLASH_KEY);
    sessionStorage.removeItem(FLASH_KEY);
    return message;
  } catch {
    return null;
  }
};

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
  // Latest known copy of the document open in /chat. Which document is open
  // is decided only by the URL; this is just its data.
  const [documentCache, setDocumentCache] = useState(null);
  // Where the navbar's Chat link goes: the chat the user last opened.
  const [lastChatDocId, setLastChatDocId] = useState(null);
  const [user, setUser] = useState(null);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  // The URL (/chat?doc=<id>) is the single source of truth for the open
  // document, so reload, back/forward and links keep it, and changing it is
  // always a navigation (no state that can race React Router's URL update).
  const docParam = location.pathname === '/chat' ? new URLSearchParams(location.search).get('doc') : null;
  const wantedDocId = docParam && /^\d+$/.test(docParam) ? Number(docParam) : null;
  const chatDocument = wantedDocId !== null && documentCache?.id === wantedDocId ? documentCache : null;

  const openDocument = useCallback((doc, { replace = false } = {}) => {
    if (doc) setDocumentCache(doc);
    setLastChatDocId(doc ? doc.id : null);
    navigate(doc ? `/chat?doc=${doc.id}` : '/chat', { replace });
  }, [navigate]);

  // Called with every fresh documents list (the chat sidebar polls): keeps
  // the open document's status current. If it is gone, the cache is emptied
  // and the loader below reports it and returns to /chat.
  const handleDocumentsLoaded = useCallback((docs) => {
    setDocumentCache(prev => {
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
      setDocumentCache(null);
      setLastChatDocId(null);
      toast.error('Your session has expired. Please log in again.', { id: 'session-expired' });
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, []);

  // Load the document named in the URL when we don't have it yet (reload,
  // back/forward, shared link) or it disappeared from the list.
  const cachedId = documentCache?.id;
  useEffect(() => {
    if (!user || docParam === null || cachedId === wantedDocId) return;
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
        setDocumentCache(doc);
      } else {
        toast.error('That document no longer exists.', { id: 'doc-missing' });
        setLastChatDocId(null);
        navigate('/chat', { replace: true });
      }
    };
    loadWanted();
    return () => { ignore = true; };
  }, [user, docParam, wantedDocId, cachedId, navigate]);

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
    const flash = popFlash();
    if (flash) toast.success(flash, { id: 'flash' });
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

  // A full page load to the landing page: clearing the user first would let
  // the protected routes redirect to /login before the navigation lands.
  // `message` (optional) is shown as a toast after the reload.
  const handleLogout = (message) => {
    localStorage.removeItem('token');
    if (typeof message === 'string') {
      try { sessionStorage.setItem(FLASH_KEY, message); } catch { /* toast is optional */ }
    }
    window.location.assign('/');
  };

  const getAuthenticatedLayout = (children) => (
    <div className="app-layout">
      <Navbar
        onLogout={handleLogout}
        setActiveDocument={openDocument}
        chatPath={lastChatDocId !== null ? `/chat?doc=${lastChatDocId}` : '/chat'}
      />
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
      {/* Top-center, below the 64px navbar, so toasts never cover its buttons. */}
      <Toaster position="top-center" containerStyle={{ top: 76 }} toastOptions={{ duration: 4000 }} />
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
