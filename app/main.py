import os
from datetime import datetime

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
SESSION_SECRET = os.getenv(
    "SESSION_SECRET",
    "medical-camp-development-secret"
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET
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
    camps = (
        db.query(Camp)
        .filter(
            Camp.status == "scheduled",
            Camp.available_slots > 0
        )
        .all()
    )

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
            "camp_id": camp_id
        }

        return RedirectResponse(
            url="/registration",
            status_code=303
        )

    # Validate contact number
    contact_number = contact_number.strip()

    if not contact_number.isdigit() or len(contact_number) != 10:
        request.session["error"] = (
            "Contact number must contain exactly 10 digits."
        )

        request.session["form_data"] = {
            "name": name,
            "age": age,
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
            "camp_id": camp_id
        }

        return RedirectResponse(
            url="/registration",
            status_code=303
        )

    # Registration is allowed only for scheduled camps
    if camp.status != "scheduled":
        request.session["error"] = (
            "Registration is not available for this medical camp."
        )

        request.session["form_data"] = {
            "name": name,
            "age": age,
            "camp_id": camp_id
        }

        return RedirectResponse(
            url="/registration",
            status_code=303
        )

    # Check camp capacity
    if camp.available_slots <= 0:
        request.session["error"] = (
            "This medical camp is fully booked."
        )

        request.session["form_data"] = {
            "name": name,
            "age": age,
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

    # Consume one available slot
    camp.available_slots -= 1

    db.add(registration)

    try:
        db.commit()
        db.refresh(registration)
    except Exception:
        db.rollback()

        request.session["error"] = (
            "Registration could not be completed. Please try again."
        )

        request.session["form_data"] = {
            "name": name,
            "age": age,
            "camp_id": camp_id
        }

        return RedirectResponse(
            url="/registration",
            status_code=303
        )

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

@app.get("/admin")
def admin_home(
    request: Request,
    admin: AdminUser = Depends(require_admin)
):
    return RedirectResponse(
        url="/admin/camps",
        status_code=303
    )


@app.get("/admin/login")
def admin_login(request: Request):
    error = request.session.pop("admin_login_error", None)

    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={
            "error": error
        }
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
        url="/admin/camps",
        status_code=303
    )


@app.get("/admin/logout")
def admin_logout(request: Request):
    request.session.clear()

    return RedirectResponse(
        url="/admin/login",
        status_code=303
    )


# =========================
# Protected Admin Routes
# =========================

@app.get("/admin/camps")
def admin_camps(
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    camps = (
        db.query(Camp)
        .order_by(Camp.id)
        .all()
    )

    success = request.session.pop("admin_success", None)
    error = request.session.pop("admin_error", None)

    return templates.TemplateResponse(
        request=request,
        name="admin_camps.html",
        context={
            "camps": camps,
            "success": success,
            "error": error
        }
    )


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
    date = date.strip()
    location = location.strip()
    description = description.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Camp name cannot be empty."
        )

    if not date:
        raise HTTPException(
            status_code=400,
            detail="Camp date cannot be empty."
        )
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Camp date must be in YYYY-MM-DD format."
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

    request.session["admin_success"] = "Medical camp created successfully."

    return RedirectResponse(
        url="/admin/camps",
        status_code=303
    )


@app.get("/admin/camps/{camp_id}/edit")
def edit_camp_form(
    camp_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    camp = (
        db.query(Camp)
        .filter(Camp.id == camp_id)
        .first()
    )

    if not camp:
        raise HTTPException(
            status_code=404,
            detail="Medical camp not found."
        )

    registration_count = (
        db.query(Registration)
        .filter(Registration.camp_id == camp.id)
        .count()
    )

    return templates.TemplateResponse(
        request=request,
        name="admin_edit_camp.html",
        context={
            "camp": camp,
            "registration_count": registration_count
        }
    )


@app.post("/admin/camps/{camp_id}/edit")
def edit_camp(
    camp_id: int,
    request: Request,
    name: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
    description: str = Form(""),
    available_slots: int = Form(...),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    camp = (
        db.query(Camp)
        .filter(Camp.id == camp_id)
        .first()
    )

    if not camp:
        raise HTTPException(
            status_code=404,
            detail="Medical camp not found."
        )

    name = name.strip()
    date = date.strip()
    location = location.strip()
    description = description.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Camp name cannot be empty."
        )

    if not date:
        raise HTTPException(
            status_code=400,
            detail="Camp date cannot be empty."
        )
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Camp date must be in YYYY-MM-DD format."
            )

    if not location:
        raise HTTPException(
            status_code=400,
            detail="Camp location cannot be empty."
        )

    if available_slots < 0:
        raise HTTPException(
            status_code=400,
            detail="Available slots cannot be negative."
        )

    camp.name = name
    camp.date = date
    camp.location = location
    camp.description = description
    camp.available_slots = available_slots

    db.commit()

    request.session["admin_success"] = "Medical camp updated successfully."

    return RedirectResponse(
        url="/admin/camps",
        status_code=303
    )


