import './App.css';
import { useState } from 'react';

function App() {
  const [connectionStatus, setConnectionStatus] = useState('disconnected');

  const cards = [
    { id: 1, color: '#3B82F6', label: 'Analytics' },     // Blue
    { id: 2, color: '#60A5FA', label: 'Dashboard' },    // Light Blue
    { id: 3, color: '#1E3A8A', label: 'Settings' },     // Dark Blue
    { id: 4, color: '#10B981', label: 'Profile' },      // Green
    { id: 5, color: '#34D399', label: 'Reports' },      // Light Green
    { id: 6, color: '#8B5CF6', label: 'Tasks' },        // Purple
  ];

  return (
    <div className="app">
      {/* Header Section */}
      <header className="header">
        <div className="header-content">
          <div className="team-badge">Team Name</div>
          <h1 className="project-title">Vison</h1>
          <p className="project-description">
            An innovative eye tracking API demonstration showcasing real-time gaze interaction
          </p>
          <div className="durhack-badge">Built for DurHack 2025</div>
        </div>
      </header>

      {/* Main Demo Area */}
      <main className="main-content">
        <div className="cards-grid">
          {cards.map((card) => (
            <div
              key={card.id}
              className="card"
              style={{ backgroundColor: card.color }}
            >
              <div className="card-content">
                <div className="card-number">{card.id}</div>
                <div className="card-label">{card.label}</div>
              </div>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="status-indicator">
          <span className={`status-dot ${connectionStatus}`}></span>
          <span className="status-text">
            Eye Tracking: {connectionStatus === 'connected' ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </footer>
    </div>
  );
}

export default App;
