<div align="center">
<pre>
  _____         _      _          
 |_   _|       (_)    | |         
   | | __ _ ___ _  ___| | ___   _ 
   | |/ _` / __| |/ _ \ |/ / | | |
   | | (_| \__ \ |  __/   <| |_| |
   \_/\__,_|___/_|\___|_|\_\\__, |
                             __/ |
                            |___/ 
</pre>

# 🛣️ Tarieky (طريقي) - Empowering Citizens, Transforming Cities.

[![Django](https://img.shields.io/badge/Backend-Django-092E20?style=for-the-badge&logo=django&logoColor=white)]()
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)]()
[![Docker](https://img.shields.io/badge/DevOps-Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)]()

*An Advanced Graduation Project redefining civic engagement and urban maintenance through scalable technology.*

---

</div>

## 🌌 The Vision & Mission

In rapidly growing cities, infrastructure maintenance can't rely solely on manual patrols. **Tarieky (طريقي)** shifts the paradigm by crowd-sourcing urban oversight. We equip every citizen with a digital megaphone to report potholes, broken streetlights, missing signs, and road hazards instantly. 

By routing these reports directly to the relevant local authorities (Supervisors) based on precise geographic data, Tarieky accelerates repairs and improves city infrastructure.

---

## 🏗️ Core Features

### 1. The Citizen Experience
- **Frictionless Onboarding:** Users sign up securely using **OTP (One Time Password)** verification sent to their email.
- **Context-Rich Reporting:** Citizens can report issues (e.g., `lighting`, `pothole`, `road_damage`), attach photos, and provide exact `latitude` and `longitude` coordinates.
- **Real-time Notifications:** Integrated with **Firebase Cloud Messaging (FCM)** to keep citizens informed when their report status is updated.

### 2. The Supervisor Workflow
- **Geo-Fenced Authority:** Supervisors manage issues assigned to their specific `governorate` and `city`.
- **Lifecycle Management:** Supervisors can update issue statuses: `Pending` ➡️ `In Progress` ➡️ `Resolved` (or `Rejected`).

---

## 🛠️ Tech Stack & Architecture

- **Backend Framework:** Django & Django REST Framework (DRF)
- **Authentication:** JWT (JSON Web Tokens) with custom OTP flows.
- **Database:** SQLite (Local) / PostgreSQL (Production via Neon DB).
- **Deployment:** Dockerized application configured for platforms like Railway.

---

## 🚀 Running the Project Locally

### Prerequisites
- Python 3.11+
- Docker (optional, for containerized run)

### Local Setup (Without Docker)
```bash
# 1. Clone the repository
git clone <your-repo-url>
cd tarieky

# 2. Create a virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt

# 3. Apply database migrations
python manage.py migrate

# 4. Start the development server
python manage.py runserver
```

### Docker Setup
```bash
# Build and run the Docker container
docker build -t tarieky-backend .
docker run -p 8000:8000 tarieky-backend
```

---

## 🎓 About This Graduation Project

Tarieky represents a complete backend solution for modern urban maintenance reporting. It demonstrates the implementation of secure REST APIs, role-based access control, geospatial data handling, and push notification integrations.

<div align="center">
  <br>
  <b>Engineered to make a difference. Designed to save lives.</b><br>
  <i>Built with ❤️ by the Tarieky Team</i>
</div>
