import { useState } from 'react';
import { Eye, EyeOff, Edit2, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import { deleteAccount, updateProfile, changePassword, errorMessage } from '../api';
import './ProfileSettings.css';

const MIN_PASSWORD_LENGTH = 8;
const MAX_PASSWORD_BYTES = 72;

export default function ProfileSettings({ user, onUserUpdate, onLogout }) {
  const [displayName, setDisplayName] = useState(user?.name || '');
  const [isEditingName, setIsEditingName] = useState(false);
  const [isSavingName, setIsSavingName] = useState(false);

  // Google-only accounts have no password yet and set one without the current one.
  const hasPassword = user?.has_password !== false;
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [showDeletePassword, setShowDeletePassword] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);


  const handleSaveProfile = async (e) => {
    e.preventDefault();
    const name = displayName.trim();
    if (!name) {
      toast.error('Display name cannot be empty.');
      return;
    }
    setIsSavingName(true);
    try {
      const updated = await updateProfile(name);
      setDisplayName(updated.name);
      onUserUpdate?.({ ...user, ...updated });
      setIsEditingName(false);
      toast.success('Profile updated successfully!');
    } catch (error) {
      console.error("Update profile error:", error);
      toast.error(errorMessage(error, 'Failed to update your name.'));
    } finally {
      setIsSavingName(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      toast.error(`New password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (new TextEncoder().encode(newPassword).length > MAX_PASSWORD_BYTES) {
      toast.error(`New password must be at most ${MAX_PASSWORD_BYTES} bytes.`);
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match.');
      return;
    }
    setIsChangingPassword(true);
    try {
      await changePassword({ currentPassword: hasPassword ? currentPassword : null, newPassword });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      if (!hasPassword) onUserUpdate?.({ ...user, has_password: true });
      toast.success(hasPassword ? 'Password changed successfully!' : 'Password set successfully!');
    } catch (error) {
      console.error("Change password error:", error);
      toast.error(errorMessage(error, 'Failed to change password.'));
    } finally {
      setIsChangingPassword(false);
    }
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
      toast.error(errorMessage(error, "Failed to delete account. Incorrect password?"));
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
                      maxLength={255}
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
              {isEditingName && (
                <button type="submit" className="save-btn" disabled={isSavingName}>
                  {isSavingName ? 'Saving...' : 'Save changes'}
                </button>
              )}
            </form>
          </section>

          <hr className="settings-divider" />

          {/* Change Password Section */}
          <section className="settings-section">
            <h3>{hasPassword ? 'Change password' : 'Set a password'}</h3>
            <form onSubmit={handleChangePassword} className="settings-form">
              {hasPassword && (
              <div className="form-group">
                <label>Current password</label>
                <div className="password-input">
                  <input
                    type={showCurrentPassword ? "text" : "password"}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    autoComplete="current-password"
                    required
                  />
                  <button type="button" onClick={() => setShowCurrentPassword(!showCurrentPassword)}>
                    {showCurrentPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              )}
              
              <div className="form-group">
                <label>New password</label>
                <div className="password-input">
                  <input
                    type={showNewPassword ? "text" : "password"}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    autoComplete="new-password"
                    minLength={MIN_PASSWORD_LENGTH}
                    required
                  />
                  <button type="button" onClick={() => setShowNewPassword(!showNewPassword)}>
                    {showNewPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              
              <div className="form-group">
                <label>Confirm new password</label>
                <div className="password-input">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    autoComplete="new-password"
                    required
                  />
                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)}>
                    {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              
              <button type="submit" className="save-btn" disabled={isChangingPassword}>
                {isChangingPassword ? 'Saving...' : hasPassword ? 'Update password' : 'Set password'}
              </button>
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
