# 👁️ Visio - Eye & Face Tracking System

<div align="center">

![DurHackX 2025](https://img.shields.io/badge/DurHackX-2025-60A5FA?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-19.2-61DAFB?style=for-the-badge&logo=react)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Enabled-FF6B6B?style=for-the-badge)

**An innovative real-time eye and face tracking system built for DurHackX 2025**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Architecture](#-architecture) • [Team](#-team)

</div>

---

## 📖 Overview

**Visio** is a sophisticated face tracking application that enables real-time head pose detection and orientation tracking. The system uses MediaPipe for advanced computer vision capabilities and provides a seamless web interface for monitoring and control.

### 🎯 Key Capabilities

- **Face Orientation Tracking**: Real-time head pose estimation (yaw, pitch, roll)
- **Real-time Processing**: Sub-100ms latency for responsive tracking
- **Web Dashboard**: Modern React-based interface for live monitoring
- **Distributed Architecture**: Laptop-based tracking with Raspberry Pi integration (in development)

---

## ✨ Features

### 🔍 Face Tracking
- Real-time head pose estimation (yaw, pitch, roll)
- Face landmark detection with MediaPipe Face Mesh
- Smooth orientation calculation
- Visual feedback overlay

### ️ Web Interface
- Live video feed display
- Dual camera support (laptop + Raspberry Pi)
- Real-time orientation data display
- Connection status monitoring
- Responsive design for all devices

---

## 🚀 Installation

### Prerequisites

⚠️ **Important**: This project requires **Python 3.12** due to MediaPipe compatibility requirements. The latest Python versions are not supported.

- **Python 3.12** (specifically required for MediaPipe)
- **Node.js 14+** and npm
- **Webcam** or camera device
- **Windows/Linux/macOS**

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/CD-Chief/DurhackX.git
cd DurhackX
```

### 2️⃣ Backend Setup (Laptop Tracker)

```bash
cd laptop

# Install Python dependencies using Python 3.12
py -3.12 -m pip install -r requirements.txt

# Download MediaPipe face landmarker model (if not already present)
# The model should be in laptop/models/ directory
```

### 3️⃣ Frontend Setup

```bash
cd ../frontend

# Install Node.js dependencies
npm install

# Start the development server
npm start
```

The frontend will be available at `http://localhost:3000`

---

## 🎮 Usage

### Starting the System

#### 1. Start the Laptop Tracker (Backend)

```bash
cd laptop
py -3.12 main.py
```

The tracker server will start on `http://localhost:5002`

#### 2. Start the Web Interface (Frontend)

```bash
cd frontend
npm start
```

Access the dashboard at `http://localhost:3000`

### Using the Dashboard

1. **Monitor Status**: Watch the connection indicator and real-time orientation data (Yaw and Pitch)
2. **Video Feeds**: 
   - **Main view**: Shows what the Raspberry Pi camera sees (when connected)
   - **Preview**: Shows your laptop camera feed with face tracking overlay

---

## 🏗️ Architecture

### Project Structure

```
DurhackX/
├── laptop/                 # Backend tracking system
│   ├── main.py            # Main server and tracking coordinator
│   ├── face_tracker.py    # Face orientation tracking
│   ├── communication.py   # Raspberry Pi communication
│   ├── models/            # MediaPipe model files
│   └── requirements.txt   # Python dependencies
│
├── frontend/              # React web interface
│   ├── src/
│   │   ├── App.js        # Main application component
│   │   ├── App.css       # Styling
│   │   └── index.js      # Entry point
│   ├── public/           # Static assets
│   └── package.json      # Node dependencies
│
└── Raspberry/            # ⚠️ In Development
    └── (Testing code only - not yet functional)
```

### Technology Stack

**Backend:**
- Python 3.12
- MediaPipe (Face Mesh, Iris Detection)
- OpenCV (cv2)
- Flask (REST API)
- NumPy (numerical processing)

**Frontend:**
- React 19.2
- Modern CSS with Flexbox/Grid
- Fetch API for real-time communication

**Communication:**
- HTTP REST endpoints
- JSON data format
- 100ms polling interval for smooth tracking

---

## 🔌 API Endpoints

### Laptop Tracker Server (`localhost:5002`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/orientation` | GET | Get current tracking data (yaw, pitch, face_detected) |
| `/laptop_feed` | GET | Live video feed from laptop camera with tracking overlay |

### Raspberry Pi Server (`192.168.1.100:5000`) - In Development

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/video_feed` | GET | Live video feed from Pi camera |
| `/orientation` | POST | Receive orientation data from laptop |

---

## ⚙️ Configuration

### Laptop Tracker Configuration

Edit `laptop/main.py` to configure:
- Camera device ID
- Server host/port
- Tracking sensitivity
- Calibration parameters

### Frontend Configuration

Edit `frontend/src/App.js` to configure:
- Backend URL (default: `localhost:5002`)
- Raspberry Pi IP (default: `192.168.1.100`)
- Polling intervals
- UI settings

---

## 🐛 Troubleshooting

### Python Version Issues
```bash
# Verify Python 3.12 is installed
py -3.12 --version

# If not installed, download from python.org
# Ensure you select Python 3.12.x specifically
```

### MediaPipe Import Errors
```bash
# Reinstall MediaPipe with Python 3.12
py -3.12 -m pip uninstall mediapipe
py -3.12 -m pip install mediapipe
```

### Camera Access Issues
- Ensure no other application is using the camera
- Check camera permissions in your OS settings
- Try different camera indices in the code (0, 1, 2, etc.)

### Connection Issues
- Verify the laptop tracker is running before starting the frontend
- Check firewall settings allow localhost connections
- Ensure ports 3000, 5002, and 5000 are not in use

---

## 🚧 Current Status

### ✅ Completed
- Face orientation tracking system
- Web dashboard with live video feeds
- Real-time data visualization

### 🔨 In Development
- Raspberry Pi camera integration
- Pi-to-laptop communication
- Distributed processing architecture
- Multi-device synchronization

### 📋 Planned Features
- Recording and playback
- Analytics dashboard
- Multi-user support
- Mobile app interface
- Machine learning improvements

---

## 👥 Team

**Team Name** - DurHackX 2025

Built with ❤️ for DurHackX 2025

---

## 📝 License

This project was created for DurHackX 2025.

---

## 🙏 Acknowledgments

- **DurHackX 2025** for the opportunity and inspiration
- **Google MediaPipe** for powerful computer vision tools
- **React** team for the excellent framework
- All open-source contributors whose libraries made this possible

---

<div align="center">

**Built at DurHackX 2025** 🚀

*Pushing the boundaries of computer vision and human-computer interaction*

</div>