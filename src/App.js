import React, { useEffect, useState } from 'react';
import './App.css';

function App() {
  const [connectors, setConnectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/connectors')
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch connectors');
        return res.json();
      })
      .then(data => {
        setConnectors(data.value || []);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo-section">
            <div className="logo">
              <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                <rect width="40" height="40" rx="8" fill="#0066CC"/>
                <path d="M12 14h16v2H12v-2zm0 5h16v2H12v-2zm0 5h10v2H12v-2z" fill="white"/>
              </svg>
            </div>
            <div className="brand">
              <h1>Express Network</h1>
              <p className="subtitle">Email Connector Management</p>
            </div>
          </div>
        </div>
      </header>

      <main className="main-content">
        <div className="container">
          <div className="page-header">
            <h2>SMTP Connectors</h2>
            <p className="description">Manage your SMTP relays and OAuth conversions</p>
          </div>

          {loading && (
            <div className="loading">
              <div className="spinner"></div>
              <p>Loading connectors...</p>
            </div>
          )}

          {error && (
            <div className="error-message">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && connectors.length === 0 && (
            <div className="empty-state">
              <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
                <circle cx="32" cy="32" r="32" fill="#F0F4F8"/>
                <path d="M32 20v24M20 32h24" stroke="#0066CC" strokeWidth="3" strokeLinecap="round"/>
              </svg>
              <h3>No connectors found</h3>
              <p>Get started by creating your first SMTP connector</p>
              <button className="btn btn-primary">Add Connector</button>
            </div>
          )}

          {!loading && !error && connectors.length > 0 && (
            <div className="connectors-grid">
              {connectors.map((connector, index) => (
                <div key={index} className="connector-card">
                  <div className="connector-header">
                    <div className="connector-icon">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>
                    <div className="connector-status status-active">Active</div>
                  </div>
                  <div className="connector-body">
                    <h3 className="connector-name">{connector.name || `Connector ${index + 1}`}</h3>
                    <div className="connector-details">
                      <div className="detail-row">
                        <span className="detail-label">Type:</span>
                        <span className="detail-value">{connector.type || 'SMTP'}</span>
                      </div>
                      {connector.host && (
                        <div className="detail-row">
                          <span className="detail-label">Host:</span>
                          <span className="detail-value">{connector.host}</span>
                        </div>
                      )}
                      {connector.port && (
                        <div className="detail-row">
                          <span className="detail-label">Port:</span>
                          <span className="detail-value">{connector.port}</span>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="connector-footer">
                    <button className="btn btn-secondary">Configure</button>
                    <button className="btn btn-ghost">Details</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      <footer className="footer">
        <div className="container">
          <p>&copy; 2026 Express Network. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
