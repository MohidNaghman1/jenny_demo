"""
Run this once to generate contracts.pdf and payments.db
"""
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

def create_contracts_pdf():
    doc = SimpleDocTemplate("contracts.pdf", pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    heading = ParagraphStyle('heading', parent=styles['Heading1'], spaceAfter=12)
    body = ParagraphStyle('body', parent=styles['Normal'], spaceAfter=8, leading=16)

    contracts = [
        {
            "id": "CONTRACT-001",
            "client": "Acme Corp",
            "start": "January 1, 2024",
            "expiry": "December 31, 2024",
            "payment": "$5,000 per month",
            "penalty": "A late payment penalty of 5% per month applies after 30 days overdue. Penalties are compounded monthly and added to the outstanding balance.",
            "suspension": "Services will be suspended after 60 days of non-payment. Reinstatement requires full payment of outstanding balance plus a $200 reinstatement fee.",
        },
        {
            "id": "CONTRACT-002",
            "client": "BrightTech Ltd",
            "start": "March 1, 2024",
            "expiry": "February 28, 2025",
            "payment": "$8,500 per month",
            "penalty": "A flat late fee of $500 applies after 15 days overdue. Additional interest of 2% per month accrues after 30 days.",
            "suspension": "Services will be immediately suspended after 45 days of non-payment. Client must provide written notice of payment intent before reinstatement.",
        },
        {
            "id": "CONTRACT-003",
            "client": "Nova Solutions",
            "start": "June 1, 2024",
            "expiry": "May 31, 2025",
            "payment": "$3,200 per month",
            "penalty": "Late payment penalty of 3% per month applies, capped at a maximum of 15% of the total outstanding amount.",
            "suspension": "Services will be suspended after 90 days of non-payment. A 7-day written notice must be provided before suspension takes effect. Reinstatement fee is $150.",
        },
    ]

    for c in contracts:
        story.append(Paragraph(f"SERVICE AGREEMENT — {c['id']}", heading))
        story.append(Paragraph(f"<b>Client:</b> {c['client']}", body))
        story.append(Paragraph(f"<b>Contract Period:</b> {c['start']} to {c['expiry']}", body))
        story.append(Paragraph(f"<b>Monthly Payment:</b> {c['payment']}", body))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("<b>Section 4 — Late Payment Penalties</b>", body))
        story.append(Paragraph(c['penalty'], body))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("<b>Section 5 — Service Suspension</b>", body))
        story.append(Paragraph(c['suspension'], body))
        story.append(Spacer(1, 1*cm))

    doc.build(story)
    print("✅ contracts.pdf created")

def create_payments_db():
    conn = sqlite3.connect("payments.db")
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS payments;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            contract_id TEXT
        );

        CREATE TABLE payments (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            amount REAL,
            due_date TEXT,
            status TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    """)

    cur.executemany("INSERT INTO customers VALUES (?,?,?)", [
        (1, 'Acme Corp',     'CONTRACT-001'),
        (2, 'BrightTech Ltd','CONTRACT-002'),
        (3, 'Nova Solutions','CONTRACT-003'),
    ])

    cur.executemany("INSERT INTO payments VALUES (?,?,?,?,?)", [
        (1, 1, 5000.00, '2024-10-01', 'overdue'),
        (2, 1, 5000.00, '2024-11-01', 'overdue'),
        (3, 2, 8500.00, '2024-11-01', 'paid'),
        (4, 3, 3200.00, '2024-10-01', 'overdue'),
        (5, 2, 8500.00, '2024-12-01', 'pending'),
    ])

    conn.commit()
    conn.close()
    print("✅ payments.db created")

if __name__ == "__main__":
    create_contracts_pdf()
    create_payments_db()
