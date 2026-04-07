// ─── Golf Booking Database v0.1.1 - Client JS ───

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initToggles();
    initConditionalFields();
    initModalConditionalFields();
    initSelectAll();
    initBulkActions();
    initDateDayDisplay();
    autoFadeFlash();
    setModalDate();
    autoOpenSettings();
});

// ═══════════════════════════════════════════
// SIDEBAR TOGGLE (mobile)
// ═══════════════════════════════════════════
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    sidebar.classList.toggle('open');
    overlay.classList.toggle('open');
}

// ═══════════════════════════════════════════
// NEW BOOKING MODAL
// ═══════════════════════════════════════════
function openNewIntakeModal() {
    const modal = document.getElementById('new-booking-modal');
    if (modal) {
        modal.classList.add('open');
        document.body.style.overflow = 'hidden';
        setModalDate();
        // Re-init toggles inside modal
        initToggles();
    }
    // Close mobile sidebar if open
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
}

function closeNewIntakeModal() {
    const modal = document.getElementById('new-booking-modal');
    if (modal) {
        modal.classList.remove('open');
        document.body.style.overflow = '';
    }
}

function setModalDate() {
    const dateInput = document.getElementById('modal-date-of-call');
    if (dateInput && !dateInput.value) {
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        dateInput.value = `${yyyy}-${mm}-${dd}`;
    }
}

// Close modal on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-backdrop')) {
        closeNewIntakeModal();
    }
});

// Close modals on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeNewIntakeModal();
        closeSettingsModal();
    }
});

