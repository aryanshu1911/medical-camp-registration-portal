# Medical Camp Registration Portal

A full-stack web application developed as part of the **Software Development Internship at Sysslan IT Solutions**.

The portal allows users to view medical camps, check availability, and register online. An authenticated admin panel is provided for managing camps and participant registrations.

## Features

- Responsive medical camp listing
- Camp details, availability, and status
- Online registration with server-side validation
- Automatic slot/capacity management
- Registration confirmation
- Admin authentication and logout
- Admin camp management
  - Add, edit, cancel, complete, reopen, and delete camps
- Admin registration management
  - View, edit, move, and delete registrations
- SQLite database with SQLAlchemy ORM
- Responsive and user-friendly interface

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy
- **Frontend:** HTML5, CSS3, Jinja2
- **Database:** SQLite
- **Authentication:** Session-based authentication, Argon2 password hashing
- **Server:** Uvicorn

## Project Structure

```text
medical-camp-portal/
├── app/
│   ├── models/
│   ├── templates/
│   ├── static/
│   ├── database.py
│   └── main.py
├── create_admin.py
├── medical_camp.db
├── requirements.txt
├── .gitignore
└── README.md
```

## Setup

1. Clone the repository
   ```shell
   git clone https://github.com/aryanshu1911/medical-camp-registration-portal.git
   cd medical-camp-registration-portal
   ```
2. Create and activate a virtual environment
   ```shell
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies
   ```shell
   pip install -r requirements.txt
   ```
4. Create an admin account
   ```shell
   python create_admin.py
   ```
5. Start the application
   ```shell
   uvicorn app.main:app --reload
   ```

**Open:**
http://127.0.0.1:8000

## Admin Access

Use the following demo credentials to access the admin panel:

**Username:** `admin`
**Password:** `admin123`

Admin login:

```text
http://127.0.0.1:8000/admin/login
```

## Main Workflow

```text
View Camps
    ↓
Select Camp
    ↓
Submit Registration
    ↓
Validate & Store Data
    ↓
Update Available Slots
    ↓
Registration Confirmation
```

## Task Coverage

The project covers the assigned internship requirements across:

- **Level 1:** Project setup, pages, and navigation
- **Level 2:** Camp information and responsive UI
- **Level 3:** Registration and validation
- **Level 4:** Database storage and admin management
- **Level 5:** UI polish and end-to-end testing

## Note

The project uses synthetic/demo data only and does not contain real patient or medical records.

## Author

**Aryanshu Singh**
Software Development Intern — Sysslan IT Solutions