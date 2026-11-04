# Build Guide - Production Environment (TRD v2.0)

## 1. Prerequisites
Install **Python 3.11 or 3.12** (do NOT use Python 3.14 — its wheel toolchain
breaks `langchain-core` / `CrewAI 0.11.2` dependency resolution).

Also install **FFmpeg** (required for headless video rendering):
- Windows: `winget install FFmpeg` or download from ffmpeg.org and add `ffmpeg` to PATH.
- macOS: `brew install ffmpeg`
- Linux: `apt-get install ffmpeg`

## 2. Create & Activate the Virtual Environment
```powershell
# From the project root
python setup_env.py
```

On Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```
On Unix/macOS:
```bash
source .venv/bin/activate
```

## 3. Configure Environment Variables
Copy the example file and fill in real credentials:
```powershell
copy .env.example .env
# edit .env with GEMINI_API_KEY, COINDCX_API_KEY, COINDCX_SECRET_KEY, META_ACCESS_TOKEN, META_PAGE_ID
```

## 4. Run the Pipeline (Production - native crew.kickoff())
```powershell
python main.py
```
The CrewAI `Process.sequential` framework will execute end-to-end:
Supervisor → Dev Wizard → Quant Trader → Video & Creative Director → DB Tracker → Content Viralist → Supervisor report.

## 5. Headless Automated Scheduling (Daily 09:30 AM)
### Windows Task Scheduler
```powershell
schedule_runner.bat
```
Register `schedule_runner.bat` in Task Scheduler with a daily trigger at 09:30.

### Unix/Linux cron
Add to crontab (`crontab -e`):
```cron
30 9 * * * /path/to/odlixceo/.venv/bin/python /path/to/odlixceo/ops_scheduler.py >> /path/to/odlixceo/scheduler.log 2>&1
```

## 6. Database
All pipeline events, trade guardrail violations, video fallback events, and social
publish confirmations are written to `company_vault.db` (table `system_logs`).
Inspect with:
```powershell
python -c "import sqlite3; c=sqlite3.connect('company_vault.db'); [print(r) for r in c.execute('SELECT * FROM system_logs ORDER BY id')]"
```
