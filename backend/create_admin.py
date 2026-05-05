"""
Crea el primer usuario admin.
Uso: python create_admin.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models.user import User
from app.core.security import hash_password

create_db_and_tables()

email    = input("Email admin: ").strip()
name     = input("Nombre: ").strip()
password = input("Contraseña: ").strip()

with Session(engine) as session:
    if session.exec(select(User).where(User.email == email)).first():
        print("❌  Ya existe un usuario con ese email.")
    else:
        user = User(email=email, name=name, password_hash=hash_password(password), role="admin")
        session.add(user)
        session.commit()
        print(f"✓  Usuario admin creado: {email}")
