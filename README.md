🍽️ RestoKyiv — Interactive Restaurant Discovery Platform

RestoKyiv is a full-stack web application built with Flask that allows users to discover restaurants on an interactive map, leave reviews, and explore dining options in Kyiv. The project focuses on security, usability, and modern web development practices.

🚀 Features
🗺️ Map-Based Restaurant Discovery
Interactive map interface
Geolocation-based restaurant search
Fast navigation through locations in Kyiv
🔐 Secure Authentication System
User registration and login
Password hashing using bcrypt
Session-based authentication
CSRF protection enabled
⭐ Review System
Add restaurant reviews
Anonymous review option
Edit and delete own reviews
Rating system for restaurants
🌐 Multilingual Support
Supports multiple languages
Easy language switching
🧱 Security Features
SQLAlchemy ORM (prevents SQL injection)
CSRF protection
Rate limiting (anti-abuse protection)
Secure headers
Input validation and sanitization
Privacy-aware geolocation handling
🛠️ Tech Stack
Backend
Python 3
Flask
Flask-SQLAlchemy
Flask-Login
Flask-WTF
Frontend
HTML5 / CSS3
JavaScript
Leaflet.js (maps)
Database
SQLite (development)
PostgreSQL (optional production setup)
📁 Project Structure
RestoKyiv/ │ ├── app.py # Main Flask application ├── models.py # Database models ├── forms.py # WTForms (if used) ├── config.py # Configuration settings │ ├── templates/ # HTML templates ├── static/ # CSS, JS, images │ ├── instance/ # Database files ├── migrations/ # DB migrations (if used) │ ├── requirements.txt # Dependencies
