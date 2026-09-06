from getpass import getpass

from pwdlib import PasswordHash

from app.database import SessionLocal
from app.models import AdminUser


password_hash = PasswordHash.recommended()

db = SessionLocal()

username = input("Enter admin username: ").strip()
password = getpass("Enter admin password: ")
confirm_password = getpass("Confirm admin password: ")

if not username:
    print("Username cannot be empty.")
    db.close()
    raise SystemExit

if not password:
    print("Password cannot be empty.")
    db.close()
    raise SystemExit

if password != confirm_password:
    print("Passwords do not match.")
    db.close()
    raise SystemExit

existing_admin = (
    db.query(AdminUser)
    .filter(AdminUser.username == username)
    .first()
)

if existing_admin:
    print("An admin with this username already exists.")
    db.close()
    raise SystemExit

hashed_password = password_hash.hash(password)

admin = AdminUser(
    username=username,
    password_hash=hashed_password
)

db.add(admin)
db.commit()

print(f"Admin user '{username}' created successfully.")

db.close()