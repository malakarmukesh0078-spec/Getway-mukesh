import imaplib
import email
from email.header import decode_header
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, request
import threading
import time
import re
from bs4 import BeautifulSoup

app = Flask(__name__)

# =========================================================================
# FAMPAY CONFIGURATION
# =========================================================================
FAMPAY_EMAIL = "mukeshmalakar00890@gmail.com"
FAMPAY_PASSWORD = "vaqqtegpwyxhoegj"
FAMPAY_SENDER = "no-reply@famapp.in"
FAMPAY_INTERVAL = 2
FAMPAY_DB = "fampay_notice.db"

# =========================================================================
# BINANCE CONFIGURATION
# =========================================================================
BINANCE_EMAIL = "mukkeshff7788@gmail.com"
BINANCE_PASSWORD = "wjlqdeskbtnsltdm"
BINANCE_SENDER = "do-not-reply@ses.binance.com"
BINANCE_INTERVAL = 2
BINANCE_DB = "binance_notice.db"

# =========================================================================
# COMMON HELPERS
# =========================================================================
def clean_html(raw_html):
    """Clean HTML and extract plain text"""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    text = soup.get_text(separator=' ')
    text = ' '.join(text.split())
    return text.strip()

def extract_email_body(msg):
    """Extract and clean email body from message"""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            
            if "attachment" in content_disposition:
                continue
                
            if content_type in ["text/plain", "text/html"]:
                try:
                    payload = part.get_payload(decode=True).decode(errors='ignore')
                    if content_type == "text/html":
                        body = clean_html(payload)
                    else:
                        body = payload.strip()
                    if body:
                        break
                except Exception as e:
                    print(f"Error decoding part: {e}")
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True).decode(errors='ignore')
            content_type = msg.get_content_type()
            if content_type == "text/html":
                body = clean_html(payload)
            else:
                body = payload.strip()
        except Exception as e:
            print(f"Error decoding message: {e}")
            body = ""
    
    return body

# =========================================================================
# FAMPAY – DATABASE + EMAIL ENGINE
# =========================================================================
def fampay_db_conn():
    conn = sqlite3.connect(FAMPAY_DB)
    conn.row_factory = sqlite3.Row
    return conn

def fampay_init_db():
    with fampay_db_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS notices
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      subject TEXT,
                      message TEXT,
                      received_at TIMESTAMP,
                      email_date TEXT,
                      is_new BOOLEAN DEFAULT 1)''')
        conn.commit()

def fampay_save_notice(subject, message, email_date):
    if not message:
        return
    snippet = message[:500]
    with fampay_db_conn() as conn:
        exists = conn.execute("SELECT id FROM notices WHERE subject = ? AND message LIKE ?",
                             (subject, f"{snippet}%")).fetchone()
        if not exists:
            conn.execute("INSERT INTO notices (subject, message, received_at, email_date, is_new) VALUES (?, ?, ?, ?, 1)",
                      (subject, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), email_date))
            conn.commit()

def fampay_process_emails(search_criterion='ALL'):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(FAMPAY_EMAIL, FAMPAY_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, f'FROM "{FAMPAY_SENDER}" {search_criterion}')
        if status != "OK": return
        
        for msg_id in reversed(messages[0].split()):
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"] or "No Subject")[0]
                    if isinstance(subject, bytes): 
                        subject = subject.decode(encoding or "utf-8")
                    
                    body = extract_email_body(msg)
                    if body:
                        fampay_save_notice(subject, body, msg["Date"])
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"FAMPay error: {e}")

def fampay_background_worker():
    while True:
        fampay_process_emails('UNSEEN')
        time.sleep(FAMPAY_INTERVAL)

# =========================================================================
# BINANCE – DATABASE + EMAIL ENGINE
# =========================================================================
def binance_db_conn():
    conn = sqlite3.connect(BINANCE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def binance_init_db():
    with binance_db_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS notices
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      subject TEXT,
                      message TEXT,
                      received_at TIMESTAMP,
                      email_date TEXT,
                      is_new BOOLEAN DEFAULT 1)''')
        conn.commit()

def binance_save_notice(subject, message, email_date):
    if not message:
        return
    snippet = message[:500]
    with binance_db_conn() as conn:
        exists = conn.execute("SELECT id FROM notices WHERE subject = ? AND message LIKE ?",
                             (subject, f"{snippet}%")).fetchone()
        if not exists:
            conn.execute("INSERT INTO notices (subject, message, received_at, email_date, is_new) VALUES (?, ?, ?, ?, 1)",
                      (subject, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), email_date))
            conn.commit()

