import './App.css';
import { useState, useEffect } from 'react';

function App() {
  const [orientation, setOrientation] = useState({
    yaw: 0,
    pitch: 0,
    face_detected: false,
    tracker_type: 'face',
    calibrated: false
  });

  const [piConnected, setPiConnected] = useState(false);

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

  const switchTracker = async (type) => {
    try {
      await fetch('http://localhost:5002/switch_tracker', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type })
      });
    } catch (error) {
      console.error('Failed to switch tracker:', error);
    }
  };

  const startCalibration = async () => {
    try {
      await fetch('http://localhost:5002/calibrate', { method: 'POST' });
    } catch (error) {
      console.error('Failed to start calibration:', error);
    }
  };

  return (
    <div className="App">
      <header className="header">
        <div className="header-content">
          <span className="team-name">Team Name</span>
          <h1 className="project-name">Visio</h1>
          <span className="durhack-badge">DurHackX</span>
        </div>
      </header>

      {/* Tracking controls - moved below header */}
      <div className="controls-bar">
        <div className="tracker-switch">
          <button 
            className={`btn ${orientation.tracker_type === 'face' ? 'active' : ''}`}
            onClick={() => switchTracker('face')}
          >
            👤 Face
          </button>
          <button 
            className={`btn ${orientation.tracker_type === 'eye' ? 'active' : ''}`}
            onClick={() => switchTracker('eye')}
          >
            👁️ Eye
          </button>
        </div>

        {orientation.tracker_type === 'eye' && (
          <button className="btn btn-calibrate" onClick={startCalibration}>
            🎯 Calibrate
          </button>
        )}

        <div className="orientation-display">
          <span className={`indicator ${orientation.face_detected ? 'active' : ''}`}></span>
          <span>Yaw: {orientation.yaw.toFixed(1)}°</span>
          {orientation.tracker_type === 'face' && (
            <span> | Pitch: {orientation.pitch.toFixed(1)}°</span>
          )}
        </div>
      </div>
      
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
            <div className="preview-label">
              {orientation.tracker_type === 'face' ? 'Your Face' : 'Your Eyes'}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
