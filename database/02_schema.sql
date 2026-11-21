USE elphynix_research;

-- Users includes ADMIN and VENDOR accounts. Passwords must be Werkzeug hashes.
CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(100) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  role ENUM('ADMIN','VENDOR') NOT NULL DEFAULT 'VENDOR',
  email VARCHAR(255) NOT NULL,
  full_name VARCHAR(150) NULL,
  company_name VARCHAR(200) NULL,
  complete INT UNSIGNED NOT NULL DEFAULT 0,
  terminate INT UNSIGNED NOT NULL DEFAULT 0,
  quotafull INT UNSIGNED NOT NULL DEFAULT 0,
  security_terminate INT UNSIGNED NOT NULL DEFAULT 0,
  user_token CHAR(32) NULL UNIQUE,
  is_shown ENUM('show','hide') NOT NULL DEFAULT 'show',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS client (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(100) NOT NULL UNIQUE,
  email VARCHAR(255) NOT NULL,
  company_name VARCHAR(200) NOT NULL DEFAULT '',
  token VARCHAR(64) NOT NULL UNIQUE,
  is_shown ENUM('show','hide') NOT NULL DEFAULT 'show',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS project (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  project_identifier VARCHAR(100) NOT NULL UNIQUE,
  project_identifier_token VARCHAR(64) NOT NULL,
  status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
  ir DECIMAL(5,2) NULL,
  loi INT UNSIGNED NULL,
  quota INT UNSIGNED NOT NULL DEFAULT 0,
  counts INT UNSIGNED NOT NULL DEFAULT 0,
  cpi DECIMAL(12,4) NULL,
  client_id BIGINT UNSIGNED NULL,
  created_by BIGINT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_project_status_created(status, created_at),
  CONSTRAINT fk_project_client FOREIGN KEY (client_id) REFERENCES client(id) ON DELETE SET NULL,
  CONSTRAINT fk_project_creator FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS security_terminate_flag (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  project_id VARCHAR(100) NOT NULL,
  flag BOOLEAN NOT NULL DEFAULT FALSE,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_security_project(project_id),
  CONSTRAINT fk_security_project FOREIGN KEY (project_id)
    REFERENCES project(project_identifier) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS survey_response (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  status ENUM('STARTED','COMPLETE','TERMINATE','QUOTAFULL','SECURITYTERMINATE') NOT NULL DEFAULT 'STARTED',
  ip_address VARCHAR(45) NULL,
  start_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  end_time DATETIME NULL,
  country VARCHAR(100) NULL,
  project_id VARCHAR(100) NOT NULL,
  u_id VARCHAR(150) NOT NULL,
  vendor_username VARCHAR(100) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_response_project_uid(project_id, u_id),
  INDEX idx_response_status(status),
  INDEX idx_response_start(start_time),
  INDEX idx_response_country(country),
  CONSTRAINT fk_response_project FOREIGN KEY (project_id)
    REFERENCES project(project_identifier) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS request_log (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  request_id CHAR(36) NOT NULL,
  method VARCHAR(10) NULL,
  endpoint VARCHAR(500) NULL,
  user_agent VARCHAR(1000) NULL,
  ip_address VARCHAR(45) NULL,
  username VARCHAR(100) NULL,
  response_status SMALLINT UNSIGNED NULL,
  error_message VARCHAR(255) NULL,
  processing_time_ms INT UNSIGNED NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME NULL,
  is_successful BOOLEAN NOT NULL DEFAULT FALSE,
  INDEX idx_request_created(created_at),
  INDEX idx_request_endpoint(endpoint(191)),
  INDEX idx_request_status(response_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