@app.post("/admin/camps/{camp_id}/status")
def update_camp_status(
    camp_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    camp = (
        db.query(Camp)
        .filter(Camp.id == camp_id)
        .first()
    )

    if not camp:
        raise HTTPException(
            status_code=404,
            detail="Medical camp not found."
        )

    allowed_statuses = {
        "scheduled",
        "cancelled",
        "completed"
    }

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid camp status."
        )

    # Do not reopen a completed camp through the simple status action.
    if camp.status == "completed" and status != "completed":
        raise HTTPException(
            status_code=400,
            detail="A completed camp cannot be reopened or cancelled."
        )

    # A scheduled camp can be cancelled or completed.
    # A cancelled camp can be reopened.
    camp.status = status

    db.commit()

    return RedirectResponse(
        url="/admin/camps",
        status_code=303
    )


@app.post("/admin/camps/{camp_id}/delete")
def delete_camp(
    camp_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    camp = (
        db.query(Camp)
        .filter(Camp.id == camp_id)
        .first()
    )

    if not camp:
        request.session["admin_error"] = "Medical camp not found."

        return RedirectResponse(
            url="/admin/camps",
            status_code=303
        )

    registration_count = (
        db.query(Registration)
        .filter(Registration.camp_id == camp.id)
        .count()
    )

    if registration_count > 0:
        request.session["admin_error"] = (
            "This camp cannot be deleted because it has registrations."
        )

        return RedirectResponse(
            url="/admin/camps",
            status_code=303
        )

    db.delete(camp)
    db.commit()

    request.session["admin_success"] = (
        "Medical camp deleted successfully."
    )

    return RedirectResponse(
        url="/admin/camps",
        status_code=303
    )


# =========================
# Admin Registration Routes
# =========================

@app.get("/admin/registrations")
def admin_registrations(
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    registrations = (
        db.query(Registration)
        .order_by(Registration.id)
        .all()
    )

    success = request.session.pop("admin_success", None)
    error = request.session.pop("admin_error", None)

    return templates.TemplateResponse(
        request=request,
        name="admin_registrations.html",
        context={
            "registrations": registrations,
            "success": success,
            "error": error
        }
    )


@app.post("/admin/registrations/{registration_id}/delete")
def delete_registration(
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
        request.session["admin_error"] = (
            "Registration not found."
        )

        return RedirectResponse(
            url="/admin/registrations",
            status_code=303
        )

    camp = (
        db.query(Camp)
        .filter(Camp.id == registration.camp_id)
        .first()
    )

    # Restore the consumed slot.
    if camp:
        camp.available_slots += 1

    db.delete(registration)

    try:
        db.commit()
    except Exception:
        db.rollback()

        request.session["admin_error"] = (
            "Registration could not be deleted."
        )

        return RedirectResponse(
            url="/admin/registrations",
            status_code=303
        )

    request.session["admin_success"] = (
        "Registration deleted successfully."
    )

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
        raise HTTPException(
            status_code=404,
            detail="Registration not found."
        )

    # Validate participant details
    name = name.strip()
    contact_number = contact_number.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name cannot be empty."
        )

    if age < 1 or age > 120:
        raise HTTPException(
            status_code=400,
            detail="Age must be between 1 and 120."
        )

    if not contact_number.isdigit() or len(contact_number) != 10:
        raise HTTPException(
            status_code=400,
            detail="Contact number must contain exactly 10 digits."
        )

    # Find destination camp
    new_camp = (
        db.query(Camp)
        .filter(Camp.id == camp_id)
        .first()
    )

    if not new_camp:
        raise HTTPException(
            status_code=404,
            detail="Selected medical camp does not exist."
        )

    old_camp = (
        db.query(Camp)
        .filter(Camp.id == registration.camp_id)
        .first()
    )

    # If the camp itself is not changing, only update participant data.
    if registration.camp_id == camp_id:

        # Keep the registration valid even if the camp has since
        # become cancelled/completed; changing participant details
        # does not create a new registration.
        registration.name = name
        registration.age = age
        registration.contact_number = contact_number

    else:

        # Destination must accept registrations.
        if new_camp.status != "scheduled":
            raise HTTPException(
                status_code=400,
                detail="The selected medical camp is not accepting registrations."
            )

        if new_camp.available_slots <= 0:
            raise HTTPException(
                status_code=400,
                detail="The selected medical camp is fully booked."
            )

        # Restore the slot consumed by the old camp.
        if old_camp:
            old_camp.available_slots += 1

        # Consume one slot in the new camp.
        new_camp.available_slots -= 1

        registration.camp_id = camp_id
        registration.name = name
        registration.age = age
        registration.contact_number = contact_number

    try:
        db.commit()
    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Registration could not be updated."
        )

    return RedirectResponse(
        url="/admin/registrations",
        status_code=303
    )