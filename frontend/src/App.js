import './App.css';

function App() {
  return (
    <div className="App">
      <header className="header">
        <div className="header-content">
          <span className="team-name">Team Name</span>
          <h1 className="project-name">Visio</h1>
          <span className="durhack-badge">DurHackX</span>
        </div>
      </header>
      
      <main className="main-content">
        <div className="video-container">
          {/* Main video feed placeholder */}
          <div className="main-video">
            <div className="status-message">
              <div className="status-icon">📡</div>
              <p>Raspberry Pi Not Connected</p>
            </div>
          </div>
          
          {/* Small preview video in top left */}
          <div className="preview-video"></div>
        </div>
      </main>
    </div>
  );
}

export default App;
