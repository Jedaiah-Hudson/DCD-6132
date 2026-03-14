function DashboardPage() {
    const userEmail = localStorage.getItem('userEmail');
  
    return (
      <div style={{ padding: '40px', fontFamily: 'Arial, sans-serif' }}>
        <h1>Dashboard</h1>
        <p>Welcome{userEmail ? `, ${userEmail}` : ''}!</p>
      </div>
    );
  }
  
  export default DashboardPage;