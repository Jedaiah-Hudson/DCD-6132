import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './CreateAccountPage.css';

function CreateAccountPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleCreateAccount = async (e) => {
    e.preventDefault();
  
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();
    const trimmedConfirmPassword = confirmPassword.trim();
  
    if (!trimmedEmail || !trimmedPassword || !trimmedConfirmPassword) {
      alert('Please fill in all fields.');
      return;
    }
  
    if (!trimmedEmail.includes('@')) {
      alert('Please enter a valid email address.');
      return;
    }
  
    const hasUppercase = /[A-Z]/.test(trimmedPassword);
    const hasLowercase = /[a-z]/.test(trimmedPassword);
    const hasNumber = /[0-9]/.test(trimmedPassword);
    const hasSpecialCharacter = /[^A-Za-z0-9]/.test(trimmedPassword);
    const validLength = trimmedPassword.length >= 8 && trimmedPassword.length <= 20;
  
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
  
    if (trimmedPassword !== trimmedConfirmPassword) {
      alert('Passwords do not match.');
      return;
    }
  
    try {
      const response = await fetch('http://127.0.0.1:8000/accounts/signup/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: trimmedEmail,
          password: trimmedPassword,
        }),
      });
  
      const data = await response.json();
  
      if (!response.ok) {
        alert(data.message || 'Account creation failed.');
        return;
      }
  
      alert(data.message || 'Account created successfully!');
      navigate('/');
    } catch (error) {
      alert('Could not connect to the server.');
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">Create Account</h1>

        <form onSubmit={handleCreateAccount} className="auth-form">
          <div className="input-group">
            <label htmlFor="create-email">Email</label>
            <input
              id="create-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
            />
          </div>

          <div className="input-group">
            <label htmlFor="create-password">Password</label>
            <input
                id="create-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Create a password"
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
            <label htmlFor="confirm-password">Confirm Password</label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm your password"
            />
          </div>

          <button type="submit" className="auth-button">
            Create Account
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

export default CreateAccountPage;