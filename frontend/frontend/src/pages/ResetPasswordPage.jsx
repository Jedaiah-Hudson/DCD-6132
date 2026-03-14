import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './ResetPasswordPage.css';

function ResetPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');

  const handleResetPassword = (e) => {
    e.preventDefault();

    const trimmedEmail = email.trim();
    const trimmedNewPassword = newPassword.trim();
    const trimmedConfirmNewPassword = confirmNewPassword.trim();

    if (!trimmedEmail || !trimmedNewPassword || !trimmedConfirmNewPassword) {
      alert('Please fill in all fields.');
      return;
    }

    if (!trimmedEmail.includes('@')) {
      alert('Please enter a valid email address.');
      return;
    }

    const hasUppercase = /[A-Z]/.test(trimmedNewPassword);
    const hasLowercase = /[a-z]/.test(trimmedNewPassword);
    const hasNumber = /[0-9]/.test(trimmedNewPassword);
    const hasSpecialCharacter = /[^A-Za-z0-9]/.test(trimmedNewPassword);
    const validLength =
      trimmedNewPassword.length >= 8 && trimmedNewPassword.length <= 20;

    if (
      !validLength ||
      !hasUppercase ||
      !hasLowercase ||
      !hasNumber ||
      !hasSpecialCharacter
    ) {
      alert(
        'Password must be 8–20 characters and include at least one uppercase letter, one lowercase letter, one number, and one special character.'
      );
      return;
    }

    if (trimmedNewPassword !== trimmedConfirmNewPassword) {
      alert('Passwords do not match.');
      return;
    }

    alert('Password reset successfully. Please log in.');
    navigate('/');
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">Reset Password</h1>

        <form onSubmit={handleResetPassword} className="auth-form">
          <div className="input-group">
            <label htmlFor="reset-email">Email</label>
            <input
              id="reset-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
            />
          </div>

          <div className="input-group">
            <label htmlFor="new-password">New Password</label>
            <input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Enter your new password"
            />

            <ul className="password-rules">
              <li>8–20 characters</li>
              <li>At least one uppercase letter</li>
              <li>At least one lowercase letter</li>
              <li>At least one number</li>
              <li>At least one special character</li>
            </ul>
          </div>

          <div className="input-group">
            <label htmlFor="confirm-new-password">Confirm New Password</label>
            <input
              id="confirm-new-password"
              type="password"
              value={confirmNewPassword}
              onChange={(e) => setConfirmNewPassword(e.target.value)}
              placeholder="Confirm your new password"
            />
          </div>

          <button type="submit" className="auth-button">
            Reset Password
          </button>

          <div className="auth-links">
            <button type="button" className="text-button" onClick={() => navigate('/')}>
                Back to Login
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ResetPasswordPage;