// ═══════════════════════════════════════════
// TOGGLE GROUPS (round pill toggles)
// ═══════════════════════════════════════════
function initToggles() {
    document.querySelectorAll('.toggle-group').forEach(group => {
        group.querySelectorAll('.toggle-option').forEach(opt => {
            const input = opt.querySelector('input');
            if (input && input.checked) opt.classList.add('active');
            opt.addEventListener('click', () => {
                group.querySelectorAll('.toggle-option').forEach(o => o.classList.remove('active'));
                opt.classList.add('active');
                if (input) {
                    input.checked = true;
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
        });
    });
}

// ═══════════════════════════════════════════
// CONDITIONAL FIELDS
// ═══════════════════════════════════════════
function initConditionalFields() {
    // Edit page conditional field
    const golfedInputs = document.querySelectorAll('#edit-form input[name="golfed_before"], .section-card:not(.modal-body .section-card) input[name="golfed_before"]');
    const conditionalField = document.getElementById('prior-group-field');
    if (!conditionalField) return;

    function update() {
        const container = conditionalField.closest('form') || document;
        const checked = container.querySelector('input[name="golfed_before"]:checked');
        if (checked && checked.value === 'yes') {
            conditionalField.classList.add('visible');
        } else {
            conditionalField.classList.remove('visible');
        }
    }

    golfedInputs.forEach(input => input.addEventListener('change', update));
    update();
}

function initModalConditionalFields() {
    const modal = document.getElementById('new-booking-modal');
    if (!modal) return;

    const golfedInputs = modal.querySelectorAll('input[name="golfed_before"]');
    const conditionalField = document.getElementById('modal-prior-group-field');
    if (!conditionalField) return;

    function update() {
        const checked = modal.querySelector('input[name="golfed_before"]:checked');
        if (checked && checked.value === 'yes') {
            conditionalField.classList.add('visible');
        } else {
            conditionalField.classList.remove('visible');
        }
    }

    golfedInputs.forEach(input => input.addEventListener('change', update));
    update();
}

// ═══════════════════════════════════════════
// TEE TIME BUILDER (edit page)
// ═══════════════════════════════════════════
let teeTimeDayCount = 0;
let slotCounts = {};

function initTeeTimes(existingCount) {
    teeTimeDayCount = existingCount || 0;
}

function addTeeDay() {
    const container = document.getElementById('tee-days-container');
    if (!container) return;
    _addTeeDayTo(container, 'tee');
}

function _addTeeDayTo(container, prefix) {
    const dayIndex = (prefix === 'modal-tee') ? modalTeeDayCount++ : teeTimeDayCount++;
    const idPrefix = prefix;

    const dayDiv = document.createElement('div');
    dayDiv.className = 'tee-day';
    dayDiv.id = `${idPrefix}-day-${dayIndex}`;
    dayDiv.innerHTML = `
        <div class="tee-day-header">
            <div>
                <span class="tee-day-label">Tee Day</span>
                <span class="tee-day-date-display" id="${idPrefix}-day-display-${dayIndex}"></span>
            </div>
            <button type="button" class="btn-remove" onclick="document.getElementById('${idPrefix}-day-${dayIndex}').remove()">Remove Day</button>
        </div>
        <div class="form-group">
            <label>Date</label>
            <input type="date" name="tee_day_date_${dayIndex}" onchange="updateDayDisplay('${idPrefix}-day-display-${dayIndex}', this.value)">
        </div>
        <div id="${idPrefix}-slots-${dayIndex}"></div>
        <button type="button" class="btn btn-add-slot btn-sm" onclick="addSlotTo('${idPrefix}', ${dayIndex})">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Add Tee Time
        </button>
    `;

    container.appendChild(dayDiv);
    // Add first slot
    if (!slotCounts[`${idPrefix}-${dayIndex}`]) slotCounts[`${idPrefix}-${dayIndex}`] = 0;
    addSlotTo(idPrefix, dayIndex);
}

function updateDayDisplay(displayId, dateVal) {
    const display = document.getElementById(displayId);
    if (display && dateVal) {
        const d = new Date(dateVal + 'T00:00:00');
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        display.textContent = `${days[d.getDay()]}, ${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
    }
}

function addSlotTo(prefix, dayIndex) {
    const key = `${prefix}-${dayIndex}`;
    if (!slotCounts[key]) slotCounts[key] = 0;
    const slotIndex = slotCounts[key]++;

    const container = document.getElementById(`${prefix}-slots-${dayIndex}`);
    if (!container) return;

    const slotDiv = document.createElement('div');
    slotDiv.className = 'tee-slot-card';
    slotDiv.id = `${prefix}-slot-${dayIndex}-${slotIndex}`;

    const ampmName = `tee_slot_ampm_${dayIndex}_${slotIndex}`;

    slotDiv.innerHTML = `
        <div class="tee-slot-top">
            <div class="tee-slot-field tee-slot-field-course">
                <span class="tee-slot-field-label">Course</span>
                <select name="tee_slot_course_${dayIndex}_${slotIndex}">
                    <option value="">—</option>
                    <option value="Jones">Jones</option>
                    <option value="Palmer">Palmer</option>
                    <option value="Crispin">Crispin</option>
                </select>
            </div>
            <div class="tee-slot-field tee-slot-field-time">
                <span class="tee-slot-field-label">Time</span>
                <input type="text" name="tee_slot_time_${dayIndex}_${slotIndex}" placeholder="7:30">
            </div>
            <div class="tee-slot-field tee-slot-field-ampm">
                <span class="tee-slot-field-label">AM/PM</span>
                <div class="toggle-group toggle-group-sm">
                    <label class="toggle-option"><input type="radio" name="${ampmName}" value="AM" checked> AM</label>
                    <label class="toggle-option"><input type="radio" name="${ampmName}" value="PM"> PM</label>
                </div>
            </div>
            <div class="tee-slot-field tee-slot-field-holes">
                <span class="tee-slot-field-label">Holes</span>
                <input type="text" name="tee_slot_holes_${dayIndex}_${slotIndex}" placeholder="18">
            </div>
            <div class="tee-slot-remove">
                <button type="button" class="btn-remove" onclick="document.getElementById('${prefix}-slot-${dayIndex}-${slotIndex}').remove()">×</button>
            </div>
        </div>
        <div class="tee-slot-bottom">
            <span class="tee-slot-field-label">Notes</span>
            <input type="text" name="tee_slot_notes_${dayIndex}_${slotIndex}" class="tee-slot-notes" placeholder="Notes for this tee time...">
        </div>
    `;

    container.appendChild(slotDiv);
    // Init toggles on the new AM/PM group
    slotDiv.querySelectorAll('.toggle-group').forEach(group => {
        group.querySelectorAll('.toggle-option').forEach(opt => {
            const input = opt.querySelector('input');
            if (input && input.checked) opt.classList.add('active');
            opt.addEventListener('click', () => {
                group.querySelectorAll('.toggle-option').forEach(o => o.classList.remove('active'));
                opt.classList.add('active');
                if (input) input.checked = true;
            });
        });
    });
}

// ═══════════════════════════════════════════
// MODAL TEE TIME BUILDER
// ═══════════════════════════════════════════
let modalTeeDayCount = 0;

function addModalTeeDay() {
    const container = document.getElementById('modal-tee-days-container');
    if (!container) return;
    _addTeeDayTo(container, 'modal-tee');
}

// Legacy compat for edit page
function updateTeeDayDisplay(dayIndex, dateVal) {
    updateDayDisplay(`tee-day-display-${dayIndex}`, dateVal);
}

function removeTeeDay(dayIndex) {
    const day = document.getElementById(`tee-day-${dayIndex}`);
    if (day) day.remove();
}

function addTeeSlot(dayIndex) {
    addSlotTo('tee', dayIndex);
}

function removeTeeSlot(dayIndex, slotIndex) {
    const slot = document.getElementById(`tee-slot-${dayIndex}-${slotIndex}`);
    if (slot) slot.remove();
}

// ═══════════════════════════════════════════
// SELECT ALL / BULK ACTIONS
// ═══════════════════════════════════════════
function initSelectAll() {
    const selectAll = document.getElementById('select-all');
    if (!selectAll) return;

    selectAll.addEventListener('change', () => {
        document.querySelectorAll('.row-checkbox').forEach(cb => {
            cb.checked = selectAll.checked;
        });
        updateBulkBar();
    });

    document.querySelectorAll('.row-checkbox').forEach(cb => {
        cb.addEventListener('change', updateBulkBar);
    });
}

function updateBulkBar() {
    const checked = document.querySelectorAll('.row-checkbox:checked');
    const bar = document.getElementById('bulk-bar');
    const count = document.getElementById('bulk-count');
    if (bar) {
        if (checked.length > 0) {
            bar.classList.add('visible');
            count.textContent = checked.length;
        } else {
            bar.classList.remove('visible');
        }
    }
}

function initBulkActions() {
    const form = document.getElementById('bulk-form');
    if (!form) return;

    document.querySelectorAll('.bulk-action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            document.getElementById('bulk-action').value = action;
            const existing = form.querySelectorAll('input[name="booking_ids"]');
            existing.forEach(e => e.remove());
            document.querySelectorAll('.row-checkbox:checked').forEach(cb => {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'booking_ids';
                input.value = cb.value;
                form.appendChild(input);
            });
            form.submit();
        });
    });
}

// ═══════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════
function initDateDayDisplay() {
    document.querySelectorAll('.tee-day').forEach(day => {
        const dateInput = day.querySelector('input[type="date"]');
        if (dateInput && dateInput.value) {
            const displayEl = day.querySelector('.tee-day-date-display');
            if (displayEl) {
                updateDayDisplay(displayEl.id, dateInput.value);
            }
        }
    });
}

function autoFadeFlash() {
    document.querySelectorAll('.flash').forEach(f => {
        setTimeout(() => {
            f.style.transition = 'opacity 0.5s ease';
            f.style.opacity = '0';
            setTimeout(() => f.remove(), 500);
        }, 5000);
    });
}

// ═══════════════════════════════════════════
// SETTINGS MODAL
// ═══════════════════════════════════════════
function openSettingsModal() {
    const modal = document.getElementById('settings-modal');
    if (modal) {
        modal.classList.add('open');
        document.body.style.overflow = 'hidden';
        // Only load users if the users panel exists (admin only)
        if (document.getElementById('settings-users-list')) {
            loadSettingsUsers();
        }
        initToggles();
    }
    // Close mobile sidebar if open
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
}

function closeSettingsModal() {
    const modal = document.getElementById('settings-modal');
    if (modal) {
        modal.classList.remove('open');
        document.body.style.overflow = '';
    }
    // Clean settings param from URL without reload
    const url = new URL(window.location);
    if (url.searchParams.has('settings')) {
        url.searchParams.delete('settings');
        window.history.replaceState({}, '', url.toString());
    }
}

function autoOpenSettings() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('settings') === '1') {
        openSettingsModal();
    }
}

function switchSettingsTab(tabName, btn) {
    // Hide all panels
    document.querySelectorAll('.settings-panel').forEach(p => p.style.display = 'none');
    // Deactivate all tabs
    document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
    // Show target panel
    const panel = document.getElementById(`settings-tab-${tabName}`);
    if (panel) panel.style.display = 'block';
    // Activate clicked tab
    btn.classList.add('active');
}

function loadSettingsUsers() {
    const container = document.getElementById('settings-users-list');
    if (!container) return;

    fetch('/api/users')
        .then(r => r.json())
        .then(users => {
            if (users.length === 0) {
                container.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:0.85rem;">No users found.</div>';
                return;
            }

            // Get current user ID from the sidebar avatar (hack but works without extra data attr)
            const currentUsername = document.querySelector('.sidebar-user-name')?.textContent?.trim();

            container.innerHTML = users.map(u => {
                const isSelf = u.username === currentUsername;
                const initials = u.username.substring(0, 2).toUpperCase();
                const created = u.created_at ? u.created_at.split(' ')[0] : '';

                return `
                <div class="settings-user-row">
                    <div class="settings-user-avatar">${initials}</div>
                    <div class="settings-user-info">
                        <div class="settings-user-name">
                            ${u.username}
                            ${isSelf ? '<span class="settings-user-self-label">(you)</span>' : ''}
                        </div>
                        <div class="settings-user-meta">
                            <span class="user-badge ${u.role}">${u.role}</span>
                            ${created ? ' &middot; joined ' + created : ''}
                        </div>
                    </div>
                    <div class="settings-user-actions">
                        <form method="POST" action="/users/${u.id}/edit" style="display:flex;gap:5px;align-items:center;">
                            <select name="role" style="min-width:90px;padding:4px 8px;font-size:0.78rem;">
                                <option value="editor" ${u.role === 'editor' ? 'selected' : ''}>Editor</option>
                                <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
                            </select>
                            <input type="password" name="password" placeholder="New pw" style="width:100px;padding:4px 8px;font-size:0.78rem;">
                            <button type="submit" class="btn btn-sm">Save</button>
                        </form>
                        ${!isSelf ? `
                        <form method="POST" action="/users/${u.id}/delete" onsubmit="return confirm('Delete user ${u.username}?')">
                            <button type="submit" class="btn btn-sm btn-danger">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                            </button>
                        </form>` : ''}
                    </div>
                </div>`;
            }).join('');
        })
        .catch(err => {
            container.innerHTML = '<div style="padding:16px;text-align:center;color:#f87171;font-size:0.85rem;">Failed to load users.</div>';
        });
}

// Close settings modal on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.id === 'settings-modal') {
        closeSettingsModal();
    }
});

// ═══════════════════════════════════════════
// THEME TOGGLE (light/dark)
// ═══════════════════════════════════════════
function initTheme() {
    const saved = localStorage.getItem('gbd-theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    const checkbox = document.getElementById('theme-toggle-checkbox');
    if (checkbox) checkbox.checked = (saved === 'light');
}

function toggleTheme(isLight) {
    const theme = isLight ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('gbd-theme', theme);
}

// ═══════════════════════════════════════════
// COURSE ROUNDS TOGGLE
// ═══════════════════════════════════════════
function toggleRoundsField(checkbox, inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (checkbox.checked) {
        input.classList.add('enabled');
    } else {
        input.classList.remove('enabled');
        input.value = '';
    }
}
