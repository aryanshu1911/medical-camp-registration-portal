from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from pwdlib import PasswordHash

from app.database import Base, engine, SessionLocal
from app.models.camp import Camp
from app.models.registration import Registration
from app.models.admin_user import AdminUser


app = FastAPI(title="Medical Camp Registration Portal")


# Static files
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)


# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="medical-camp-development-secret"
)


# Create database tables
Base.metadata.create_all(bind=engine)


# Templates
templates = Jinja2Templates(directory="app/templates")


# Password hashing
password_hash = PasswordHash.recommended()


# Database dependency
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# Admin authentication dependency
def require_admin(
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user_id = request.session.get("admin_user_id")

    if not admin_user_id:
        raise HTTPException(
            status_code=303,
            headers={"Location": "/admin/login"}
        )

    admin = (
        db.query(AdminUser)
        .filter(AdminUser.id == admin_user_id)
        .first()
    )

    if not admin:
        request.session.clear()

        raise HTTPException(
            status_code=303,
            headers={"Location": "/admin/login"}
        )

    return admin


# =========================
# Public Routes
# =========================

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


@app.get("/camps")
def camps(
    request: Request,
    db: Session = Depends(get_db)
):
    camps = db.query(Camp).all()

    return templates.TemplateResponse(
        request=request,
        name="camps.html",
        context={
            "camps": camps
        }
    )


@app.get("/registration")
def registration(
    request: Request,
    db: Session = Depends(get_db)
):
    camps = db.query(Camp).all()

    error = request.session.pop("error", None)
    form_data = request.session.pop("form_data", {})

    if not form_data:
        camp_id = request.query_params.get("camp_id")

        if camp_id:
            try:
                form_data["camp_id"] = int(camp_id)
            except ValueError:
                pass

    return templates.TemplateResponse(
        request=request,
        name="registration.html",
        context={
            "camps": camps,
            "error": error,
            "form_data": form_data
        }
    )


@app.post("/registration")
def submit_registration(
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    contact_number: str = Form(...),
    camp_id: int = Form(...),
    db: Session = Depends(get_db)
):
    # Validate name
    name = name.strip()

    if not name:
        request.session["error"] = "Name cannot be empty."

        request.session["form_data"] = {
            "name": name,
            "age": age,
            "contact_number": contact_number,
            "camp_id": camp_id
        }

        return RedirectResponse(
            url="/registration",
            status_code=303
        )

    # Validate age
    if age < 1 or age > 120:
        request.session["error"] = "Age must be between 1 and 120."

        request.session["form_data"] = {
            "name": name,
            "age": age,
            "contact_number": contact_number,
            "camp_id": camp_id
        }

        return RedirectResponse(
            url="/registration",
            status_code=303
        )

    # Validate contact number
    if not contact_number.isdigit() or len(contact_number) != 10:
        request.session["error"] = (
            "Contact number must contain exactly 10 digits."
        )

        request.session["form_data"] = {
            "name": name,
            "age": age,
            "contact_number": contact_number,
            "camp_id": camp_id
        }

        return RedirectResponse(
            url="/registration",
            status_code=303
        )

    # Check that the selected camp exists
    camp = (
        db.query(Camp)
        .filter(Camp.id == camp_id)
        .first()
    )

    if not camp:
        request.session["error"] = (
            "Selected medical camp does not exist."
        )

        request.session["form_data"] = {
            "name": name,
            "age": age,
            "contact_number": contact_number,
            "camp_id": camp_id
        }

        return RedirectResponse(
            url="/registration",
            status_code=303
        )

    # Create registration
    registration = Registration(
        name=name,
        age=age,
        contact_number=contact_number,
        camp_id=camp_id
    )

    db.add(registration)
    db.commit()
    db.refresh(registration)

    return templates.TemplateResponse(
        request=request,
        name="registration_success.html",
        context={
            "registration": registration
        }
    )


@app.get("/contact")
def contact(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="contact.html",
        context={}
    )


# =========================
# Admin Authentication
# =========================

@app.get("/admin/login")
def admin_login(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={}
    )


@app.post("/admin/login")
def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    username = username.strip()

    admin = (
        db.query(AdminUser)
        .filter(AdminUser.username == username)
        .first()
    )

    if not admin or not password_hash.verify(
        password,
        admin.password_hash
    ):
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={
                "error": "Invalid username or password."
            },
            status_code=401
        )

    # Store only the admin user's ID in the session
    request.session["admin_user_id"] = admin.id

    return RedirectResponse(
        url="/admin/registrations",
        status_code=303
    )


# =========================
# Protected Admin Routes
# =========================

@app.get("/admin/camps/new")
def add_camp_form(
    request: Request,
    admin: AdminUser = Depends(require_admin)
):
    return templates.TemplateResponse(
        request=request,
        name="admin_add_camp.html",
        context={}
    )


@app.post("/admin/camps/new")
def add_camp(
    request: Request,
    name: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
    description: str = Form(""),
    available_slots: int = Form(...),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    name = name.strip()
    location = location.strip()
    description = description.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Camp name cannot be empty."
        )

    if not location:
        raise HTTPException(
            status_code=400,
            detail="Camp location cannot be empty."
        )

    if available_slots < 1:
        raise HTTPException(
            status_code=400,
            detail="Available slots must be at least 1."
        )

    camp = Camp(
        name=name,
        date=date,
        location=location,
        description=description,
        available_slots=available_slots,
        status="scheduled"
    )

    db.add(camp)
    db.commit()

    return RedirectResponse(
        url="/admin/camps",
        status_code=303
    )


@app.get("/admin/camps")
def admin_camps(
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    camps = db.query(Camp).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_camps.html",
        context={
            "camps": camps
        }
    )


@app.get("/admin/registrations")
def admin_registrations(
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    registrations = db.query(Registration).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_registrations.html",
        context={
            "registrations": registrations
        }
    )


@app.post("/admin/registrations/{registration_id}/delete")
def delete_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    registration = (
        db.query(Registration)
        .filter(Registration.id == registration_id)
        .first()
    )

    if not registration:
        return RedirectResponse(
            url="/admin/registrations",
            status_code=303
        )

    db.delete(registration)
    db.commit()

    return RedirectResponse(
        url="/admin/registrations",
        status_code=303
    )


@app.get("/admin/registrations/{registration_id}/edit")
def edit_registration(
    registration_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    registration = (
        db.query(Registration)
        .filter(Registration.id == registration_id)
        .first()
    )

    if not registration:
        return RedirectResponse(
            url="/admin/registrations",
            status_code=303
        )

    camps = db.query(Camp).all()

    return templates.TemplateResponse(
        request=request,
        name="edit_registration.html",
        context={
            "registration": registration,
            "camps": camps
        }
    )


@app.post("/admin/registrations/{registration_id}/edit")
def update_registration(
    registration_id: int,
    name: str = Form(...),
    age: int = Form(...),
    contact_number: str = Form(...),
    camp_id: int = Form(...),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    registration = (
        db.query(Registration)
        .filter(Registration.id == registration_id)
        .first()
    )

    if not registration:
        return RedirectResponse(
            url="/admin/registrations",
            status_code=303
        )

    registration.name = name.strip()
    registration.age = age
    registration.contact_number = contact_number.strip()
    registration.camp_id = camp_id

    db.commit()

    return RedirectResponse(
        url="/admin/registrations",
        status_code=303
    )