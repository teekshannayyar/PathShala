import { useState, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
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

import { getCurrentUser } from './api';

function App() {
  const [activeDocument, setActiveDocument] = useState(null);
  const [user, setUser] = useState(null);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

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
      <Navbar onLogout={handleLogout} setActiveDocument={setActiveDocument} />
      <div className="app-main">
        {location.pathname === '/chat' && (
          <Sidebar 
            activeDocument={activeDocument} 
            setActiveDocument={setActiveDocument}
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
              <Dashboard 
                onDocumentSelect={(doc) => {
                  setActiveDocument(doc);
                  navigate('/chat');
                }}
              />
            ) : <Navigate to="/login" />
          } 
        />
        <Route 
          path="/chat" 
          element={
            user ? getAuthenticatedLayout(
              <ChatInterface 
                activeDocument={activeDocument} 
                setActiveDocument={setActiveDocument} 
              />
            ) : <Navigate to="/login" />
          } 
        />
        <Route 
          path="/documents" 
          element={
            user ? getAuthenticatedLayout(
              <DocumentManager 
                onDocumentSelect={(doc) => {
                  setActiveDocument(doc);
                  navigate('/chat');
                }}
              />
            ) : <Navigate to="/login" />
          } 
        />
        <Route 
          path="/settings" 
          element={
            user ? getAuthenticatedLayout(
              <ProfileSettings user={user} onLogout={handleLogout} />
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
      </Routes>
    </>
  );
}

export default App;
