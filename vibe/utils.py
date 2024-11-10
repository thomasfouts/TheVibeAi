"""VibeAI helper functions"""
import uuid
import hashlib

def find_user_by_email(email):
    #TODO
    return

def generate_reset_token(email):
    #TODO
    return

def save_reset_token(email, reset_token):
    #TODO
    return

def send_reset_email(email, reset_token):
    #TODO
    return

def verify_reset_token(token):
    #TODO
    return

def update_user_password(email, password):
    #TODO
    return

def hash_password(password):
    """Hash password."""
    algorithm = 'sha512'
    salt = uuid.uuid4().hex
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + password
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    return "$".join([algorithm, salt, password_hash])


def verify_password(password, password_hash):
    """Check password."""
    algorithm, salt, stored_hash = password_hash.split('$')
    hash_obj = hashlib.new(algorithm)
    salted_input_password = salt + password
    hash_obj.update(salted_input_password.encode('utf-8'))
    input_hash = hash_obj.hexdigest()
    return stored_hash == input_hash