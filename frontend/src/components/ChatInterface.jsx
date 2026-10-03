import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, User, Bot, Paperclip, Loader2, PanelLeftOpen } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { askQuestion, uploadDocument, getChatHistory, generateQuiz } from '../api';
import toast from 'react-hot-toast';
import './ChatInterface.css';

const MAX_UPLOAD_MB = 50;

export default function ChatInterface({ activeDocument, setActiveDocument }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  
  const [isGeneratingQuiz, setIsGeneratingQuiz] = useState(false);
  const [quizData, setQuizData] = useState(null);
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const navigate = useNavigate();

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Fetch chat history or reset when document changes
  useEffect(() => {
    const fetchHistory = async () => {
      if (activeDocument) {
        try {
          const history = await getChatHistory(activeDocument.id);
          if (history.length > 0) {
            setMessages(history);
          } else {
            setMessages([
              {
                id: 'welcome',
                role: 'assistant',
                content: `Hi there! I have analyzed this document. What would you like to know?`,
                sources: []
              }
            ]);
          }
        } catch (error) {
          console.error("Failed to load history", error);
        }
      } else {
        setMessages([]);
      }
    };
    fetchHistory();
  }, [activeDocument]);

  const handleGenerateQuiz = () => {
    if (!activeDocument) return;
    navigate(`/quizzes?generate=${activeDocument.id}`);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userQuestion = input.trim();
    setInput('');
    
    // Add user message to UI
    const newUserMsg = { id: Date.now().toString(), role: 'user', content: userQuestion };
    setMessages(prev => [...prev, newUserMsg]);
    setIsLoading(true);

    try {
      const response = await askQuestion(userQuestion, activeDocument?.id);
      
      const newBotMsg = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        sources: response.sources
      };
      
      setMessages(prev => [...prev, newBotMsg]);
    } catch (error) {
      console.error("Chat error", error);
      toast.error(error.response?.data?.detail || "Network error: Failed to get response from AI");
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: "Sorry, I encountered an error trying to answer that. Make sure the backend is running.",
        sources: []
      }]);
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
      toast.error(error.response?.data?.detail || "Failed to upload document", { id: 'upload' });
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
            disabled={isGeneratingQuiz}
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
            {isGeneratingQuiz ? <Loader2 size={16} className="spin" /> : "📝 Test Your Knowledge"}
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
                    rehypePlugins={[rehypeRaw]}
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
            placeholder={activeDocument ? `Ask a question about ${activeDocument.filename.replace('.pdf', '')}...` : "Message PathShala..."}
            disabled={isLoading}
          />
          <button type="submit" className="send-btn" disabled={isLoading || !input.trim()}>
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
