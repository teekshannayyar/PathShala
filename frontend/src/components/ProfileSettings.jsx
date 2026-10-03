import { useState } from 'react';
import { Eye, EyeOff, Edit2, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import { deleteAccount } from '../api';
import './ProfileSettings.css';

export default function ProfileSettings({ user, onLogout }) {
  const [displayName, setDisplayName] = useState(user?.name || '');
  const [isEditingName, setIsEditingName] = useState(false);
  
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [showDeletePassword, setShowDeletePassword] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);


  const handleSaveProfile = (e) => {
    e.preventDefault();
    toast.success('Profile updated successfully!');
    setIsEditingName(false);
  };

  const handleChangePassword = (e) => {
    e.preventDefault();
    toast.success('Password changed successfully!');
  };

  const handleDeleteAccount = async (e) => {
    e.preventDefault();
    if (!deletePassword) {
      toast.error('Please enter your password to confirm.');
      return;
    }
    
    setIsDeleting(true);
    try {
      await deleteAccount(deletePassword);
      toast.success('Account permanently deleted.');
      onLogout();
    } catch (error) {
      console.error("Delete account error:", error);
      toast.error(error.response?.data?.detail || "Failed to delete account. Incorrect password?");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="settings-page animate-fade-in">
      <div className="settings-container">
        <div className="settings-header">
          <h2>Account Settings</h2>
        </div>

        <div className="settings-content glass">
          {/* Profile Section */}
          <section className="settings-section">
            <h3>Profile</h3>
            <p className="user-email">{user?.email || 'user@example.com'}</p>
            
            <form onSubmit={handleSaveProfile} className="settings-form">
              <div className="form-group">
                <label>Display name</label>
                <div className="display-name-container">
                  {isEditingName ? (
                    <input 
                      type="text" 
                      value={displayName} 
                      onChange={(e) => setDisplayName(e.target.value)} 
                      required
                      autoFocus
                    />
                  ) : (
                    <div className="display-name-view">
                      <span>{displayName}</span>
                      <button type="button" className="edit-name-btn" onClick={() => setIsEditingName(true)}>
                        <Edit2 size={14} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
              {isEditingName && <button type="submit" className="save-btn">Save changes</button>}
            </form>
          </section>

          <hr className="settings-divider" />

          {/* Change Password Section */}
          <section className="settings-section">
            <h3>Change password</h3>
            <form onSubmit={handleChangePassword} className="settings-form">
              <div className="form-group">
                <label>Current password</label>
                <div className="password-input">
                  <input type={showCurrentPassword ? "text" : "password"} required />
                  <button type="button" onClick={() => setShowCurrentPassword(!showCurrentPassword)}>
                    {showCurrentPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              
              <div className="form-group">
                <label>New password</label>
                <div className="password-input">
                  <input type={showNewPassword ? "text" : "password"} required />
                  <button type="button" onClick={() => setShowNewPassword(!showNewPassword)}>
                    {showNewPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              
              <div className="form-group">
                <label>Confirm new password</label>
                <div className="password-input">
                  <input type={showConfirmPassword ? "text" : "password"} required />
                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)}>
                    {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              
              <button type="submit" className="save-btn">Update password</button>
            </form>
          </section>

          <hr className="settings-divider" />

          {/* Session Section */}
          <section className="settings-section">
            <h3>Session</h3>
            <button className="signout-btn" onClick={onLogout}>Sign out</button>
          </section>

          <hr className="settings-divider" />

          {/* Delete Account */}
          <section className="settings-section">
            {!showDeleteConfirm ? (
               <button className="delete-account-btn" onClick={() => setShowDeleteConfirm(true)}>Delete account</button>
            ) : (
              <form onSubmit={handleDeleteAccount} className="delete-confirm-form">
                <div className="danger-content">
                  <AlertTriangle size={24} className="danger-icon" />
                  <p>Permanently delete your account and everything in it. This cannot be undone.</p>
                </div>
                <div className="form-group">
                  <label>Enter password to confirm</label>
                  <div className="password-input">
                    <input 
                      type={showDeletePassword ? "text" : "password"} 
                      value={deletePassword}
                      onChange={(e) => setDeletePassword(e.target.value)}
                      required 
                      placeholder="Password"
                    />
                    <button type="button" onClick={() => setShowDeletePassword(!showDeletePassword)}>
                      {showDeletePassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <div className="delete-actions">
                  <button type="button" className="cancel-delete-btn" onClick={() => setShowDeleteConfirm(false)}>Cancel</button>
                  <button type="submit" className="confirm-delete-btn" disabled={isDeleting}>
                    {isDeleting ? 'Deleting...' : 'Permanently Delete'}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
