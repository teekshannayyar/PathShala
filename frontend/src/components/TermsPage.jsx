import { Link } from 'react-router-dom';
import LegalPage, { Placeholder } from './LegalPage';

export default function TermsPage() {
  return (
    <LegalPage title="Terms and Conditions">
      <p className="legal-meta">Effective date: <Placeholder>Effective date</Placeholder></p>
      <p className="legal-meta">Operator: <Placeholder>Operator name</Placeholder></p>
      <p className="legal-meta">Contact: <Placeholder>Contact email</Placeholder></p>

      <p>
        These terms apply to your use of PathShala, a study app operated by{' '}
        <Placeholder>Operator name</Placeholder>.{' '}
        <Placeholder>How users accept these terms, for example when they sign up</Placeholder>
      </p>

      <h2>1. What PathShala does</h2>
      <p>
        PathShala lets you upload PDF documents, ask questions that are answered from the text of
        those documents, generate multiple-choice quizzes from them, and see your quiz results,
        weak topics and study streak.
      </p>

      <h2>2. Your account</h2>
      <p>
        You need an account to use PathShala. You can sign up with an email address and password,
        or with Google. Keep your password private. You can delete your account at any time in
        Settings.
      </p>
      <p><Placeholder>Minimum age to create an account</Placeholder></p>

      <h2>3. What you upload</h2>
      <p>
        Only upload documents you have the right to use. PathShala stores and processes your files
        to provide the features above, which includes sending parts of their text to Groq, as
        described in the <Link to="/privacy">Privacy Policy</Link>.
      </p>
      <p><Placeholder>Ownership of uploaded content and the permission PathShala needs to process it</Placeholder></p>

      <h2>4. Acceptable use</h2>
      <p><Placeholder>Uses that are not allowed, and what happens if they occur</Placeholder></p>

      <h2>5. AI-generated answers and quizzes</h2>
      <p>
        Answers and quizzes are written by an AI model and can be wrong or incomplete. Check
        important information against your documents and other reliable sources.
      </p>

      <h2>6. Usage limits</h2>
      <p>
        PathShala limits how many requests can be made from one IP address in a given time, for
        example how many quizzes can be generated per hour.
      </p>

      <h2>7. Fees</h2>
      <p>
        PathShala does not currently charge for accounts.{' '}
        <Placeholder>Update this section if paid plans are added</Placeholder>
      </p>

      <h2>8. Suspension and closing accounts</h2>
      <p><Placeholder>When the operator may suspend or close an account</Placeholder></p>

      <h2>9. Changes to the service and these terms</h2>
      <p><Placeholder>How the service may change and how users will be told about changes to these terms</Placeholder></p>

      <h2>10. Warranties and liability</h2>
      <p><Placeholder>Warranty disclaimer and limitation of liability, to be written by the operator</Placeholder></p>

      <h2>11. Governing law</h2>
      <p><Placeholder>Governing law and jurisdiction</Placeholder></p>

      <h2>12. Contact</h2>
      <p>Questions about these terms: <Placeholder>Contact email</Placeholder></p>
    </LegalPage>
  );
}
