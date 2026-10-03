import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, User, Bot, Paperclip, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { askQuestion, uploadDocument, getChatHistory, errorMessage, MAX_QUESTION_CHARS } from '../api';
import toast from 'react-hot-toast';
import './ChatInterface.css';

const MAX_UPLOAD_MB = 50;

// Raw HTML in answers is never rendered (no rehype-raw). The one tag LLMs
// commonly emit is <br> (e.g. inside table cells), so turn exactly that raw
// node into a real line break and drop nothing else into the DOM.
const BR_TAG = /^<br\s*\/?>$/i;
const rehypeLineBreaks = () => (tree) => {
  const walk = (node) => {
    if (!node.children) return;
    node.children = node.children.map(child =>
      child.type === 'raw' && BR_TAG.test(child.value.trim())
        ? { type: 'element', tagName: 'br', properties: {}, children: [] }
        : child
    );
    node.children.forEach(walk);
  };
  walk(tree);
};

const welcomeMessage = (doc) => {
  let content;
  if (doc.processing_status === 'ready') {
    content = 'Hi there! I have analyzed this document. What would you like to know?';
  } else if (doc.processing_status === 'failed') {
    content = `I couldn't process this document${doc.processing_error ? `: ${doc.processing_error}` : '.'} Try reprocessing it from Documents, or upload it again.`;
  } else {
    content = "I'm still processing this document. You can ask questions as soon as it's ready.";
  }
  return { id: `welcome-${doc.id}-${doc.processing_status}`, role: 'assistant', content, sources: [] };
};

export default function ChatInterface({ activeDocument, setActiveDocument }) {
  // Messages are tagged with the document they belong to (null for a chat
  // without a document), so a late reply never lands in another chat.
  const [chat, setChat] = useState({ docId: null, messages: [] });
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const navigate = useNavigate();

  const docId = activeDocument?.id ?? null;
  const isReady = !activeDocument || activeDocument.processing_status === 'ready';
  const ownMessages = chat.docId === docId ? chat.messages : [];
  const messages = activeDocument && ownMessages.length === 0 ? [welcomeMessage(activeDocument)] : ownMessages;

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  // Fetch chat history when the open document changes (not on status refreshes).
  useEffect(() => {
    if (docId === null) return;
    let ignore = false;
    const fetchHistory = async () => {
      try {
        const history = await getChatHistory(docId);
        if (!ignore) setChat({ docId, messages: history });
      } catch (error) {
        if (ignore) return;
        if (error?.response?.status === 404) {
          toast.error('That document no longer exists.', { id: 'doc-missing' });
          setActiveDocument(null);
        } else {
          console.error("Failed to load history", error);
        }
      }
    };
    fetchHistory();
    return () => { ignore = true; };
  }, [docId, setActiveDocument]);

  // The question starts this document's thread if its history hasn't loaded;
  // a reply is dropped if the user has since moved to another chat.
  const addQuestion = (forDocId, message) => {
    setChat(prev => prev.docId === forDocId
      ? { docId: forDocId, messages: [...prev.messages, message] }
      : { docId: forDocId, messages: [message] });
  };
  const addReply = (forDocId, message) => {
    setChat(prev => prev.docId === forDocId
      ? { docId: forDocId, messages: [...prev.messages, message] }
      : prev);
  };

  const handleGenerateQuiz = () => {
    if (!activeDocument) return;
    navigate(`/quizzes?generate=${activeDocument.id}`);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const userQuestion = input.trim();
    if (!userQuestion || isLoading || !isReady) return;
    if (userQuestion.length > MAX_QUESTION_CHARS) {
      toast.error(`Questions can be at most ${MAX_QUESTION_CHARS} characters.`);
      return;
    }

    const sentFor = docId;
    setInput('');
    
    // Add user message to UI
    addQuestion(sentFor, { id: Date.now().toString(), role: 'user', content: userQuestion });
    setIsLoading(true);

    try {
      const response = await askQuestion(userQuestion, sentFor ?? undefined);
      addReply(sentFor, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        sources: response.sources
      });
    } catch (error) {
      console.error("Chat error", error);
      if (error?.response?.status === 404 && sentFor !== null) {
        toast.error('That document no longer exists.', { id: 'doc-missing' });
        setActiveDocument(null);
        return;
      }
      toast.error(errorMessage(error, "Network error: Failed to get response from AI"));
      addReply(sentFor, {
        id: Date.now().toString(),
        role: 'assistant',
        content: "Sorry, I encountered an error trying to answer that. Make sure the backend is running.",
        sources: []
      });
    } finally {
      setIsLoading(false);
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
      setActiveDocument(newDoc);
      toast.success("PDF uploaded successfully!", { id: 'upload' });
    } catch (error) {
      console.error("Upload failed", error);
      toast.error(errorMessage(error, "Failed to upload document"), { id: 'upload' });
    } finally {
      setIsUploading(false);
      e.target.value = null; // reset input
    }
  };

  return (
    <div className="chat-container">
      {/* Optional Top Header for Chat */}
      <div className="chat-top-bar glass" style={{
        padding: '12px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid var(--border-color)',
        zIndex: 10
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {activeDocument ? (
            <h3 style={{ margin: 0, fontSize: '16px', color: 'var(--text-primary)' }}>
              {activeDocument.filename.replace('.pdf', '')}
            </h3>
          ) : (
            <h3 style={{ margin: 0, fontSize: '16px', color: 'var(--text-secondary)' }}>
              New Chat
            </h3>
          )}
        </div>

        {activeDocument && activeDocument.embedding_complete && (
          <button 
            onClick={handleGenerateQuiz}
            style={{
              background: 'var(--accent-glow)',
              color: 'var(--accent-primary)',
              border: 'none',
              padding: '8px 16px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            📝 Test Your Knowledge
          </button>
        )}
      </div>
      
      {messages.length === 0 ? (
        <div className="chat-empty">
          <h2>What can I help with?</h2>
        </div>
      ) : (
        <div className="chat-messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`message-row ${msg.role} animate-fade-in`}>
              <div className="avatar">
                {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
              </div>
              <div className="message-content">
                <div className="message-text markdown-body">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]} 
                    rehypePlugins={[rehypeLineBreaks]}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="message-row assistant animate-fade-in">
              <div className="avatar"><Bot size={18} /></div>
              <div className="message-content typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      <div className={`chat-input-area ${messages.length === 0 ? 'centered' : ''}`}>
        <form onSubmit={handleSubmit} className="input-form">
          <button 
            type="button" 
            className="attach-btn" 
            onClick={() => fileInputRef.current.click()}
            disabled={isUploading}
            title="Attach a PDF to chat with"
          >
            {isUploading ? <Loader2 size={20} className="spin" /> : <Paperclip size={20} />}
          </button>
          
          <input 
            type="file" 
            accept=".pdf" 
            ref={fileInputRef} 
            style={{ display: 'none' }} 
            onChange={handleFileChange}
          />
          
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              !activeDocument ? "Message PathShala..."
                : activeDocument.processing_status === 'failed' ? "This document couldn't be processed"
                : !isReady ? "Still processing this document..."
                : `Ask a question about ${activeDocument.filename.replace('.pdf', '')}...`
            }
            maxLength={MAX_QUESTION_CHARS}
            disabled={isLoading || !isReady}
          />
          <button type="submit" className="send-btn" disabled={isLoading || !isReady || !input.trim()}>
            <Send size={18} />
          </button>
        </form>
        <div className="chat-disclaimer">
          PathShala can make mistakes. Consider checking important information.
        </div>
      </div>
    </div>
  );
}
