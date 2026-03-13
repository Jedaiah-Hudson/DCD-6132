import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './LoginPage.css';


function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = (e) => {
    e.preventDefault();
  
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();
  
    if (!trimmedEmail || !trimmedPassword) {
      alert('Please enter both email and password.');
      return;
    }
  
    if (!trimmedEmail.includes('@')) {
      alert('Please enter a valid email address.');
      return;
    }
  
    setLoading(true);
  
    setTimeout(() => {
      alert("Login successful");
      setLoading(false);
    }, 1000);
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

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? "Logging in..." : "Login"}
          </button>
 
          <div className="login-links">
            <button type="button" className="text-button" onClick={() => navigate('/create-account')}>
              Create Account
            </button>
            
            <button type="button" className="text-button" onClick={() => navigate('/reset-password')}>
              Reset Password
            </button>

          </div>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;