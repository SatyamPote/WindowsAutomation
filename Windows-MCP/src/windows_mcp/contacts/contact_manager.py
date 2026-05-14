import json
import os
import logging

logger = logging.getLogger("contact_manager")

CONTACTS_FILE = os.path.join(os.getcwd(), "contacts.json")

def load_contacts() -> dict:
    if not os.path.exists(CONTACTS_FILE):
        return {}
    try:
        with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load contacts: {e}")
        return {}

def save_contacts(contacts: dict):
    try:
        with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(contacts, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save contacts: {e}")

def normalize_name(name: str) -> str:
    return name.strip().lower()

def add_contact(name: str, phone: str) -> str:
    contacts = load_contacts()
    norm = normalize_name(name)
    contacts[norm] = {
        "name": name.strip(),
        "phone": phone.strip()
    }
    save_contacts(contacts)
    logger.info(f"Added contact: {name} ({phone})")
    return f"Contact '{name}' added successfully."

def remove_contact(name: str) -> str:
    contacts = load_contacts()
    norm = normalize_name(name)
    if norm in contacts:
        del contacts[norm]
        save_contacts(contacts)
        logger.info(f"Removed contact: {name}")
        return f"Contact '{name}' removed successfully."
    return f"Contact '{name}' not found."

def get_contact(name: str) -> dict:
    contacts = load_contacts()
    norm = normalize_name(name)
    # Direct match
    if norm in contacts:
        return contacts[norm]
    # Partial match
    for k, v in contacts.items():
        if norm in k or k in norm:
            return v
    return None

def format_contacts() -> str:
    contacts = load_contacts()
    if not contacts:
        return "No contacts found."
    res = "📋 *Saved Contacts:*\n"
    for v in contacts.values():
        res += f"• `{v['name']}`: `{v['phone']}`\n"
    return res
