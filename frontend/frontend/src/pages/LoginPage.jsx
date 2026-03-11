import { useState } from 'react';
import './LoginPage.css';

function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = (e) => {
    e.preventDefault();
  
    if (!email.trim() || !password.trim()) {
      alert('Please enter both email and password.');
      return;
    }
  
    alert('Login clicked');
  };
  
  return (
    <div className="min-h-screen login-page">
      <div className="login-card">
        <h1 className="login-title">AI Matchmaking Tool</h1>

        <form onSubmit={handleLogin} className="login-form">
          <div className="input-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
            />
          </div>

          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
            />
          </div>

          <button type="submit" className="login-button">
            Login
          </button>

          <div className="login-links">
            <button type="button" className="text-button">
              Create Account
            </button>
            <button type="button" className="text-button">
              Forgot Password?
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;