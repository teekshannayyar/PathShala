import React from 'react';
import { BookOpen, Zap, Shield, Sparkles, ArrowRight, BrainCircuit, MessageSquare, Clock } from 'lucide-react';
import './LandingPage.css';

export default function LandingPage({ onLogin, onSignup }) {
  return (
    <div className="landing-container">
      {/* Navigation */}
      <nav className="landing-nav glass">
        <div className="nav-logo">
          <BookOpen className="text-accent" size={28} />
          <span className="logo-text">PathShala</span>
        </div>
        <div className="nav-actions">
          <button className="login-btn" onClick={onLogin}>Log in</button>
          <button className="primary-btn" onClick={onSignup}>
            Get Started <ArrowRight size={16} />
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="hero-section">
        <div className="hero-background">
          <div className="glow-orb orb-1"></div>
          <div className="glow-orb orb-2"></div>
        </div>
        <div className="hero-content">
          <div className="badge">
            <Sparkles size={14} className="text-accent" />
            <span>The future of learning is here</span>
          </div>
          <h1 className="hero-title">
            Master any document<br />
            with your <span className="text-gradient">Personal AI Tutor</span>
          </h1>
          <p className="hero-subtitle">
            Upload your PDFs, textbooks, or research papers and instantly chat with them. 
            PathShala extracts the knowledge and answers your questions with precise citations.
          </p>
          <div className="hero-cta">
            <button className="primary-btn large" onClick={onSignup}>
              Start Learning for Free
            </button>
            <p className="hero-disclaimer">No credit card required.</p>
          </div>
        </div>
        
        {/* Mockup Preview */}
        <div className="hero-mockup-wrapper">
          <div className="hero-mockup glass">
            <div className="mockup-header">
              <div className="dots">
                <span className="dot red"></span>
                <span className="dot yellow"></span>
                <span className="dot green"></span>
              </div>
              <div className="mockup-title">Biology_101.pdf</div>
            </div>
            <div className="mockup-body">
              <div className="mockup-msg user">Can you explain the process of photosynthesis?</div>
              <div className="mockup-msg ai">
                Based on page 42 of your document, photosynthesis is the process where plants convert light energy into chemical energy...
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Features Section */}
      <section className="features-section">
        <div className="features-header">
          <h2>Why choose PathShala?</h2>
          <p>Built for students, researchers, and lifelong learners.</p>
        </div>
        
        <div className="features-grid">
          <div className="feature-card glass">
            <div className="feature-icon-wrapper">
              <BrainCircuit className="feature-icon" />
            </div>
            <h3>Smart Contextual Memory</h3>
            <p>Our AI remembers your previous questions in the conversation, allowing for natural, flowing follow-up questions.</p>
          </div>
          
          <div className="feature-card glass">
            <div className="feature-icon-wrapper">
              <Zap className="feature-icon" />
            </div>
            <h3>Lightning Fast Retrieval</h3>
            <p>Powered by advanced vector search (ChromaDB), we find the exact paragraph you need in milliseconds.</p>
          </div>
          
          <div className="feature-card glass">
            <div className="feature-icon-wrapper">
              <Shield className="feature-icon" />
            </div>
            <h3>Private & Secure</h3>
            <p>Your documents are strictly isolated. No one else can access your files, and you can securely delete them at any time.</p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer glass">
        <div className="footer-content">
          <div className="footer-left">
            <div className="footer-logo">
              <BookOpen className="text-accent" size={24} />
              <span className="logo-text">PathShala</span>
            </div>
            <p className="footer-copyright">© {new Date().getFullYear()} PathShala. All rights reserved.</p>
          </div>
          
          <div className="footer-right">
            <div className="footer-credits">
              <span>Crafted with passion by <strong className="text-primary">Teekshan Nayyar</strong></span>
              <a 
                href="https://www.linkedin.com/in/teekshan-nayyar" 
                target="_blank" 
                rel="noopener noreferrer"
                className="linkedin-link"
                title="Connect on LinkedIn"
              >
                <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path>
                  <rect x="2" y="9" width="4" height="12"></rect>
                  <circle cx="4" cy="4" r="2"></circle>
                </svg>
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
