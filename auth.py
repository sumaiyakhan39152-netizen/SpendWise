from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, saved_password):
    return check_password_hash(saved_password, password)


def validate_user(name, email, password):
    if not name or not name.strip():
        return False, "Name is required"

    if "@" not in email or "." not in email:
        return False, "Enter a valid email"

    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    return True, "Valid"