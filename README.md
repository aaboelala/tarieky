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

# 🛣️ Tarieky (طريقي) - Empowering Citizens, Transforming Cities

[![Django](https://img.shields.io/badge/Backend-Django-092E20?style=for-the-badge&logo=django&logoColor=white)]()
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)]()
[![Jenkins](https://img.shields.io/badge/CI-Jenkins-D24939?style=for-the-badge&logo=jenkins&logoColor=white)]()
[![ArgoCD](https://img.shields.io/badge/CD-ArgoCD-EF7B4D?style=for-the-badge&logo=argo&logoColor=white)]()
[![Kubernetes](https://img.shields.io/badge/Platform-Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)]()
[![Firebase](https://img.shields.io/badge/Notifications-Firebase-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)]()

*An Advanced Platform Engineering & Backend solution redefining urban maintenance reporting through scalable technology and robust DevOps practices.*

---
</div>

## 🌌 Overview

In rapidly growing cities, infrastructure maintenance can't rely solely on manual patrols. **Tarieky (طريقي)** shifts the paradigm by crowd-sourcing urban oversight. We equip every citizen with a digital megaphone to report potholes, broken streetlights, missing signs, and road hazards instantly. 

By routing these reports directly to the relevant local authorities (Supervisors) based on precise geographic data, Tarieky accelerates repairs and improves city infrastructure.

## 🏗️ Application Architecture & Core Features

Tarieky is built on a robust **Django & Django REST Framework (DRF)** backend, providing a scalable API for mobile and web clients.

### 🌟 Key Features
- **Role-Based Workflows:** Distinct experiences for Citizens (reporters) and Supervisors (resolvers).
- **Secure Authentication:** JWT (JSON Web Tokens) with a custom OTP (One Time Password) email verification flow for signup and password resets.
- **Geospatial Processing:** Calculates Haversine distances to find nearby issues and filter reports by exact `latitude`, `longitude`, `city`, and `governorate`.
- **Firebase Cloud Messaging (FCM) Integration:** 
  - Real-time push notifications sent asynchronously when an issue's status changes.
  - Smart broadcasting: Notifies the reporter directly, and optionally broadcasts "City Alerts" to other users in the same region.
- **Tasdeeq (Verification) System:** Citizens can "upvote" or verify existing issues to prioritize them.
- **Production-Ready DB:** SQLite for local dev, seamlessly switching to Neon PostgreSQL in production using `dj-database-url`.

---

## 🚀 DevOps & Platform Engineering

Tarieky is designed with a **Cloud-Native, GitOps-driven DevOps architecture**, demonstrating advanced platform engineering principles. The infrastructure is defined as code and leverages Kubernetes for high availability and scalability.

### 🔄 CI/CD Pipeline Architecture
The CI/CD pipeline is orchestrated using **Jenkins running natively on Kubernetes** with a dynamic, ephemeral agent setup.

1. **Quality & SAST (Parallel Execution):**
   - **Automated Testing:** Runs Python `coverage` to ensure high test quality (fails under 70%).
   - **SonarQube Integration:** Performs Static Application Security Testing (SAST) for code quality and vulnerability scanning.
2. **Software Composition Analysis (SCA):**
   - **Trivy Filesystem Scan:** Scans the codebase for vulnerable dependencies before building.
3. **Secure Rootless Image Build:**
   - Uses **BuildKit daemon (`buildkitd`) in rootless mode** via `buildctl` to construct Docker images securely without requiring Docker socket access.
   - Implements advanced layer caching using GitHub Container Registry (GHCR) to drastically reduce build times.
4. **Image Security Scan:**
   - **Trivy Image Scan:** Scans the built tarball for `HIGH` and `CRITICAL` vulnerabilities.
5. **Secure Publishing:**
   - Uses **Skopeo** to securely copy the image tarball directly to GHCR without a local Docker daemon.
6. **GitOps Manifest Update:**
   - The pipeline updates the Kubernetes `deployment.yaml` with the new image tag and pushes the changes back to the repository (`main` branch) automatically.

### 🚢 Continuous Deployment with ArgoCD
- Follows the **GitOps** philosophy.
- **ArgoCD** continuously monitors the `devops/k8s` directory in the repository.
- Automatically syncs, prunes, and self-heals the application state in the Kubernetes cluster to match the Git repository, ensuring the deployment is always in the desired state.

### 🛡️ Kubernetes Security & Governance
The cluster is hardened using Kubernetes security best practices:
- **Namespaces & RBAC:** Isolated `jenkins` namespace with strict `Role` and `RoleBinding` definitions (Principle of Least Privilege).
- **Network Policies:** Egress filtering to only allow necessary outbound traffic (DNS, HTTPS) and block access to internal cluster subnets.
- **Resource Management:** Configured `ResourceQuota` and `LimitRange` to prevent noisy neighbor problems and ensure predictable scheduling.
- **Security Contexts:** Jenkins controllers and agents run as non-root (`runAsUser: 1000`), drop all capabilities (`capabilities: drop: ["ALL"]`), and enforce `RuntimeDefault` seccomp profiles. Privilege escalation is strictly prohibited.

---

## 🛠️ Running the Project Locally

### Prerequisites
- Python 3.11+
- Docker

### Local Setup
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
# Build the Docker container
docker build -t tarieky-backend .

# Run the container
docker run -p 8000:8000 --env-file .env tarieky-backend
```

---

<div align="center">
  <br>
  <b>Engineered to make a difference. Designed to save lives.</b><br>
  <i>Built with ❤️ by the Tarieky Team</i>
</div>
