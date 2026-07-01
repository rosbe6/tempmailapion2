import sqlite3
import os
import uuid
from datetime import datetime, timedelta

DATABASE_PATH = "tempmail.db"

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Tabla de direcciones temporales
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address_id TEXT UNIQUE NOT NULL,
            full_address TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Tabla de correos (con referencia a la dirección)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address_id TEXT NOT NULL,
            email_to TEXT NOT NULL,
            email_from TEXT NOT NULL,
            subject TEXT,
            body_text TEXT,
            body_html TEXT,
            full_content TEXT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read BOOLEAN DEFAULT 0,
            FOREIGN KEY (address_id) REFERENCES temp_addresses(address_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def generate_temp_address(custom_name):
    """Genera una dirección temporal con nombre personalizado"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    address_id = custom_name.lower().strip()
    full_address = f"{address_id}@apionbot.com"
    expires_at = datetime.now() + timedelta(hours=1)
    
    try:
        cursor.execute('''
            INSERT INTO temp_addresses (address_id, full_address, expires_at)
            VALUES (?, ?, ?)
        ''', (address_id, full_address, expires_at))
        conn.commit()
        conn.close()
        return {
            "address_id": address_id,
            "full_address": full_address,
            "expires_at": expires_at.isoformat()
        }
    except sqlite3.IntegrityError:
        conn.close()
        return {"error": "Esta dirección ya existe"}

def get_temp_address(address_id):
    """Obtiene una dirección temporal"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM temp_addresses WHERE address_id = ?', (address_id,))
    address = cursor.fetchone()
    conn.close()
    
    return dict(address) if address else None

def save_email(address_id, email_to, email_from, subject, body_text, body_html, full_content):
    """Guarda un correo vinculado a una dirección"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO emails (address_id, email_to, email_from, subject, body_text, body_html, full_content)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (address_id, email_to, email_from, subject, body_text, body_html, full_content))
    
    conn.commit()
    email_id = cursor.lastrowid
    conn.close()
    
    return email_id

def get_emails_by_address(address_id):
    """Obtiene todos los correos de una dirección"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM emails WHERE address_id = ? ORDER BY received_at DESC', (address_id,))
    emails = cursor.fetchall()
    conn.close()
    
    return [dict(email) for email in emails]

def get_email_by_id(email_id):
    """Obtiene un correo específico"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM emails WHERE id = ?', (email_id,))
    email = cursor.fetchone()
    conn.close()
    
    return dict(email) if email else None

def mark_email_as_read(email_id):
    """Marca un correo como leído"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE emails SET read = 1 WHERE id = ?', (email_id,))
    conn.commit()
    conn.close()

def delete_email(email_id):
    """Elimina un correo"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM emails WHERE id = ?', (email_id,))
    conn.commit()
    conn.close()

def clear_emails_by_address(address_id):
    """Limpia todos los correos de una dirección"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM emails WHERE address_id = ?', (address_id,))
    conn.commit()
    conn.close()

if not os.path.exists(DATABASE_PATH):
    init_db()