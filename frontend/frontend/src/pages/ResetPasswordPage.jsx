import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import './ResetPasswordPage.css';

function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const token = searchParams.get('token');

  const [email, setEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const validatePassword = (password) => {
    const hasUppercase = /[A-Z]/.test(password);
    const hasLowercase = /[a-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    const hasSpecialCharacter = /[^A-Za-z0-9]/.test(password);
    const validLength = password.length >= 8 && password.length <= 20;

    return (
      validLength &&
      hasUppercase &&
      hasLowercase &&
      hasNumber &&
      hasSpecialCharacter
    );
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');

    const trimmedEmail = email.trim();

    if (!trimmedEmail) {
      setError('Please enter your email.');
      return;
    }

    if (!trimmedEmail.includes('@')) {
      setError('Please enter a valid email address.');
      return;
    }

    setLoading(true);

    try {
        const response = await fetch('http://127.0.0.1:8000/accounts/forgot-password/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: trimmedEmail }),
          });
          
          const raw = await response.text();
          let data = {};
          
          try {
            data = JSON.parse(raw);
          } catch {
            throw new Error('Server error while sending reset email.');
          }
          
          if (!response.ok) {
            throw new Error(data.error || data.message || 'Failed to send reset link.');
          }
          
      setMessage(data.message || 'If an account with that email exists, a reset link has been sent.');

      // dev only: useful while email sending is still placeholder
      if (data.reset_link_placeholder) {
        console.log('Reset link:', data.reset_link_placeholder);
      }
    } catch (err) {
      setError(err.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');

    const trimmedNewPassword = newPassword.trim();
    const trimmedConfirmNewPassword = confirmNewPassword.trim();

    if (!trimmedNewPassword || !trimmedConfirmNewPassword) {
      setError('Please fill in all fields.');
      return;
    }

    if (!validatePassword(trimmedNewPassword)) {
      setError(
        'Password must be 8–20 characters and include at least one uppercase letter, one lowercase letter, one number, and one special character.'
      );
      return;
    }

    if (trimmedNewPassword !== trimmedConfirmNewPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (!token) {
      setError('Missing reset token.');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/accounts/reset-password-confirm/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token,
          new_password: trimmedNewPassword,
          confirm_password: trimmedConfirmNewPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        const backendError = Array.isArray(data.error)
          ? data.error.join(' ')
          : data.error || 'Password reset failed.';
        throw new Error(backendError);
      }

      setMessage(data.message || 'Password has been reset successfully.');

      setTimeout(() => {
        navigate('/');
      }, 1500);
    } catch (err) {
      setError(err.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  const isResetMode = Boolean(token);

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">
          {isResetMode ? 'Reset Password' : 'Forgot Password'}
        </h1>

        <p className="auth-subtitle">
          {isResetMode
            ? 'Enter your new password below.'
            : 'Enter your email and we will send you a reset link.'}
        </p>

        {!isResetMode ? (
          <form onSubmit={handleForgotPassword} className="auth-form">
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

            {message && <p className="success-message">{message}</p>}
            {error && <p className="error-message">{error}</p>}

            <button type="submit" className="auth-button" disabled={loading}>
              {loading ? 'Sending...' : 'Send Reset Link'}
            </button>

            <div className="auth-links">
              <button
                type="button"
                className="text-button"
                onClick={() => navigate('/')}
              >
                Back to Login
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleResetPassword} className="auth-form">
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

            {message && <p className="success-message">{message}</p>}
            {error && <p className="error-message">{error}</p>}

            <button type="submit" className="auth-button" disabled={loading}>
              {loading ? 'Resetting...' : 'Reset Password'}
            </button>

            <div className="auth-links">
              <button
                type="button"
                className="text-button"
                onClick={() => navigate('/')}
              >
                Back to Login
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default ResetPasswordPage;