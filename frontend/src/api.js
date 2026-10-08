import axios from 'axios';

// An empty VITE_API_URL means the API is on the same origin as the site
// (Dockerfile.preview); unset means the local dev server.
export const API_BASE = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');

export const api = axios.create({
  baseURL: `${API_BASE}/api`,
});

// The browser's IANA timezone (e.g. "Asia/Kolkata"), so study streaks count
// the user's local days. The server falls back to UTC if it's missing.
const browserTimeZone = () => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
};

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const timeZone = browserTimeZone();
  if (timeZone) {
    config.headers['X-Timezone'] = timeZone;
  }
  return config;
});

// Fired when the server rejects our token (expired, invalid, or the account
// is gone). App listens for it, drops the user and lands on /login.
export const SESSION_EXPIRED_EVENT = 'pathshala:session-expired';

// Credential checks answer 401 for a wrong password; that is not an expired session.
const CREDENTIAL_ENDPOINTS = ['/auth/login', '/auth/register', '/auth/google'];

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error?.config?.url || '';
    if (error?.response?.status === 401 && !CREDENTIAL_ENDPOINTS.includes(url)) {
      localStorage.removeItem('token');
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
    return Promise.reject(error);
  }
);

export const login = async ({ email, password }) => {
  const response = await api.post('/auth/login', { email, password });
  return response.data;
};

export const register = async ({ name, email, password }) => {
  const response = await api.post('/auth/register', { name, email, password });
  return response.data;
};

export const googleLogin = async (credential) => {
  const response = await api.post('/auth/google', { credential });
  return response.data;
};

export const getDocuments = async () => {
  const response = await api.get('/documents/');
  return response.data;
};

export const deleteDocument = async (documentId) => {
  const response = await api.delete(`/documents/${documentId}`);
  return response.data;
};

export const getChatHistory = async (documentId) => {
  const response = await api.get(`/chat/history/${documentId}`);
  return response.data;
};

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const askQuestion = async (question, documentId) => {
  const response = await api.post('/chat/', {
    question,
    document_id: documentId,
  });
  return response.data;
};

export const deleteAccount = async (password) => {
  const response = await api.delete('/auth/me', {
    data: { password }
  });
  return response.data;
};

export const getCurrentUser = async () => {
  const response = await api.get('/auth/me');
  return response.data;
};

export const updateProfile = async (name) => {
  const response = await api.put('/auth/me', { name });
  return response.data;
};

export const changePassword = async ({ currentPassword, newPassword, googleCredential }) => {
  const response = await api.put('/auth/me/password', {
    current_password: currentPassword || null,
    new_password: newPassword,
    google_credential: googleCredential || null,
  });
  return response.data;
};

export const getUserStats = async () => {
  const response = await api.get('/auth/me/stats');
  return response.data;
};

export const renameDocument = async (documentId, newName) => {
  const response = await api.put(`/documents/${documentId}/rename`, {
    filename: newName
  });
  return response.data;
};

export const moveDocumentToFolder = async (documentId, folderName) => {
  const response = await api.put(`/documents/${documentId}/folder`, {
    folder: folderName
  });
  return response.data;
};

export const bulkDeleteDocuments = async (documentIds) => {
  const response = await api.post('/documents/bulk-delete', {
    document_ids: documentIds
  });
  return response.data;
};

export const reprocessDocument = async (documentId) => {
  const response = await api.post(`/documents/${documentId}/reprocess`);
  return response.data;
};

export const generateQuiz = async (documentId) => {
  const response = await api.post(`/quizzes/generate/${documentId}`);
  return response.data;
};

export const getQuizzes = async () => {
  const response = await api.get('/quizzes/');
  return response.data;
};

export const getQuiz = async (quizId) => {
  const response = await api.get(`/quizzes/${quizId}`);
  return response.data;
};

export const submitQuiz = async (quizId, answers) => {
  const response = await api.post(`/quizzes/${quizId}/submit`, { answers });
  return response.data;
};

export const getWeakTopics = async () => {
  const response = await api.get('/quizzes/analytics/weak-topics');
  return response.data;
};

// FastAPI returns a string detail for HTTPException and a list for validation errors.
export const errorMessage = (error, fallback) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') return detail[0].msg;
  return fallback;
};

export const MAX_QUESTION_CHARS = 4000;
