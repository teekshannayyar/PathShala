import { Link } from 'react-router-dom';
import LegalPage, { Placeholder } from './LegalPage';

export default function PrivacyPolicy() {
  return (
    <LegalPage title="Privacy Policy">
      <p className="legal-meta">Effective date: <Placeholder>Effective date</Placeholder></p>
      <p className="legal-meta">Operator: <Placeholder>Operator name</Placeholder></p>
      <p className="legal-meta">Contact: <Placeholder>Contact email</Placeholder></p>

      <p>
        This page explains what information PathShala stores when you use it, why it is stored,
        which outside services receive it, and how you can delete it. It describes how the
        PathShala software works today.
      </p>

      <h2>1. Information PathShala stores</h2>

      <h3>Your account</h3>
      <ul>
        <li>Your email address and display name.</li>
        <li>
          If you sign up with an email and password: a bcrypt hash of your password. The password
          itself is not stored.
        </li>
        <li>
          If you sign in with Google: the email address, name and profile picture link that Google
          provides when it confirms your sign-in.
        </li>
        <li>The date and time your account was created.</li>
      </ul>

      <h3>Your documents</h3>
      <ul>
        <li>The PDF files you upload, saved on PathShala&apos;s server.</li>
        <li>Each file&apos;s name, folder, size, upload time and processing status, plus an error message if processing failed.</li>
        <li>The text extracted from each PDF.</li>
        <li>
          A search index: the extracted text split into passages of about 500 words, with a list of
          numbers (an embedding) computed for each passage on PathShala&apos;s server. These are kept in
          a vector database so the app can find the passages that match your question.
        </li>
      </ul>

      <h3>Your chats, quizzes and activity</h3>
      <ul>
        <li>
          The questions you ask about a document and the answers you receive, saved with that
          document. Questions asked with no document open are not saved.
        </li>
        <li>
          Quizzes generated from your documents: the questions, answer options, correct answers,
          topics and explanations.
        </li>
        <li>
          Your quiz attempts: your score, your answer to each question, whether it was correct, and
          when you finished.
        </li>
        <li>
          The calendar dates (in your time zone) on which you uploaded a document, asked a question
          or submitted a quiz. These dates are used to count your study streak.
        </li>
      </ul>

      <h3>In your browser</h3>
      <ul>
        <li>
          After you sign in, a sign-in token is kept in your browser&apos;s local storage. It is removed
          when you log out, and the server stops accepting it after a set time (60 minutes by
          default).
        </li>
        <li>
          Each request to PathShala includes your browser&apos;s time zone name (for example
          Asia/Kolkata) so that streaks follow your local days. The time zone itself is not saved.
        </li>
        <li>The PathShala code does not include analytics or advertising scripts.</li>
      </ul>

      <h2>2. Why it is stored</h2>
      <p>
        This information is used only to run the features you see in the app: signing you in,
        showing your documents, answering questions from your documents, generating and grading
        quizzes, listing your weak topics, and counting your study streak.
      </p>

      <h2>3. Services that receive your information</h2>
      <h3>Groq (AI answers and quizzes)</h3>
      <p>
        PathShala uses Groq&apos;s API to write answers and quizzes. When you ask a question about a
        document, your question, up to three matching passages from that document and up to four
        earlier messages from the same chat are sent to Groq. A question asked with no document
        open is sent on its own. When you generate a quiz, up to the first 15,000 characters of the
        document&apos;s text are sent to Groq. Groq&apos;s handling of this data is covered by its own
        terms and privacy policy: <Placeholder>Link to Groq&apos;s privacy policy</Placeholder>.
      </p>
      <h3>Google</h3>
      <p>
        If you choose Google sign-in, Google confirms your identity and shares your email address,
        name and profile picture link with PathShala. The app also loads Google&apos;s sign-in script
        (from accounts.google.com) and the Inter font (from Google Fonts), so your browser contacts
        Google when you open PathShala.
      </p>
      <h3>Hosting</h3>
      <p>
        The website, the server, the database, the uploaded files and the vector database are run
        by hosting providers: <Placeholder>List each hosting provider and the region where data is stored</Placeholder>.
      </p>

      <h2>4. Request limits and IP addresses</h2>
      <p>
        To limit how many requests one person can make (for example, sign-in attempts per minute),
        the server counts requests per IP address. These counters are held in the server&apos;s memory,
        or in a separate counter store if one is configured, and are not saved in the database.
        Hosting providers may keep their own request logs: <Placeholder>Describe hosting logs and how long they are kept</Placeholder>.
      </p>

      <h2>5. How long information is kept and how to delete it</h2>
      <p>Your information is kept until you delete it.</p>
      <ul>
        <li>
          <strong>Deleting a document</strong> (on the Documents page, or deleting a chat in the chat
          sidebar) removes the PDF file, its passages and embeddings from the vector database, its
          chat messages, and the quizzes and quiz attempts made from it.
        </li>
        <li>
          <strong>Deleting your account</strong> (in Settings) removes all of your PDF files, their
          entries in the vector database, and every database record linked to your account: your
          profile, documents, chats, quizzes, quiz attempts and activity dates.
        </li>
        <li>
          Backups: <Placeholder>Describe database backups and how long deleted data can remain in them</Placeholder>.
        </li>
      </ul>

      <h2>6. Security</h2>
      <p>
        Passwords are stored only as bcrypt hashes. Each document, chat and quiz can be opened only
        by the account that created it. <Placeholder>Add any further security measures the operator applies, such as encryption in transit and at rest</Placeholder>.
      </p>

      <h2>7. Your choices</h2>
      <p>
        In the app you can rename, move and delete your documents, change your display name,
        change or set a password, and delete your account. For anything else, such as a copy of
        your data, contact <Placeholder>Contact email</Placeholder>.
      </p>

      <h2>8. Children</h2>
      <p><Placeholder>Minimum age to use PathShala and any rules for younger users</Placeholder></p>

      <h2>9. Your rights under law</h2>
      <p><Placeholder>Rights that apply under the laws where PathShala operates, and how to exercise them</Placeholder></p>

      <h2>10. Changes to this policy</h2>
      <p><Placeholder>How users will be told about changes to this policy</Placeholder></p>

      <p>
        See also the <Link to="/terms">Terms and Conditions</Link>.
      </p>
    </LegalPage>
  );
}
