# hospitalQ - Smart Queue Management System

 hospitalQ is a smart, real-time queue management system designed to reduce waiting times and optimize patient flow in hospitals and clinics. Built with Python (Flask) and optimized for real-time performance using WebSockets, this system helps administrators manage tokens efficiently while providing patients/users with live updates.

Live Demo: [hospitalq.onrender.com](https://hospitalq.onrender.com)



## 🚀 Features

*   **Real-time Token Operations:** Instant queue updates using `gevent-websocket` for high performance and low latency.
*   **Smart Queue Routing:** Efficient logic to handle, assign, and advance patient queues seamlessly.
*   **Admin Dashboard:** Dedicated interface for hospital administrators to manage queues, call the next token, and monitor traffic.
*   **Database:** Uses PostreSQL (From Neon) for fast data persistence without heavy infrastructure requirements.
*   **Production Ready:** Pre-configured for seamless deployment on platforms like Render using Gunicorn and Gevent.



## 🛠️ Tech Stack

*   **Backend:** Python 3.11+, Flask
*   **Real-time Communication:** Gevent-WebSocket
*   **WSGI Server:** Gunicorn (with Gevent workers)
*   **Frontend:** HTML5, CSS3, JavaScript
*   **Database:** postresql

---

## 📦 Installation & Local Setup

Follow these steps to get the project running locally on your machine:

### 1. Clone the Repository
```bash
git clone [https://github.com/jeromeofficial07/hospitalQ.git](https://github.com/jeromeofficial07/hospitalQ.git)
cd hospitalQ 
```

python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt

Bash
python app.py
The application will be available locally at http://127.0.0.1:5000

🌐 Deployment
This project is configured to deploy easily on Render using the provided render.yaml and gunicorn_config.py.

The production server utilizes Gevent workers to handle asynchronous WebSocket traffic efficiently:

Bash
gunicorn -c gunicorn_config.py app:app
