# Golf Booking Database

**Version 0.1.1** | A [viibeware Corp.](https://viibeware.com) Application

A self-hosted web application for collecting and managing customer intake information at a golf resort. Built with Flask and SQLite, packaged as a Docker container for easy deployment on any server.

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [User Roles & Multi-User](#user-roles--multi-user)
- [Data Management](#data-management)
- [Backup & Restore](#backup--restore)
- [Updating](#updating)
- [Troubleshooting](#troubleshooting)
- [Tech Stack](#tech-stack)
- [Support](#support)

---

## Features

### Intake Form
- **Auto-generated intake numbers** — Sequential IDs (GBD1001, GBD1002, ...) assigned automatically
- **Booking reference** — Separate BKG# field for the customer's own reference number
- **Contact information** — Name, phone number, email
- **Group details** — Group name, number of golfers, year
- **Date preferences** — Preferred and 2nd option dates with arrival and departure for each
- **Return guest tracking** — "Golfed before?" toggle with prior group name field
- **Meal preferences** — Breakfast options (Yes / No / Quote Both Ways)
- **Lodging** — Cottage, Lodge, or Quote Both Ways
- **Courses** — Jones, Palmer, and Crispin with number of rounds per course
- **Tee times** — Repeatable tee day entries, each with multiple tee time slots:
  - Course selection (Jones / Palmer / Crispin)
  - Time entry with AM/PM toggle
  - Number of holes
  - Per-tee-time notes
- **Billing** — Master Bill or Individual Pay toggle
- **Additional fields** — Address, budget, pickup details, general notes

### Interface
- **Sidebar navigation** with recent intakes list (up to 8 most recent)
- **New Intake modal** — 600px popup with blurred backdrop for quick data entry
- **Light / Dark theme** — Toggle in Settings, preference saved per browser
- **Clickable intake numbers** in the table view to open records
- **Search** across all text fields
- **Sortable columns** — Click any column header to sort ascending/descending
- **Archive system** — Move completed intakes to a separate archive view
- **Bulk actions** — Select multiple intakes to archive or restore at once

### Output
- **Print view** — Condensed, single-page-optimized layout
- **PDF export** — Two-column formatted PDF for each record
- **CSV export** — Export active, archived, or all records
- **CSV import** — Import records into active or archived via Settings

### Administration
- **Role-based access** — Admin and Editor roles
- **Multi-user isolation** — Each editor sees only their own records
- **User management** — Add, edit roles, reset passwords, delete users
- **Settings modal** — Appearance, Data (import/export), Users, and About tabs

---

## Requirements

- **Docker** and **Docker Compose** installed on your server
- A Linux server (Ubuntu, Fedora, Debian, etc.) or any system running Docker
- Minimum 512MB RAM, 100MB disk space

---

## Installation

### 1. Download and Extract

Copy the `golf-booking-db` folder to your server:

```bash
tar -xzf golf-booking-db.tar.gz
cd golf-booking-db
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

### 3. Generate a Secret Key

The `SECRET_KEY` is used to encrypt session cookies. **You must change this before deploying.** Generate a secure key using one of these methods:

```bash
# Python (recommended)
python3 -c "import secrets; print(secrets.token_hex(32))"

# OpenSSL
openssl rand -hex 32

# /dev/urandom
head -c 32 /dev/urandom | xxd -p -c 64
```

Open `.env` in a text editor and replace the `SECRET_KEY` value:

```bash
nano .env
```

```env
SECRET_KEY=paste-your-generated-key-here
```

### 4. Build and Start

```bash
docker compose up -d --build
```

The application will be available at:

```
http://your-server-ip:5055
```

### 5. First Login

Default credentials:

| Field    | Value   |
|----------|---------|
| Username | `admin` |
| Password | `admin` |

> **Important:** Change the default admin password immediately after first login via **Settings > Users**.

---

## Configuration

All configuration is managed through the `.env` file. The application reads these values on startup.

### Environment Variables

| Variable             | Default                         | Description                                                  |
|----------------------|---------------------------------|--------------------------------------------------------------|
| `SECRET_KEY`         | `change-me-generate-a-real-key` | Flask session encryption key. **Must be changed.**           |
| `DATABASE`           | `/data/golf_booking_db.db`      | Path to the SQLite database file inside the container.       |
| `APP_PORT`           | `5055`                          | Host port the application is accessible on.                  |
| `DEFAULT_ADMIN_USER` | `admin`                         | Username for the default admin account (first run only).     |
| `DEFAULT_ADMIN_PASS` | `admin`                         | Password for the default admin account (first run only).     |

### Example `.env` File

```env
SECRET_KEY=a1b2c3d4e5f6789012345678abcdef0123456789abcdef0123456789abcdef01
DATABASE=/data/golf_booking_db.db
APP_PORT=5055
DEFAULT_ADMIN_USER=admin
DEFAULT_ADMIN_PASS=changeme
```

### Best Practices

- **Always generate a unique `SECRET_KEY`** for each deployment. Never use the default or share keys between environments.
- **Change the default admin password** on first login. The `DEFAULT_ADMIN_USER` and `DEFAULT_ADMIN_PASS` values are only used when the database is first created (no users exist). Changing them in `.env` after users exist has no effect.
- **Do not commit `.env` to version control.** The `.dockerignore` file already excludes it from Docker builds. If using Git, add `.env` to your `.gitignore`.
- **Use a reverse proxy** (Nginx, Caddy, or Nginx Proxy Manager) with HTTPS in production. The app runs on HTTP internally — your proxy should handle SSL termination.
- **If you change `SECRET_KEY`** after the app has been running, all active user sessions will be invalidated and users will need to log in again.
- **Back up your database regularly** (see [Backup & Restore](#backup--restore)).

---

## Usage

### Creating an Intake

1. Click the **New Intake** button in the sidebar
2. Fill out the form fields in the modal popup
3. Add tee days and tee time slots as needed
4. Click **Create Intake**

The intake is assigned an auto-generated number (GBD1001, GBD1002, etc.) and appears in the Active Intakes list.

### Viewing and Editing

- Click any **intake number** in the table to view the full record
- Click the **Edit** button to modify an existing record
- Use **Print** for a clean printable layout or **PDF** to download a file

### Archiving

- Click the **archive icon** on any row to move it to the archive
- Use **bulk select** (checkboxes) to archive or restore multiple records at once
- Switch between **Active** and **Archive** views using the sidebar links

### Search and Sort

- Use the **search bar** to filter records by BKG#, group name, contact, address, notes, or intake number
- Click any **column header** to sort ascending or descending

---

## User Roles & Multi-User

The application supports multiple users with role-based access control.

| Capability           | Editor | Admin |
|----------------------|--------|-------|
| View own records     | ✅     | ✅    |
| View all records     | ❌     | ✅    |
| Create intakes       | ✅     | ✅    |
| Edit own intakes     | ✅     | ✅    |
| Archive/restore      | ✅     | ✅    |
| Delete intakes       | ❌     | ✅    |
| Import/Export CSV     | ✅     | ✅    |
| Manage users         | ❌     | ✅    |
| Change theme         | ✅     | ✅    |

### Multi-User Isolation

- **Editors** can only see and manage records they created. They cannot access records created by other users.
- **Admins** can see and manage all records across all users.
- The **Recent** sidebar section shows each user's own recent intakes (admins see all).
- **CSV exports** respect user isolation — editors only export their own records.

### Managing Users

1. Click **Settings** in the sidebar (admin only for the Users tab)
2. Go to the **Users** tab
3. Add new users with a username, password, and role
4. Edit roles or reset passwords for existing users
5. Delete users (you cannot delete your own account)

---

## Data Management

### Exporting Data

There are three export options:

| Method                     | Location                    | What it exports                        |
|----------------------------|-----------------------------|----------------------------------------|
| **Export Active to CSV**   | Active Intakes page         | All currently displayed active records |
| **Export Archived to CSV** | Archived Intakes page       | All currently displayed archived records |
| **Export All Records**     | Settings > Data tab         | All records (active + archived)        |

### Importing Data

1. Go to **Settings > Data** tab
2. Select a CSV file
3. Choose whether to import into **Active** or **Archived**
4. Click **Import CSV**

The CSV should include column headers matching the export format. Each imported record receives a new auto-generated intake number.

---

## Backup & Restore

The SQLite database is stored in a Docker volume (`golfdb_data`), which persists across container rebuilds.

### Backup

```bash
docker cp golf-booking-db:/data/golf_booking_db.db ./backup_$(date +%Y%m%d).db
```

### Restore

```bash
docker cp ./backup_20260407.db golf-booking-db:/data/golf_booking_db.db
docker compose restart
```

### Automated Backups

Add a cron job for daily backups:

```bash
crontab -e
```

```
0 2 * * * docker cp golf-booking-db:/data/golf_booking_db.db /backups/golf_booking_db_$(date +\%Y\%m\%d).db
```

---

## Updating

To update to a new version:

1. **Back up your database** (see above)
2. Replace the application files with the new version
3. Rebuild and restart:

```bash
docker compose down
docker compose up -d --build
```

Your data is preserved in the Docker volume. The application automatically runs database migrations on startup to add any new columns without losing existing data.

> **Note:** If you see stale styles or broken behavior after updating, do a hard refresh in your browser (`Ctrl+Shift+R` or `Cmd+Shift+R`) to clear cached CSS and JavaScript files.

---

## Troubleshooting

### "Container name already in use"

```bash
docker stop golf-booking-db
docker rm golf-booking-db
docker compose up -d --build
```

### Settings button doesn't work

This is usually a browser cache issue. Hard refresh with `Ctrl+Shift+R` or clear your browser cache.

### "no such column" errors

The app auto-migrates the database on startup. If you see column errors, restart the container:

```bash
docker compose restart
```

### Port already in use

Change `APP_PORT` in your `.env` file to a different port:

```env
APP_PORT=5056
```

Then restart: `docker compose up -d`

### Forgot admin password

If you're locked out, you can reset directly in the database:

```bash
docker exec -it golf-booking-db python3 -c "
from werkzeug.security import generate_password_hash
import sqlite3
conn = sqlite3.connect('/data/golf_booking_db.db')
conn.execute('UPDATE users SET password_hash=? WHERE username=?',
    (generate_password_hash('newpassword'), 'admin'))
conn.commit()
print('Password reset to: newpassword')
"
```

---

## Tech Stack

| Component      | Technology                          |
|----------------|-------------------------------------|
| Backend        | Python 3.12, Flask                  |
| Database       | SQLite with WAL mode                |
| PDF Generation | ReportLab                           |
| Frontend       | Vanilla HTML, CSS, JavaScript       |
| Container      | Docker with Docker Compose          |

---

## Support

**viibeware Corp.** — [viibeware.com](https://viibeware.com)

Contact: [viibeware@proton.me](mailto:viibeware@proton.me)
