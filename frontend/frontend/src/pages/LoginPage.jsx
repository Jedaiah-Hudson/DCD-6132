import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './LoginPage.css';


function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
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
  
    try {
      const response = await fetch('http://127.0.0.1:8000/accounts/login/', {
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
        alert(data.message || 'Login failed.');
        setLoading(false);
        return;
      }
  
      localStorage.setItem('token', data.token);
      localStorage.setItem('userEmail', data.user.email);
      
      console.log('login response:', data);
      console.log('stored token:', localStorage.getItem('token'));
  
      alert(data.message || 'Login successful!');
      setLoading(false);
      navigate('/dashboard');
    } catch (error) {
      alert('Could not connect to the server.');
      setLoading(false);
    }
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
              Forgot Password
            </button>

          </div>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;