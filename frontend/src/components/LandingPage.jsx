import { Link } from 'react-router-dom';
import { BookOpen, FileText, MessageSquare, ListChecks, Target, Trash2 } from 'lucide-react';
import './LandingPage.css';

const FEATURES = [
  {
    icon: FileText,
    title: 'Upload your PDFs',
    text: 'Add PDFs of up to 50 MB and sort them into folders. PathShala reads the text in each file, so scanned pages without selectable text cannot be used.',
  },
  {
    icon: MessageSquare,
    title: 'Ask questions about a document',
    text: 'Each answer is written from the three passages of the document that best match your question, plus your last few messages in that chat. Answers can contain mistakes, so check anything important.',
  },
  {
    icon: ListChecks,
    title: 'Generate quizzes',
    text: 'Create a multiple-choice quiz of up to 10 questions from a document. After you submit it, you see the correct answer to every question, with a short explanation when one was generated.',
  },
  {
    icon: Target,
    title: 'Find your weak topics',
    text: 'Every quiz question is tagged with a topic. Topics where you answer fewer than 60% correctly are listed, weakest first. The dashboard also counts how many days in a row you have studied.',
  },
  {
    icon: Trash2,
    title: 'Delete what you upload',
    text: 'Only your account can open your documents. Deleting a document removes the file, its chats and its quizzes. Deleting your account removes everything you added.',
  },
];

export default function LandingPage({ onLogin, onSignup }) {
  return (
    <div className="landing-container">
      <nav className="landing-nav">
        <div className="nav-logo">
          <BookOpen className="text-accent" size={28} />
          <span className="logo-text">PathShala</span>
        </div>
        <div className="nav-actions">
          <button className="login-btn" onClick={onLogin}>Log in</button>
          <button className="primary-btn" onClick={onSignup}>Sign up</button>
        </div>
      </nav>

      <header className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">Ask questions about your PDFs and get answers from their text</h1>
          <p className="hero-subtitle">
            Upload a textbook chapter, lecture notes or a paper. PathShala answers your questions
            using passages from that document, builds multiple-choice quizzes from it, lists the
            quiz topics you score lowest on, and tracks your study streak.
          </p>
          <div className="hero-cta">
            <button className="primary-btn large" onClick={onSignup}>Create an account</button>
            <button className="secondary-btn large" onClick={onLogin}>Log in</button>
          </div>
        </div>
      </header>

      <section className="features-section">
        <div className="features-header">
          <h2>What PathShala does</h2>
        </div>

        <div className="features-grid">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div className="feature-card" key={title}>
              <div className="feature-icon-wrapper">
                <Icon className="feature-icon" />
              </div>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          ))}
        </div>

        <p className="features-note">
          To write answers and quizzes, the relevant document text and your questions are sent
          to Groq, the AI service PathShala uses. See the <Link to="/privacy">Privacy Policy</Link> for
          details.
        </p>
      </section>

      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-left">
            <div className="footer-logo">
              <BookOpen className="text-accent" size={24} />
              <span className="logo-text">PathShala</span>
            </div>
            <p className="footer-copyright">© {new Date().getFullYear()} PathShala. All rights reserved.</p>
          </div>

          <div className="footer-right">
            <nav className="footer-legal" aria-label="Legal">
              <Link to="/privacy">Privacy Policy</Link>
              <Link to="/terms">Terms and Conditions</Link>
            </nav>
            <div className="footer-credits">
              <span>Built by <strong className="text-primary">Teekshan Nayyar</strong></span>
              <a
                href="https://www.linkedin.com/in/teekshan-nayyar"
                target="_blank"
                rel="noopener noreferrer"
                className="linkedin-link"
                title="Teekshan Nayyar on LinkedIn"
                aria-label="Teekshan Nayyar on LinkedIn"
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
