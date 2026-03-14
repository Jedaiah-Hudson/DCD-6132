import './DashboardPage.css';

const contracts = [
  {
    id: 1,
    title: 'Cybersecurity Infrastructure Enhancement',
    agency: 'Department of Defense',
    naics: '541512',
    dueDate: 'March 15, 2026',
    category: 'Prime',
  },
  {
    id: 2,
    title: 'Medical Equipment Manufacturing Contract',
    agency: 'Department of Health & Human Services',
    naics: '339112',
    dueDate: 'March 22, 2026',
    category: 'Subcontract',
  },
  {
    id: 3,
    title: 'Industrial Equipment Maintenance Services',
    agency: 'General Services Administration',
    naics: '811310',
    dueDate: 'April 5, 2026',
    category: 'Prime',
  },
  {
    id: 4,
    title: 'Healthcare IT System Implementation',
    agency: 'Veterans Affairs',
    naics: '541519',
    dueDate: 'April 12, 2026',
    category: 'Prime',
  },
];

const categories = [
  { name: 'Cybersecurity', count: 24 },
  { name: 'Manufacturing', count: 18 },
  { name: 'Industrial', count: 15 },
  { name: 'Healthcare', count: 21 },
];

const recentHistory = [
  {
    id: 1,
    agency: 'Department of Defense',
    naics: '541512',
    category: 'Prime',
    dueDate: 'Feb 28, 2026',
  },
  {
    id: 2,
    agency: 'GSA',
    naics: '541611',
    category: 'Subcontract',
    dueDate: 'Feb 25, 2026',
  },
  {
    id: 3,
    agency: 'Department of Energy',
    naics: '221114',
    category: 'Partnership',
    dueDate: 'Feb 20, 2026',
  },
];

function DashboardPage() {
  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <h2 className="sidebar-title">AI Matchmaking Tool</h2>

        <nav className="sidebar-nav">
          <button className="sidebar-link active">Dashboard</button>
          <button className="sidebar-link">AI Matchmaking</button>
          <button className="sidebar-link">Profile</button>
          <button className="sidebar-link">Notifications</button>
        </nav>
      </aside>

      <div className="dashboard-main">
        <header className="dashboard-topbar">
          <div className="dashboard-inner">
            <input
              type="text"
              placeholder="Search contracts..."
              className="search-bar"
            />
            <div className="topbar-icons">
              <span className="icon-circle">3</span>
              <span className="icon-placeholder">👤</span>
            </div>
          </div>
        </header>

        <main className="dashboard-content">
          <div className="dashboard-inner">
            <h1 className="page-title">Dashboard</h1>

            <section className="section">
              <h2 className="section-title">For You</h2>
              <div className="contract-list">
                {contracts.map((contract) => (
                  <div key={contract.id} className="contract-card">
                    <h3>{contract.title}</h3>
                    <p>
                      <strong>Agency:</strong> {contract.agency}
                    </p>
                    <p>
                      <strong>NAICS Code:</strong> {contract.naics}
                    </p>
                    <p>
                      <strong>Due Date:</strong> {contract.dueDate}
                    </p>
                    <span className="contract-tag">{contract.category}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="section">
              <h2 className="section-title">Quick Browse</h2>
              <div className="browse-grid">
                {categories.map((category) => (
                  <div key={category.name} className="browse-card">
                    <h3>{category.name}</h3>
                    <p>{category.count} opportunities</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="section">
              <h2 className="section-title">Recent Contract History</h2>
              <div className="history-table-wrapper">
                <table className="history-table">
                  <thead>
                    <tr>
                      <th>Agency</th>
                      <th>NAICS</th>
                      <th>Category</th>
                      <th>Due Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentHistory.map((item) => (
                      <tr key={item.id}>
                        <td>{item.agency}</td>
                        <td>{item.naics}</td>
                        <td>{item.category}</td>
                        <td>{item.dueDate}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}

export default DashboardPage;