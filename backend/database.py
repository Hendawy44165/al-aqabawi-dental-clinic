import sqlite3
import datetime
from pathlib import Path
import os

if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/clinic.db"
else:
    DB_PATH = Path(__file__).parent / "clinic.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price TEXT NOT NULL,
        description TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS doctor_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER NOT NULL,
        slot_date TEXT NOT NULL,
        slot_time TEXT NOT NULL,
        is_booked BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (doctor_id) REFERENCES doctors (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_slot_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        notes TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients (id),
        FOREIGN KEY (doctor_slot_id) REFERENCES doctor_slots (id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT,
        customer_phone TEXT,
        summary TEXT,
        status TEXT DEFAULT 'open',
        urgency REAL DEFAULT 0.5,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        thread_id TEXT PRIMARY KEY,
        patient_name TEXT,
        patient_phone TEXT,
        status TEXT DEFAULT 'active',
        ai_enabled INTEGER DEFAULT 1,
        last_message TEXT,
        sentiment TEXT DEFAULT 'حجز موعد',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id TEXT,
        sender TEXT,
        text TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Seed data
    c.execute("SELECT COUNT(*) FROM doctors")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO doctors (name) VALUES (?)", ("Dr. Mohamed Al-Aqabawi",))
        c.execute("INSERT INTO doctors (name) VALUES (?)", ("Dr. Ibrahim Gamal",))
        
        services = [
            ("حشو عادي", "800+", "حشو عادي كومبوزيت تجميلي"),
            ("حشو عصب", "2500+", "شامل تنظيف وإعادة معالجة الجذور"),
            ("طربوش زيركون", "2500+", "زيركون ألماني تجميلي عالي الجودة"),
            ("تنظيف عميق وتلميع", "600 offer", "عرض خاص تنظيف وتلميع وإزالة آثار السجاير"),
            ("علاج اللثة بالليزر", "1500+", "علاج وتجميل اللثة بالليزر بدون ألم"),
            ("معاينة 3D result preview", "مجاناً مع الكشف", "معاينة الشكل النهائي 3D قبل الشغل"),
            ("زراعة", "8000+", "زراعة أسنان فورية"),
            ("تقويم", "12000+", "تقويم أسنان بمقدم وتقسيط شهري 800 جنيه"),
            ("خلع", "500+", "خلع عادي أو جراحي")
        ]
        c.executemany("INSERT INTO services (name, price, description) VALUES (?, ?, ?)", services)
        
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        
        slots = []
        for d_id in [1, 2]:
            for time in ["10:00", "11:00", "12:00", "13:00", "14:00"]:
                slots.append((d_id, today.strftime("%Y-%m-%d"), time, False))
                slots.append((d_id, tomorrow.strftime("%Y-%m-%d"), time, False))
                
        c.executemany("INSERT INTO doctor_slots (doctor_id, slot_date, slot_time, is_booked) VALUES (?, ?, ?, ?)", slots)

        # Seed sample conversations & tickets (thread-2 and thread-3 for demo tickets)
        c.execute("""
            INSERT OR IGNORE INTO conversations (thread_id, patient_name, patient_phone, status, ai_enabled, last_message, sentiment)
            VALUES 
            ('thread-2', 'محمود علي', '01099887766', 'escalated', 0, 'ألم شديد جداً وتورم في الضرس السفلي', 'طوارئ عاجلة'),
            ('thread-3', 'حبيبة خالد', '01198765432', 'claimed', 0, 'أنا بعتت رسالة ومستنية الدكتور يكلمني', 'طوارئ وإعادة تواصل')
        """)

        c.execute("""
            INSERT OR IGNORE INTO chat_messages (thread_id, sender, text)
            VALUES 
            ('thread-2', 'user', 'السلام عليكم، الضرس عندي وجعه شديد أوي ومستمر ومش قادر أنام خالص وتعبان جداً'),
            ('thread-2', 'bot', 'ألف سلامة عليك يا فندم! تم تحويل حالتك فوراً للـ ريسيبشن البشري وطبيب الطوارئ وسيتم التواصل معك مباشرة 📱'),
            ('thread-3', 'user', 'السلام عليكم، محتاجة أغير موعد الحجز لبكرة الساعة 5')
        """)


        c.execute("""
            INSERT OR IGNORE INTO tickets (id, conversation_id, customer_phone, summary, status, urgency)
            VALUES 
            (1, 'thread-2', '01099887766', 'ألم شديد جداً وتورم في الضرس السفلي لا يستجيب للمسكنات', 'open', 0.95),
            (2, 'thread-3', '01198765432', 'طلب تغيير موعد ومتابعة مع د. إبراهيم جمال', 'claimed', 0.8)
        """)
        
    conn.commit()
    conn.close()

def get_doctors():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM doctors")
    docs = [dict(row) for row in c.fetchall()]
    conn.close()
    return docs

def get_services():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM services")
    services = [dict(row) for row in c.fetchall()]
    conn.close()
    return services

def get_available_slots(doctor_name=None, date=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    query = """
        SELECT s.id, d.name as doctor_name, s.slot_date, s.slot_time 
        FROM doctor_slots s 
        JOIN doctors d ON s.doctor_id = d.id 
        WHERE s.is_booked = FALSE
    """
    params = []
    if doctor_name:
        doc_lower = str(doctor_name).lower()
        if any(w in doc_lower for w in ["محمد", "عقباوي", "mohamed", "aqabawi"]):
            query += " AND (d.name LIKE '%Mohamed%' OR d.name LIKE '%Aqabawi%')"
        elif any(w in doc_lower for w in ["إبراهيم", "ابراهيم", "جمال", "ibrahim", "gamal"]):
            query += " AND (d.name LIKE '%Ibrahim%' OR d.name LIKE '%Gamal%')"
        else:
            query += " AND d.name LIKE ?"
            params.append(f"%{doctor_name}%")
            
    if date:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        tomorrow_str = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        date_lower = str(date).lower()
        if any(w in date_lower for w in ["today", "النهاردة", "اليوم"]):
            query += " AND s.slot_date = ?"
            params.append(today_str)
        elif any(w in date_lower for w in ["tomorrow", "بكرة", "غدا", "غداً"]):
            query += " AND s.slot_date = ?"
            params.append(tomorrow_str)
        else:
            query += " AND s.slot_date LIKE ?"
            params.append(f"%{date}%")
    
    c.execute(query, params)
    slots = [dict(row) for row in c.fetchall()]
    
    if not slots:
        c.execute("""
            SELECT s.id, d.name as doctor_name, s.slot_date, s.slot_time 
            FROM doctor_slots s 
            JOIN doctors d ON s.doctor_id = d.id 
            WHERE s.is_booked = FALSE
        """)
        slots = [dict(row) for row in c.fetchall()]
        
    conn.close()
    return slots

def create_appointment(patient_name, patient_phone, slot_id, notes=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT is_booked FROM doctor_slots WHERE id = ?", (slot_id,))
    res = c.fetchone()
    if not res or res[0]:
        conn.close()
        return {"error": "Slot unavailable"}
        
    c.execute("SELECT id FROM patients WHERE phone = ?", (patient_phone,))
    p = c.fetchone()
    if p:
        patient_id = p[0]
    else:
        c.execute("INSERT INTO patients (name, phone) VALUES (?, ?)", (patient_name, patient_phone))
        patient_id = c.lastrowid
        
    c.execute("INSERT INTO appointments (patient_id, doctor_slot_id, notes) VALUES (?, ?, ?)", (patient_id, slot_id, notes))
    c.execute("UPDATE doctor_slots SET is_booked = TRUE WHERE id = ?", (slot_id,))
    
    conn.commit()
    conn.close()
    return {"success": True}

def get_appointments():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT a.id, p.name as patient_name, p.phone as patient_phone, d.name as doctor_name, s.slot_date, s.slot_time, a.status, a.notes
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctor_slots s ON a.doctor_slot_id = s.id
        JOIN doctors d ON s.doctor_id = d.id
    """)
    apps = [dict(row) for row in c.fetchall()]
    conn.close()
    return apps

def create_ticket(thread_id, phone="01012345678", summary="طوارئ/استئاء مريض يطلب التدخل البشري", urgency=0.9):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO tickets (conversation_id, customer_phone, summary, status, urgency, created_at)
        VALUES (?, ?, ?, 'open', ?, CURRENT_TIMESTAMP)
    """, (thread_id, phone, summary, urgency))
    ticket_id = c.lastrowid
    c.execute("UPDATE conversations SET status = 'escalated', ai_enabled = 0, last_message = ? WHERE thread_id = ?", (summary, thread_id))
    conn.commit()
    conn.close()
    return ticket_id

def update_appointment_status(appointment_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE appointments SET status = ? WHERE id = ?", (status, appointment_id))
    conn.commit()
    conn.close()
    return {"success": True}


def update_ticket_status(ticket_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
    c.execute("SELECT conversation_id FROM tickets WHERE id = ?", (ticket_id,))
    row = c.fetchone()
    if row and row[0]:
        thread_id = row[0]
        if status in ['resolved', 'closed']:
            c.execute("UPDATE conversations SET status = 'active', ai_enabled = 1 WHERE thread_id = ?", (thread_id,))
        elif status in ['claimed', 'open']:
            c.execute("UPDATE conversations SET status = ?, ai_enabled = 0 WHERE thread_id = ?", (status, thread_id))
    conn.commit()
    conn.close()
    return {"success": True}

def update_service_price(service_id, new_price):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE services SET price = ? WHERE id = ?", (str(new_price), service_id))
    conn.commit()
    conn.close()
    return {"success": True}

# Conversation & Human Takeover Helpers
def get_conversations():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
    convs = [dict(row) for row in c.fetchall()]
    conn.close()
    return convs

def get_conversation_messages(thread_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM chat_messages WHERE thread_id = ? ORDER BY timestamp ASC", (thread_id,))
    msgs = [dict(row) for row in c.fetchall()]
    conn.close()
    return msgs

def add_chat_message(thread_id, sender, text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO chat_messages (thread_id, sender, text) VALUES (?, ?, ?)", (thread_id, sender, text))
    c.execute("""
        INSERT INTO conversations (thread_id, patient_name, patient_phone, status, ai_enabled, last_message, updated_at)
        VALUES (?, 'مريض الشات المباشر', '01012345678', 'active', 1, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(thread_id) DO UPDATE SET 
            last_message = excluded.last_message,
            updated_at = CURRENT_TIMESTAMP
    """, (thread_id, text))
    conn.commit()
    conn.close()
    return {"success": True}


def set_ai_enabled(thread_id, enabled: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE conversations SET ai_enabled = ?, status = ? WHERE thread_id = ?", 
              (enabled, 'active' if enabled else 'manual', thread_id))
    conn.commit()
    conn.close()
    return {"success": True, "ai_enabled": enabled}

def get_conversation(thread_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM conversations WHERE thread_id = ?", (thread_id,))
    res = c.fetchone()
    conn.close()
    return dict(res) if res else None

def reset_demo_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM chat_messages")
    c.execute("DELETE FROM conversations")
    c.execute("DELETE FROM tickets")
    
    # Re-seed initial demo conversations & tickets for thread-2 and thread-3
    c.execute("""
        INSERT INTO conversations (thread_id, patient_name, patient_phone, status, ai_enabled, last_message, sentiment)
        VALUES 
        ('thread-2', 'محمود علي', '01099887766', 'escalated', 0, 'ألم شديد جداً وتورم في الضرس السفلي', 'طوارئ ألم حادة'),
        ('thread-3', 'حبيبة خالد', '01198765432', 'claimed', 0, 'أنا بعتت رسالة ومستنية الدكتور يكلمني', 'تعديل موعد')
    """)

    c.execute("""
        INSERT INTO chat_messages (thread_id, sender, text)
        VALUES 
        ('thread-2', 'user', 'السلام عليكم، الضرس عندي وجعه شديد أوي ومستمر ومش قادر أنام خالص وتعبان جداً'),
        ('thread-2', 'bot', 'ألف سلامة عليك يا فندم! تم تحويل حالتك فوراً للـ ريسيبشن البشري وطبيب الطوارئ وسيتم التواصل معك مباشرة 📱'),
        ('thread-3', 'user', 'السلام عليكم، محتاجة أغير موعد الحجز لبكرة الساعة 5')
    """)

    c.execute("""
        INSERT INTO tickets (id, conversation_id, customer_phone, summary, status, urgency)
        VALUES 
        (1, 'thread-2', '01099887766', 'ألم شديد جداً وتورم في الضرس السفلي لا يستجيب للمسكنات', 'open', 0.95),
        (2, 'thread-3', '01198765432', 'طلب تغيير موعد ومتابعة مع د. إبراهيم جمال', 'claimed', 0.8)
    """)
    conn.commit()
    conn.close()
    return {"success": True}


def get_tickets():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tickets ORDER BY created_at DESC")
    tickets = [dict(row) for row in c.fetchall()]
    conn.close()
    return tickets

# init on load
init_db()

class DatabaseClient:
    def get_doctors(self): return get_doctors()
    def get_services(self): return get_services()
    def get_available_slots(self, doctor_name=None, date=None): return get_available_slots(doctor_name, date)
    def create_appointment(self, patient_name, patient_phone, slot_id, notes=""): return create_appointment(patient_name, patient_phone, slot_id, notes)
    def get_appointments(self): return get_appointments()
    def update_appointment_status(self, appointment_id, status): return update_appointment_status(appointment_id, status)
    def update_ticket_status(self, ticket_id, status): return update_ticket_status(ticket_id, status)
    def update_service_price(self, service_id, new_price): return update_service_price(service_id, new_price)
    def reset_demo(self): return reset_demo_db()
    def get_tickets(self): return get_tickets()

db = DatabaseClient()


