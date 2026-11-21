# Elphynix Research Solution — MySQL setup

Run the SQL files in this exact order on a **fresh** `elphynix_research` database from MySQL Workbench or the MySQL command line.

1. `01_create_database.sql`
2. `02_schema.sql`
3. Generate two separate password hashes and replace the placeholders in `03_seed_data.sql`.
4. `03_seed_data.sql`

## Generate password hashes

Run twice from the project virtual environment, using different strong passwords (at least 12 characters):

```powershell
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('Choose-A-Unique-Admin-Password'))"
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('Choose-A-Different-Vendor-Password'))"
```

Put the first output in `CHANGE_ME_ADMIN_WERKZEUG_HASH` and the second in `CHANGE_ME_VENDOR_WERKZEUG_HASH`.

The seed creates these local demo identities:

- Admin username: `admin`
- Demo vendor username: `demo_vendor`
- Demo client username: `demo_client`
- Demo project identifier: `DEMO-RESEARCH-001`

The SQL file intentionally contains no usable default password. Do not use demo identities in production; create named accounts and remove demo data before launch.

## Local database account

For local development, create a dedicated account rather than using MySQL `root` for the Flask application:

```sql
CREATE USER 'elphynix_app'@'localhost' IDENTIFIED BY 'REPLACE_WITH_A_LONG_RANDOM_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE ON elphynix_research.* TO 'elphynix_app'@'localhost';
FLUSH PRIVILEGES;
```

For AWS RDS, create an application account with the same limited database privileges and configure the host as the RDS endpoint. Do not use the RDS master account in the Flask application.

## Important schema contract

The Flask code uses the singular table names `client`, `project`, and `survey_response`. The schema in `02_schema.sql` intentionally defines those exact names and the columns referenced by the Flask routes. Do not mix this schema with an older pluralized schema from another version of the application.

**If you already ran the original SQL scripts:** do not rerun these files over a database that contains data. Back up the database first and ask for a migration plan; `CREATE TABLE IF NOT EXISTS` does not retrofit columns into existing tables.
