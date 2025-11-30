-- =============================
-- CREATE TABLES
-- =============================

CREATE TABLE clients (
    client_id      SERIAL PRIMARY KEY,
    client_name    TEXT NOT NULL,
    industry       TEXT,
    contact_email  TEXT
);

CREATE TABLE projects (
    project_id   SERIAL PRIMARY KEY,
    project_name TEXT NOT NULL,
    start_date   DATE,
    end_date     DATE,
    client_id    INTEGER REFERENCES clients(client_id),
    status       TEXT,
    budget       NUMERIC
);

CREATE TABLE orders (
    order_id    SERIAL PRIMARY KEY,
    project_id  INTEGER REFERENCES projects(project_id),
    order_date  DATE,
    amount      NUMERIC,
    status      TEXT
);

-- =============================
-- INSERT INTO clients (20 rows)
-- =============================

INSERT INTO clients (client_name, industry, contact_email) VALUES
('Alpha Corp', 'technology', 'contact@alphacorp.com'),
('Beta Solutions', 'finance', 'info@betasolutions.com'),
('Gamma Industries', 'manufacturing', 'sales@gamma.com'),
('Delta Systems', 'technology', 'support@delta.com'),
('Epsilon Group', 'energy', 'hello@epsilon.com'),
('Zeta Partners', 'consulting', 'team@zeta.com'),
('Eta Holdings', 'technology', 'contact@eta.com'),
('Theta Innovations', 'manufacturing', 'info@theta.com'),
('Iota Analytics', 'finance', 'contact@iota.com'),
('Kappa Labs', 'technology', 'support@kappa.com'),
('Lambda Corp', 'energy', 'hello@lambda.com'),
('Mu Dynamics', 'finance', 'info@mu.com'),
('Nu Engineering', 'manufacturing', 'sales@nu.com'),
('Xi Ventures', 'consulting', 'team@xi.com'),
('Omicron Systems', 'energy', 'info@omicron.com'),
('Pi Software', 'technology', 'help@pi.com'),
('Rho Advisors', 'consulting', 'contact@rho.com'),
('Sigma Motors', 'manufacturing', 'support@sigma.com'),
('Tau Finance', 'finance', 'team@tau.com'),
('Upsilon Tech', 'technology', 'info@upsilon.com');


-- =============================
-- INSERT INTO projects (20 rows)
-- =============================

INSERT INTO projects (project_name, start_date, end_date, client_id, status, budget) VALUES
('Website Revamp', '2021-01-10', '2021-05-20', 1, 'completed', 50000),
('Mobile App Development', '2022-03-15', NULL, 2, 'in_progress', 120000),
('Factory Automation', '2020-09-01', '2022-02-28', 3, 'completed', 350000),
('Cloud Migration', '2023-04-01', NULL, 4, 'in_progress', 90000),
('Energy Audit Phase 1', '2022-01-05', '2022-07-30', 5, 'completed', 45000),
('Consulting Program A', '2023-05-20', NULL, 6, 'pending', 30000),
('AI Model Deployment', '2021-11-10', '2022-09-25', 7, 'completed', 140000),
('Manufacturing Dashboard', '2023-01-15', NULL, 8, 'in_progress', 60000),
('Financial Risk Tool', '2024-02-01', NULL, 9, 'pending', 75000),
('Backend API Upgrade', '2020-05-05', '2020-11-18', 10, 'completed', 20000),
('Solar Panel Mapping', '2021-08-10', NULL, 11, 'in_progress', 110000),
('Fraud Detection v2', '2024-01-20', NULL, 12, 'pending', 130000),
('Robotics Pilot', '2019-03-01', '2020-08-30', 13, 'completed', 250000),
('Market Analysis Q4', '2023-09-01', '2023-12-15', 14, 'completed', 15000),
('Energy Optimization', '2022-06-01', NULL, 15, 'in_progress', 80000),
('AI Chatbot Initiative', '2023-02-18', NULL, 16, 'pending', 40000),
('Logistics Overhaul', '2020-10-05', '2021-12-20', 17, 'completed', 180000),
('Electric Vehicle Study', '2023-05-01', NULL, 18, 'in_progress', 95000),
('Accounting Automation', '2021-07-12', '2022-03-19', 19, 'completed', 70000),
('Analytics Platform', '2024-01-10', NULL, 20, 'pending', 160000);


-- =============================
-- INSERT INTO orders (20 rows)
-- =============================
INSERT INTO orders (project_id, order_date, amount, status) VALUES
(1, '2021-02-10', 10000, 'completed'),
(1, '2021-04-15', 40000, 'completed'),
(2, '2023-05-01', 20000, 'in_progress'),
(2, '2023-08-12', 30000, 'in_progress'),
(3, '2021-03-22', 150000, 'completed'),
(3, '2021-11-10', 200000, 'completed'),
(4, '2023-06-30', 45000, 'in_progress'),
(5, '2022-03-01', 15000, 'completed'),
(6, '2023-07-05', 8000, 'pending'),
(7, '2021-12-25', 50000, 'completed'),
(8, '2023-03-14', 20000, 'in_progress'),
(9, '2024-03-01', 12000, 'pending'),
(10, '2020-07-18', 8000, 'completed'),
(11, '2021-10-05', 35000, 'in_progress'),
(12, '2024-02-15', 25000, 'pending'),
(13, '2019-06-10', 100000, 'completed'),
(14, '2023-10-12', 5000, 'completed'),
(15, '2022-08-22', 22000, 'in_progress'),
(16, '2023-03-01', 18000, 'pending'),
(17, '2021-01-15', 45000, 'completed');

