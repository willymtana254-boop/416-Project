"""Creates a clinician account, or promotes an existing account to clinician.

Clinician accounts can NOT be created from the website, so nobody can give
themselves access to other people's shared assessments. Run this yourself:

    python create_clinician.py

It asks for an email, name and password. If the email already has an
account, the account is promoted instead (its password is left unchanged).
Use the same MEDITECH_DB setting as the app, if you set one."""

import argparse
import getpass
import os
import sys

from dotenv import load_dotenv

load_dotenv()

import auth
import db


def create_or_promote(conn, email: str, name: str, password: str):
    """Returns ("created" | "promoted" | "already", user_id)."""
    existing = db.get_user_by_email(conn, email)
    if existing is not None:
        if existing["role"] == "clinician":
            return "already", existing["id"]
        db.set_role(conn, existing["id"], "clinician")
        return "promoted", existing["id"]
    uid = db.create_user(conn, email, name, auth.hash_password(password), role="clinician")
    return "created", uid


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create or promote a clinician account.")
    parser.add_argument("--email", help="clinician email address")
    parser.add_argument("--name", help="clinician display name")
    args = parser.parse_args(argv)

    email = auth.clean_email(args.email or input("Email: "))
    if not email:
        sys.exit("That is not a valid email address.")

    path = db.default_db_path()
    db.init_db(path)
    conn = db.connect(path)
    try:
        existing = db.get_user_by_email(conn, email)
        if existing is not None:
            result, uid = create_or_promote(conn, email, existing["name"], "")
        else:
            name = auth.clean_name(args.name or input("Name: "))
            if not name:
                sys.exit("Please enter a name (1-80 characters).")
            password = getpass.getpass("Password (not shown): ")
            if getpass.getpass("Repeat password: ") != password:
                sys.exit("The passwords do not match.")
            if auth.check_password(password, email):
                sys.exit("Choose a stronger password (at least 8 characters, not a common one).")
            result, uid = create_or_promote(conn, email, name, password)
    finally:
        conn.close()

    messages = {
        "created": "Created clinician account",
        "promoted": "Promoted existing account to clinician",
        "already": "That account is already a clinician",
    }
    print(f"{messages[result]}: {email} (id {uid}) in {path}")


if __name__ == "__main__":
    main()
