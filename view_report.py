#!/usr/bin/env python3
"""view_report.py - Print today's pipeline activity from company_vault.db in Hindi/English."""

import sqlite3
from datetime import date

conn = sqlite3.connect("company_vault.db")
c = conn.cursor()
today = date.today().isoformat()

c.execute("SELECT details FROM system_logs WHERE date(timestamp)=? AND category='Code'", (today,))
dev = c.fetchone()
c.execute("SELECT details FROM system_logs WHERE date(timestamp)=? AND category='Trade'", (today,))
trade = c.fetchone()
c.execute("SELECT details FROM system_logs WHERE date(timestamp)=? AND category='Video'", (today,))
video = c.fetchone()
c.execute("SELECT details FROM system_logs WHERE date(timestamp)=? AND category='Social'", (today,))
social = c.fetchone()

print("=== आज का रिपोर्ट / Today's Report ===")
print(f"डेवलपर ने: {dev[0] if dev else 'आज कोई कोड फाइल नहीं सेव की।'}")
print(f"ट्रेडर ने: {trade[0] if trade else 'आज कोई ट्रेड नहीं किया।'}")
print(f"वीडियो एजेंट ने: {video[0] if video else 'आज कोई वीडियो नहीं बनाया।'}")
print(f"मार्केटर ने: {social[0] if social else 'आज कुछ पोस्ट नहीं किया।'}")
conn.close()
