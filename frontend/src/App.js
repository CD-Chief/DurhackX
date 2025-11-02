import './App.css';
import { useState, useEffect } from 'react';

function App() {
  const [orientation, setOrientation] = useState({
    yaw: 0,
    pitch: 0,
    face_detected: false
  });

  const [piConnected, setPiConnected] = useState(false);
  const [aiInsightsOpen, setAiInsightsOpen] = useState(true);
  const [aiMessage, setAiMessage] = useState("AI insights will appear here...");

  // Poll orientation data from laptop tracker
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch('http://localhost:5002/orientation');
        const data = await response.json();
        setOrientation(data);
      } catch (error) {
        console.error('Failed to fetch orientation:', error);
      }
    }, 100);

    return () => clearInterval(interval);
  }, []);

  // Check if Pi is connected
  useEffect(() => {
    const checkPi = setInterval(async () => {
      try {
        const response = await fetch('http://192.168.1.100:5000/video_feed', { method: 'HEAD' });
        setPiConnected(response.ok);
      } catch (error) {
        setPiConnected(false);
      }
    }, 2000);

    return () => clearInterval(checkPi);
  }, []);

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
          {/* Main video feed - What Pi sees */}
          <div className="main-video">
            {piConnected ? (
              <img 
                src="http://192.168.1.100:5000/video_feed" 
                alt="Pi Camera Feed"
                className="video-feed"
              />
            ) : (
              <div className="status-message">
                <div className="status-icon">📡</div>
                <p>Raspberry Pi Not Connected</p>
                <small>Waiting for connection on 192.168.1.100:5000</small>
              </div>
            )}
            <div className="video-label">What Pi Sees</div>
            
            {/* Orientation overlay */}
            <div className="orientation-overlay">
              <span className={`indicator ${orientation.face_detected ? 'active' : ''}`}></span>
              <span>Yaw: {orientation.yaw.toFixed(1)}°</span>
              <span> | Pitch: {orientation.pitch.toFixed(1)}°</span>
            </div>
          </div>
          
          {/* Small preview video in top left - Your laptop camera */}
          <div className="preview-video">
            <img 
              src="http://localhost:5002/laptop_feed" 
              alt="Laptop Camera Feed"
              className="video-feed"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextSibling.style.display = 'flex';
              }}
            />
            <div className="preview-placeholder" style={{display: 'none'}}>
              <small>Camera Starting...</small>
            </div>
            <div className="preview-label">Your Face</div>
          </div>
        </div>

        {/* AI Insights Box */}
        <div className={`ai-insights ${aiInsightsOpen ? 'open' : 'closed'}`}>
          <div className="ai-header" onClick={() => setAiInsightsOpen(!aiInsightsOpen)}>
            <span className="insight-indicator active"></span>
            <h3>Gemini Insights</h3>
            <button 
              className="ai-toggle"
              aria-label={aiInsightsOpen ? 'Close Gemini Insights' : 'Open Gemini Insights'}
            >
              <span className={`chevron ${aiInsightsOpen ? 'up' : 'down'}`}>
                {aiInsightsOpen ? '▼' : '▲'}
              </span>
            </button>
          </div>
          {aiInsightsOpen && (
            <div className="ai-content">
              <div className="ai-message">
                {aiMessage}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
