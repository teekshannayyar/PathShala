import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { BookOpen, Check, Eye, EyeOff, MessageSquare, Zap, Shield } from 'lucide-react';
import axios from 'axios';
import './Auth.css';

export default function Auth({ onLogin, defaultIsLogin = true }) {
  const [isLogin, setIsLogin] = useState(defaultIsLogin);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({ name: '', email: '', password: '', confirmPassword: '' });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // Password validation checks
  const hasMinLength = formData.password.length >= 8;
  const hasUpper = /[A-Z]/.test(formData.password);
  const hasSymbol = /[!@#$%^&*(),.?":{}|<>]/.test(formData.password);
  const isPasswordValid = hasMinLength && hasUpper && hasSymbol;

  const handleManualAuth = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!isLogin) {
      if (!isPasswordValid) {
        return setError('Please fulfill all password requirements.');
      }
      if (formData.password !== formData.confirmPassword) {
        return setError('Passwords do not match.');
      }
    }

    const endpoint = isLogin ? '/auth/login' : '/auth/register';
    
    try {
      const res = await axios.post(`http://127.0.0.1:8000/api${endpoint}`, {
        name: formData.name,
        email: formData.email,
        password: formData.password
      });
      onLogin(res.data.user, res.data.access_token);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Authentication failed. (Check backend terminal for exact error)');
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const res = await axios.post('http://127.0.0.1:8000/api/auth/google', {
        credential: credentialResponse.credential
      });
      onLogin(res.data.user, res.data.access_token);
    } catch (err) {
      console.error(err);
      setError('Login failed. Please make sure the backend is running.');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-left">
        <div className="auth-left-bg-shapes">
          <div className="auth-shape shape-1"></div>
          <div className="auth-shape shape-2"></div>
        </div>
        
        <div className="auth-left-content">
          <div className="auth-brand">
            <BookOpen size={48} className="auth-brand-icon" />
            <h1>PathShala</h1>
          </div>
          
          <div className="auth-quote">
            "The beautiful thing about learning is that no one can take it away from you."
            <span>- B.B. King</span>
          </div>

          <div className="auth-features">
            <div className="auth-feature-item">
              <div className="feature-icon-box"><MessageSquare size={18} /></div>
              <span>Chat instantly with any textbook or PDF</span>
            </div>
            <div className="auth-feature-item">
              <div className="feature-icon-box"><Zap size={18} /></div>
              <span>Lightning-fast RAG retrieval and citations</span>
            </div>
            <div className="auth-feature-item">
              <div className="feature-icon-box"><Shield size={18} /></div>
              <span>100% private, isolated document storage</span>
            </div>
          </div>
        </div>
      </div>
      
      <div className="auth-right">
        <div className="auth-card glass animate-slide-up">
          <h2>{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
          <p>{isLogin ? 'Sign in to start chatting' : 'Sign up to PathShala'}</p>
          
          {error && <div className="error-msg">{error}</div>}
          
          <form className="manual-auth-form" onSubmit={handleManualAuth}>
            {!isLogin && (
              <input 
                type="text" 
                name="name" 
                placeholder="Your Name" 
                value={formData.name} 
                onChange={handleInputChange}
                required 
              />
            )}
            <input 
              type="email" 
              name="email" 
              placeholder="Email Address" 
              value={formData.email} 
              onChange={handleInputChange}
              required 
            />
            <div className="password-group">
              <div className="password-input-wrapper">
                <input 
                  type={showPassword ? "text" : "password"} 
                  name="password" 
                  placeholder="Password" 
                  value={formData.password} 
                  onChange={handleInputChange}
                  required 
                />
                <button 
                  type="button" 
                  className="eye-btn" 
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            
            {!isLogin && (
              <>
                <div className="password-input-wrapper">
                  <input 
                    type={showConfirm ? "text" : "password"} 
                    name="confirmPassword" 
                    placeholder="Confirm Password" 
                    value={formData.confirmPassword} 
                    onChange={handleInputChange}
                    required 
                  />
                  <button 
                    type="button" 
                    className="eye-btn" 
                    onClick={() => setShowConfirm(!showConfirm)}
                  >
                    {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <div className="password-requirements">
                  <div className={`req-item ${hasMinLength ? 'met' : ''}`}>
                    <Check size={10} className="req-icon" /> Minimum 8 characters
                  </div>
                  <div className={`req-item ${hasUpper ? 'met' : ''}`}>
                    <Check size={10} className="req-icon" /> One uppercase letter
                  </div>
                  <div className={`req-item ${hasSymbol ? 'met' : ''}`}>
                    <Check size={10} className="req-icon" /> One symbol (e.g. @, #, $)
                  </div>
                </div>
              </>
            )}
            <button type="submit" className="auth-submit-btn">
              {isLogin ? 'Sign In' : 'Sign Up'}
            </button>
          </form>

          <div className="auth-divider">
            <span>or continue with</span>
          </div>

          <div className="google-btn-wrapper">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => setError('Google Sign-In failed.')}
              theme="outline"
              size="large"
              shape="rectangular"
            />
          </div>

          <div className="auth-toggle">
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <button type="button" onClick={() => setIsLogin(!isLogin)}>
              {isLogin ? 'Sign up' : 'Log in'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