def binance_process_emails(search_criterion='ALL'):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(BINANCE_EMAIL, BINANCE_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, f'FROM "{BINANCE_SENDER}" {search_criterion}')
        if status != "OK": return
        
        for msg_id in reversed(messages[0].split()):
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"] or "No Subject")[0]
                    if isinstance(subject, bytes): 
                        subject = subject.decode(encoding or "utf-8")
                    
                    body = extract_email_body(msg)
                    if body:
                        binance_save_notice(subject, body, msg["Date"])
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"Binance error: {e}")

def binance_background_worker():
    while True:
        binance_process_emails('UNSEEN')
        time.sleep(BINANCE_INTERVAL)

# =========================================================================
# API ENDPOINTS
# =========================================================================

# --- FAMPAY endpoint ---
@app.route('/famapp')
def famapp_api():
    target_id = request.args.get('id')
    if not target_id:
        return jsonify({"status": "error", "message": "Missing ID parameter"}), 400

    with fampay_db_conn() as conn:
        row = conn.execute("SELECT * FROM notices WHERE message LIKE ? OR subject LIKE ?",
                          (f'%{target_id}%', f'%{target_id}%')).fetchone()
    
    if row:
        msg_content = row['message']
        amt = re.search(r'(?:Rs\.?|INR|₹)\s?(\d+(?:\.\d{1,2})?)', msg_content)
        tm = re.search(r'(\d{1,2}:\d{2}\s?(?:AM|PM|am|pm))', msg_content)
        
        return jsonify({
            "status": "success",
            "transfer_id": target_id,
            "amount": amt.group(0) if amt else "N/A",
            "time": tm.group(0) if tm else "N/A",
            "date": row['email_date'],
            "full_info": msg_content
        })
    else:
        return jsonify({"status": "pending", "message": "ID not found in database"}), 404

# --- BINANCE endpoint (FIXED) ---
@app.route('/binanace')
def binanace_api():
    target_amount = request.args.get('amount')
    target_name = request.args.get('name')

    if not target_amount and not target_name:
        return jsonify({"status": "error", "message": "Missing 'amount' or 'name' parameter"}), 400

    query = "SELECT * FROM notices WHERE 1=1"
    params = []
    if target_amount:
        query += " AND message LIKE ?"
        params.append(f'%{target_amount}%')
    if target_name:
        query += " AND message LIKE ?"
        params.append(f'%{target_name}%')
    query += " ORDER BY received_at DESC LIMIT 1"

    with binance_db_conn() as conn:
        row = conn.execute(query, params).fetchone()

    if not row:
        return jsonify({"status": "pending", "message": "No matching record found"}), 404

    msg_content = row['message']

    # Extract sender name - look for "From:" followed by text until "Amount:" or end
    sender_match = re.search(r'From:\s*([^A]+?)(?=\s*Amount:|$)', msg_content, re.IGNORECASE)
    if sender_match:
        sender_name = sender_match.group(1).strip()
    else:
        # Fallback: try to find name between "From:" and "Amount:"
        sender_match = re.search(r'From:\s*(\S+)', msg_content, re.IGNORECASE)
        sender_name = sender_match.group(1).strip() if sender_match else "N/A"

    # Extract amount
    amt_match = re.search(r'Amount:\s*([\d.]+)\s*([A-Z]+)', msg_content, re.IGNORECASE)
    if amt_match:
        amount_display = f"{amt_match.group(1)} {amt_match.group(2)}"
    else:
        amount_display = "N/A"

    # Extract time
    tm_match = re.search(r'Time:\s*([\d\-:\s]+)\s*\(UTC\)', msg_content, re.IGNORECASE)
    time_display = tm_match.group(1).strip() if tm_match else "N/A"

    # Extract date from time
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', time_display)
    body_date = date_match.group(1) if date_match else row['email_date']

    return jsonify({
        "status": "success",
        "sender_name": sender_name,
        "amount": amount_display,
        "time": time_display,
        "date": body_date,
        "full_info": msg_content
    })

# =========================================================================
# START THE SERVER
# =========================================================================
if __name__ == '__main__':
    # Delete old databases to start fresh
    import os
    if os.path.exists(BINANCE_DB):
        os.remove(BINANCE_DB)
        print(f"Deleted old {BINANCE_DB}")
    if os.path.exists(FAMPAY_DB):
        os.remove(FAMPAY_DB)
        print(f"Deleted old {FAMPAY_DB}")
    
    # Initialize both databases
    fampay_init_db()
    binance_init_db()

    # Start FAMPay background thread
    threading.Thread(target=lambda: fampay_process_emails('ALL'), daemon=True).start()
    threading.Thread(target=fampay_background_worker, daemon=True).start()

    # Start Binance background thread
    threading.Thread(target=lambda: binance_process_emails('ALL'), daemon=True).start()
    threading.Thread(target=binance_background_worker, daemon=True).start()

    # Run Flask
    app.run(host='0.0.0.0', port=5000, debug=True)