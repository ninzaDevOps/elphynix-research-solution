USE elphynix_research;

-- Generate two separate Werkzeug hashes before running this file.
-- Replace CHANGE_ME_ADMIN_WERKZEUG_HASH for admin and CHANGE_ME_VENDOR_WERKZEUG_HASH for demo_vendor.
-- Never use demo accounts or demo data in production.

INSERT INTO users (username, password, role, email, full_name, active)
VALUES ('admin', 'CHANGE_ME_ADMIN_WERKZEUG_HASH', 'ADMIN', 'admin@example.invalid', 'Elphynix Administrator', TRUE)
ON DUPLICATE KEY UPDATE username=VALUES(username);

INSERT INTO users (username, password, role, email, company_name, user_token, is_shown, active)
SELECT 'demo_vendor', 'CHANGE_ME_VENDOR_WERKZEUG_HASH', 'VENDOR', 'vendor@example.invalid', 'Demo Vendor', REPLACE(UUID(),'-',''), 'show', TRUE
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username='demo_vendor');

INSERT INTO client (username, email, company_name, token, is_shown)
VALUES ('demo_client', 'client@example.invalid', 'Elphynix Demo Client', REPLACE(UUID(),'-',''), 'show')
ON DUPLICATE KEY UPDATE username=VALUES(username);

INSERT INTO project (project_identifier, project_identifier_token, status, ir, loi, quota, counts, cpi, client_id, created_by)
SELECT 'DEMO-RESEARCH-001', 'DEMO000001', 'ACTIVE', 50.00, 15, 500, 0, 2.5000,
       (SELECT id FROM client WHERE username='demo_client'),
       (SELECT id FROM users WHERE username='admin')
WHERE NOT EXISTS (SELECT 1 FROM project WHERE project_identifier='DEMO-RESEARCH-001');

INSERT INTO security_terminate_flag (project_id, flag)
SELECT 'DEMO-RESEARCH-001', FALSE
WHERE NOT EXISTS (SELECT 1 FROM security_terminate_flag WHERE project_id='DEMO-RESEARCH-001');
