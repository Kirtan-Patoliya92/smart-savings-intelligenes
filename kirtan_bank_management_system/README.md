# Kirtan Bank Management System

A full-stack banking management project based on the original Python bank-management program by Kirtan Patoliya.

## Stack

- Python
- Flask
- SQLite
- HTML
- CSS
- Vanilla JavaScript
- Werkzeug password hashing

## Features

- Create bank account
- Automatic unique account number
- 4-digit PIN validation
- Secure hashed PIN storage
- Login/logout sessions
- Deposit money
- Withdraw money
- Insufficient-balance protection
- Profile editing
- Account deletion
- Transaction history
- CSV statement download
- Responsive professional dashboard

## Run

```bash
python -m venv venv
```

macOS/Linux:
```bash
source venv/bin/activate
```

Windows:
```bash
venv\Scripts\activate
```

Install:
```bash
pip install -r requirements.txt
```

Start:
```bash
python app.py
```

Open:
```text
http://127.0.0.1:5000
```

For another device on the same Wi-Fi, the app already binds to `0.0.0.0`. Use the computer's local IP, for example:

```text
http://192.168.1.5:5000
```

## Important

This is an educational/demo banking application, not a real banking system. Before production use, you would need proper secret management, HTTPS, CSRF protection, stronger authentication, authorization, audit controls, rate limiting, secure deployment, database backups, encryption, compliance controls and financial transaction safeguards.

## Credit

Designed and developed as a learning project by **Kirtan Patoliya**.
