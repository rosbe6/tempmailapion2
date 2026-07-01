import os
import re
from email.parser import Parser
import database

MAIL_FILE = "/var/mail/catchall"
processed_emails = set()

def parse_email_content(content):
    """Parsea el contenido de un correo"""
    parser = Parser()
    msg = parser.parsestr(content)
    
    email_to = msg.get('X-Original-To', msg.get('To', 'unknown'))
    email_from = msg.get('From', 'unknown')
    subject = msg.get('Subject', '(sin asunto)')
    
    body_text = ""
    body_html = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            
            if content_type == "text/plain" and not body_text:
                try:
                    body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    body_text = part.get_payload()
            
            elif content_type == "text/html" and not body_html:
                try:
                    body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    body_html = part.get_payload()
    else:
        try:
            body_text = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            body_text = msg.get_payload()
    
    return {
        'email_to': email_to.strip(),
        'email_from': email_from.strip(),
        'subject': subject.strip(),
        'body_text': body_text.strip(),
        'body_html': body_html.strip()
    }

def read_mbox_file():
    """Lee el archivo mbox"""
    if not os.path.exists(MAIL_FILE):
        return []
    
    try:
        with open(MAIL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return []
    
    emails = re.split(r'\nFrom ', content)
    if emails:
        emails[0] = emails[0].lstrip('From ')
    emails = [emails[0]] + ['From ' + e for e in emails[1:]]
    
    return [e.strip() for e in emails if e.strip()]

def import_new_emails():
    """Importa correos del archivo mbox"""
    global processed_emails
    
    emails_content = read_mbox_file()
    new_count = 0
    
    for email_content in emails_content:
        email_hash = hash(email_content[:200])
        
        if email_hash in processed_emails:
            continue
        
        try:
            parsed = parse_email_content(email_content)
            
            # Extraer el address_id del email_to (ej: abc123@apionbot.com -> abc123)
            email_to = parsed['email_to']
            if '@apionbot.com' in email_to:
                address_id = email_to.split('@')[0]
            else:
                address_id = "catchall"  # Para correos a direcciones desconocidas
            
            database.save_email(
                address_id=address_id,
                email_to=email_to,
                email_from=parsed['email_from'],
                subject=parsed['subject'],
                body_text=parsed['body_text'],
                body_html=parsed['body_html'],
                full_content=email_content
            )
            processed_emails.add(email_hash)
            new_count += 1
            print(f"✓ Correo: {parsed['subject'][:40]} -> {address_id}")
        except Exception as e:
            print(f"Error: {e}")
    
    return new_count