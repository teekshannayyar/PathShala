import { Link } from 'react-router-dom';
import { BookOpen } from 'lucide-react';
import './LegalPage.css';

// Text the operator still has to fill in before launch, shown highlighted.
export function Placeholder({ children }) {
  return <mark className="legal-placeholder">[{children}]</mark>;
}

export default function LegalPage({ title, children }) {
  return (
    <div className="legal-page">
      <header className="legal-header">
        <Link to="/" className="legal-brand">
          <BookOpen size={24} />
          <span>PathShala</span>
        </Link>
      </header>

      <main className="legal-main">
        <div className="legal-draft-note" role="note">
          <strong>Draft for review.</strong> This page is not final. Every item in
          highlighted square brackets must be filled in, and the whole page reviewed,
          before PathShala launches.
        </div>

        <h1>{title}</h1>
        {children}
      </main>

      <footer className="legal-footer">
        <nav aria-label="Legal">
          <Link to="/">Home</Link>
          <Link to="/privacy">Privacy Policy</Link>
          <Link to="/terms">Terms and Conditions</Link>
        </nav>
      </footer>
    </div>
  );
}
