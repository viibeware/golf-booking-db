# Changelog

All notable changes to the Golf Booking Database are documented here.

---

## [0.1.3] - 2026-04-10

### Added
- **Configurable recent intakes count** — Settings > Appearance lets users choose how many recent records appear in the sidebar (0, 1, 2, 3, 5, 8, or 10). Default is 3. Preference is saved per browser.
- **Branded PDF export** — PDFs now feature the app logo and "Golf Booking Database" title in the upper-left matching the sidebar branding, version number, bold intake number and group name subtitle, accent-colored section dividers with underlines, field row separators, and a professional footer with app name and "viibeware Corp." on every page.
- **In-app release notes** — Settings > About now includes a scrollable release notes section showing changes across all versions.
- **CHANGELOG.md** — Full release notes file added to the repository.

### Changed
- Recent intakes sidebar list default reduced from 8 to 3 items
- Recent intakes defined as records most recently saved (by updated_at timestamp)
- Sessions are now permanent until the user explicitly logs out (365-day session lifetime)
- PDF header redesigned to match sidebar brand style — compact left-aligned logo with stacked title and version
- Light mode tee slot cards use white background for better contrast
- Login page footer shows viibeware logo, company name, and version number

---

## [0.1.2] - 2026-04-10

### Added
- **Granular per-user permissions** — Admins can toggle six permissions on/off for each editor user via Settings > Users:
  - **Delete** — Permanently delete records (default: off)
  - **Archive** — Archive and restore records (default: on)
  - **Export** — Export records to CSV (default: on)
  - **Import** — Import records from CSV (default: on)
  - **View All** — See all users' records instead of only their own (default: off)
  - **Print/PDF** — Access print view and PDF export (default: on)
- Permission toggle switches (iOS-style) rendered in a 3-column grid under each editor in Settings > Users
- `/users/<id>/permissions` API endpoint for real-time permission toggling
- All route-level permission enforcement — every action checks the user's specific permissions

### Changed
- UI buttons (Export, Archive, Delete, Print, PDF) now conditionally render based on the current user's permissions
- Settings > Data tab visibility is now based on import/export permissions
- Admin permissions are protected and cannot be modified
- User creation remains admin-only regardless of editor permissions

---

## [0.1.1] - 2026-04-07

### Added
- **Auto-generated intake numbers** — Sequential IDs (GBD1001, GBD1002, ...) assigned automatically on record creation
- **Arrival and departure dates** — Preferred and 2nd option dates now include separate arrival and departure fields
- **Courses section** — Jones, Palmer, and Crispin courses with checkbox selection and number of rounds per course
- **Redesigned tee time slots** — Each slot now includes:
  - Course dropdown (Jones / Palmer / Crispin)
  - Time as a simple text field (instead of hour/minute dropdowns)
  - AM/PM toggle switch
  - Number of holes
  - Per-tee-time notes field
  - Labeled fields in a single horizontal row with notes underneath
- **Recent intakes sidebar** — Shows most recently edited/created intakes in the sidebar with a "More" link
- **Multi-user record isolation** — Each editor sees only their own records; admins see all
- **Settings modal accessible to editors** — Editors can access Settings for Appearance and Data tabs; Users tab remains admin-only
- **Import moved to Settings > Data tab** — With option to import into Active or Archived
- **Export All Records** button added to Settings > Data tab
- **Renamed export buttons** — "Export Active to CSV" and "Export Archived to CSV" for clarity
- **`.env` configuration** — All settings managed via environment file (SECRET_KEY, DATABASE, APP_PORT, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASS)
- **No-cache HTTP headers** — Prevents browser from serving stale HTML after deployments
- **Cache-busting query parameters** on CSS and JavaScript includes
- **Permanent sessions** — Login persists until explicit logout
- **Light mode as default theme**
- **viibeware branding** on login page footer with logo, company name, and version number
- **Application logo** replaces old SVG golf tee icon on login page and empty state
- **Settings > About** enhanced with app logo, viibeware logo (linked to viibeware.com), and support email
- **GitHub Actions workflow** for auto-generating releases from tags

### Changed
- Table view first column changed from BKG# to clickable Intake# (BKG# remains as a form field)
- Viewer role removed — only Admin and Editor roles remain
- Docker Compose updated to use `env_file` instead of inline environment variables
- `.dockerignore` excludes `.env` from Docker builds
- Light mode tee slot cards use white background for better contrast

### Fixed
- Database auto-migration for existing databases — adds missing columns without data loss
- `sqlite3.Row` `.get()` compatibility issues
- Stray duplicate JavaScript code block causing syntax errors
- Settings modal not opening due to cached broken JavaScript
- `loadSettingsUsers()` guarded to only fetch `/api/users` when the users panel exists

---

## [0.1.0] - 2026-04-05

### Added
- Initial release
- Flask + SQLite web application with Docker support
- Intake form with all core fields: BKG number, date of call, year, group name, contact info, golfer count, preferred dates, golfed-before toggle, breakfast/accommodation preferences, tee times with repeatable days and slots, address, billing method, budget, pickup, notes
- User authentication with login/logout
- Admin, Editor, and Viewer roles
- Searchable and sortable intake table
- Archive system with bulk select/archive/restore
- Print view (condensed single-page layout)
- PDF export (two-column ReportLab layout)
- CSV import and export
- Light and dark theme toggle
- Sidebar navigation
- New Intake modal popup
- Settings modal with Appearance, Users, and About tabs
- User management (add, edit role, reset password, delete)
- Docker Compose deployment
