-- =============================================================
-- CyberVerse Learning Paths Seed
-- Generated from: F:\hacking pendrive content catalog
-- Content is metadata only — no copyrighted files are stored.
-- =============================================================

-- ─────────────────────────────────────────────────────────────
-- LEARNING PATHS
-- ─────────────────────────────────────────────────────────────
INSERT INTO learning_paths (id, slug, title, description, difficulty, estimated_hours, icon, color, is_published, sort_order) VALUES
(
  'path-ceh-foundations',
  'ceh-foundations',
  'CEH Foundations',
  'Master the core concepts of ethical hacking from the ground up using the official CEH v12 curriculum. Covers networking, OS fundamentals, footprinting, scanning, enumeration, and system hacking.',
  'beginner',
  40,
  'shield',
  '#22d3ee',
  true,
  1
),
(
  'path-ceh-advanced',
  'ceh-advanced',
  'CEH Advanced Techniques',
  'Deep dive into advanced ethical hacking: web app attacks, session hijacking, SQL injection, cryptography, cloud security, and IoT hacking — fully aligned to CEH v12.',
  'intermediate',
  60,
  'zap',
  '#a78bfa',
  true,
  2
),
(
  'path-hands-on-hacking',
  'hands-on-hacking',
  'Hands-On Hacking (No Theory)',
  'Pure practical hacking skills using real tools: Burp Suite Pro, HTTP Debugger, OTP bypass, IDOR, price tampering, and account takeover — all in sandboxed environments.',
  'advanced',
  25,
  'terminal',
  '#34d399',
  true,
  3
);

-- ─────────────────────────────────────────────────────────────
-- COURSES
-- ─────────────────────────────────────────────────────────────
INSERT INTO courses (id, path_id, slug, title, description, difficulty, estimated_hours, sort_order, is_published) VALUES
-- Path 1: CEH Foundations
(
  'course-ceh-fundamentals',
  'path-ceh-foundations',
  'ceh-v12-fundamentals',
  'CEH v12 — Ethical Hacking Fundamentals',
  'Introduction to ethical hacking, footprinting, reconnaissance, scanning networks, enumeration, vulnerability analysis, and system hacking basics.',
  'beginner', 20, 1, true
),
(
  'course-ceh-system-network',
  'path-ceh-advanced',
  'ceh-v12-system-and-network-security',
  'CEH v12 — System & Network Security',
  'System penetration testing, malware threats, network sniffing, ARP poisoning, session hijacking, and evading IDS, firewalls, and honeypots.',
  'intermediate', 25, 2, true
),
(
  'course-ceh-advanced-cybersec',
  'path-ceh-advanced',
  'ceh-v12-advanced-cybersecurity',
  'CEH v12 — Advanced Cybersecurity',
  'Web server attacks, web application hacking, SQL injection, hacking wireless networks, mobile platform hacking, IoT hacking, cloud computing security, and cryptography.',
  'advanced', 35, 3, true
),
(
  'course-burp-suite',
  'path-hands-on-hacking',
  'burp-suite-live-practical',
  'Burp Suite Live Practical',
  'Hands-on sessions with Burp Suite Pro: OTP bypass, account takeover via IDOR, automated form flooding, response manipulation, and price tampering on live sandboxed targets.',
  'advanced', 15, 1, true
),
(
  'course-http-debugger',
  'path-hands-on-hacking',
  'http-debugger-pro',
  'HTTP Debugger Pro Basics',
  'Learn to intercept and manipulate HTTP traffic with HTTP Debugger Pro, including hacking sandbox web games and API parameter tampering.',
  'intermediate', 5, 2, true
),
(
  'course-ceh-pdf-modules',
  'path-ceh-foundations',
  'ceh-v12-official-modules',
  'CEH v12 — Official Module PDFs (20 Modules)',
  'The complete 20-module CEH v12 official study guide covering all exam domains, from introduction to ethical hacking through to cryptography and cloud security.',
  'beginner', 40, 2, true
);

-- ─────────────────────────────────────────────────────────────
-- MODULES (CEH v12 Official PDF Modules — 20 modules)
-- ─────────────────────────────────────────────────────────────
INSERT INTO course_modules (id, course_id, title, description, sort_order, resource_type, resource_label) VALUES
('mod-ceh-01', 'course-ceh-pdf-modules', 'Module 01 – Introduction to Ethical Hacking', 'Fundamentals of security, ethical hacking phases, types of hackers, legal implications, and the CEH methodology.', 1, 'pdf', 'CEH v12 - Module01.pdf'),
('mod-ceh-02', 'course-ceh-pdf-modules', 'Module 02 – Footprinting and Reconnaissance', 'Passive and active reconnaissance techniques, OSINT, Google hacking, whois, DNS enumeration, and social engineering vectors.', 2, 'pdf', 'CEH v12 - Module02.pdf'),
('mod-ceh-03', 'course-ceh-pdf-modules', 'Module 03 – Scanning Networks', 'Network scanning techniques, port scanning, OS fingerprinting, ping sweeps, vulnerability scanning, and countermeasures.', 3, 'pdf', 'CEH v12 - Module03.pdf'),
('mod-ceh-04', 'course-ceh-pdf-modules', 'Module 04 – Enumeration', 'NetBIOS, SNMP, LDAP, NTP, SMTP, and DNS enumeration techniques, tools, and defensive strategies.', 4, 'pdf', 'CEH v12 - Module04.pdf'),
('mod-ceh-05', 'course-ceh-pdf-modules', 'Module 05 – Vulnerability Analysis', 'Vulnerability assessment concepts, classification systems (CVE, CVSS), scanning tools, and vulnerability management lifecycle.', 5, 'pdf', 'CEH v12 - Module05.pdf'),
('mod-ceh-06', 'course-ceh-pdf-modules', 'Module 06 – System Hacking', 'Password cracking, privilege escalation, maintaining access, hiding files, covering tracks, and steganography.', 6, 'pdf', 'CEH v12 - Module06.pdf'),
('mod-ceh-07', 'course-ceh-pdf-modules', 'Module 07 – Malware Threats', 'Trojans, viruses, worms, ransomware, fileless malware, malware analysis techniques, and countermeasures.', 7, 'pdf', 'CEH v12 - Module07.pdf'),
('mod-ceh-08', 'course-ceh-pdf-modules', 'Module 08 – Sniffing', 'Network sniffing concepts, passive/active sniffing, ARP poisoning, MAC flooding, DNS poisoning, and detection tools.', 8, 'pdf', 'CEH v12 - Module08.pdf'),
('mod-ceh-09', 'course-ceh-pdf-modules', 'Module 09 – Social Engineering', 'Social engineering attacks, phishing, vishing, identity theft, impersonation, and human-based attack defenses.', 9, 'pdf', 'CEH v12 - Module09.pdf'),
('mod-ceh-10', 'course-ceh-pdf-modules', 'Module 10 – Denial-of-Service', 'DoS and DDoS attacks, botnets, attack tools, DDoS mitigation, and protection strategies.', 10, 'pdf', 'CEH v12 - Module10.pdf'),
('mod-ceh-11', 'course-ceh-pdf-modules', 'Module 11 – Session Hijacking', 'Session hijacking techniques, cross-site scripting, packet analysis, TCP/IP hijacking, and session fixation.', 11, 'pdf', 'CEH v12 - Module11.pdf'),
('mod-ceh-12', 'course-ceh-pdf-modules', 'Module 12 – Evading IDS, Firewalls, and Honeypots', 'Firewall types, IDS evasion, honeypots, detection methods, and bypass techniques.', 12, 'pdf', 'CEH v12 - Module12.pdf'),
('mod-ceh-13', 'course-ceh-pdf-modules', 'Module 13 – Hacking Web Servers', 'Web server attacks, misconfiguration exploitation, patch management, web server security auditing.', 13, 'pdf', 'CEH v12 - Module13.pdf'),
('mod-ceh-14', 'course-ceh-pdf-modules', 'Module 14 – Hacking Web Applications', 'OWASP Top 10, web application attacks, authentication bypass, XSS, CSRF, file inclusion, and input validation.', 14, 'pdf', 'CEH v12 - Module14.pdf'),
('mod-ceh-15', 'course-ceh-pdf-modules', 'Module 15 – SQL Injection', 'SQL injection types, blind SQLi, time-based attacks, automated tools, detection, and prevention.', 15, 'pdf', 'CEH v12 - Module15.pdf'),
('mod-ceh-16', 'course-ceh-pdf-modules', 'Module 16 – Hacking Wireless Networks', 'Wireless concepts, WEP/WPA/WPA2 attacks, rogue AP, evil twin, wireless IDS evasion.', 16, 'pdf', 'CEH v12 - Module16.pdf'),
('mod-ceh-17', 'course-ceh-pdf-modules', 'Module 17 – Hacking Mobile Platforms', 'Android/iOS attack vectors, mobile device management, OWASP Mobile Top 10, mobile pen testing.', 17, 'pdf', 'CEH v12 - Module17.pdf'),
('mod-ceh-18', 'course-ceh-pdf-modules', 'Module 18 – IoT and OT Hacking', 'IoT architecture, attack surfaces, IoT hacking methodology, OT/SCADA security, and defensive countermeasures.', 18, 'pdf', 'CEH v12 - Module18.pdf'),
('mod-ceh-19', 'course-ceh-pdf-modules', 'Module 19 – Cloud Computing', 'Cloud models, cloud attacks, container security, serverless security, cloud pen testing, and AWS/Azure security.', 19, 'pdf', 'CEH v12 - Module19.pdf'),
('mod-ceh-20', 'course-ceh-pdf-modules', 'Module 20 – Cryptography', 'Encryption algorithms, PKI, digital signatures, disk encryption, cryptanalysis, and quantum cryptography.', 20, 'pdf', 'CEH v12 - Module20.pdf');

-- ─────────────────────────────────────────────────────────────
-- LESSONS (Video lessons from CEH v12 Specialization — System & Network Security)
-- ─────────────────────────────────────────────────────────────
INSERT INTO lessons (id, module_id, title, slug, duration_seconds, sort_order, is_free_preview) VALUES
-- System Security & Malware Threats → System Hacking sub-module
('les-sn-01', 'mod-ceh-06', 'System Hacking Introduction', 'system-hacking-intro', 420, 1, true),
('les-sn-02', 'mod-ceh-06', 'Password Cracking Techniques', 'password-cracking-techniques', 480, 2, false),
('les-sn-03', 'mod-ceh-06', 'Types of Password Attacks', 'types-of-password-attacks', 360, 3, false),
('les-sn-04', 'mod-ceh-06', 'Microsoft Authentication', 'microsoft-authentication', 450, 4, false),
('les-sn-05', 'mod-ceh-06', 'Password Salting', 'password-salting', 300, 5, false),
('les-sn-06', 'mod-ceh-06', 'Demo: How Attackers Crack Passwords with Virtual Machines', 'demo-cracking-passwords-vms', 600, 6, false),
-- Malware Threats
('les-ml-01', 'mod-ceh-07', 'Malware Threats Overview', 'malware-threats-overview', 480, 1, true),
('les-ml-02', 'mod-ceh-07', 'Ways of Malware Propagation', 'ways-of-malware-propagation', 390, 2, false),
('les-ml-03', 'mod-ceh-07', 'What is a Virus?', 'what-is-a-virus', 360, 3, false),
('les-ml-04', 'mod-ceh-07', 'Types of Viruses', 'types-of-virus', 420, 4, false),
('les-ml-05', 'mod-ceh-07', 'How Does a Computer Get Infected?', 'how-computer-gets-infected', 350, 5, false),
('les-ml-06', 'mod-ceh-07', 'How to Defend Against a Virus Attack', 'defend-against-virus', 400, 6, false),
('les-ml-07', 'mod-ceh-07', 'What is a Rootkit?', 'what-is-rootkit', 390, 7, false),
('les-ml-08', 'mod-ceh-07', 'What is a Worm?', 'what-is-a-worm', 360, 8, false),
('les-ml-09', 'mod-ceh-07', 'Difference Between Worm and Virus', 'worm-vs-virus', 300, 9, false),
('les-ml-10', 'mod-ceh-07', 'Trojan and Trojan Horse', 'trojan-and-trojan-horse', 420, 10, false),
('les-ml-11', 'mod-ceh-07', 'Types of Trojans', 'types-of-trojan', 480, 11, false),
('les-ml-12', 'mod-ceh-07', 'How to Infect Systems Using Trojan', 'infect-systems-trojan', 450, 12, false),
('les-ml-13', 'mod-ceh-07', 'How to Identify Trojan Infections', 'identify-trojan-infections', 390, 13, false),
('les-ml-14', 'mod-ceh-07', 'How to Protect from Trojans', 'protect-from-trojans', 360, 14, false),
('les-ml-15', 'mod-ceh-07', 'Malware Pen Testing', 'malware-pen-testing', 480, 15, false),
-- Sniffing
('les-sn2-01', 'mod-ceh-08', 'Introduction to Network Sniffing', 'intro-network-sniffing', 420, 1, true),
('les-sn2-02', 'mod-ceh-08', 'Working of Network Sniffing', 'working-network-sniffing', 390, 2, false),
('les-sn2-03', 'mod-ceh-08', 'Types of Sniffing', 'types-of-sniffing', 360, 3, false),
('les-sn2-04', 'mod-ceh-08', 'Vulnerable Protocols in Sniffing', 'vulnerable-protocols-sniffing', 450, 4, false),
('les-sn2-05', 'mod-ceh-08', 'ARP Poisoning', 'arp-poisoning', 480, 5, false),
-- IDS, Firewalls, Honeypots
('les-ids-01', 'mod-ceh-12', 'Firewall, Evading IDS and Honeypots', 'firewall-evading-ids-honeypots', 480, 1, true),
('les-ids-02', 'mod-ceh-12', 'Types of Firewalls', 'types-of-firewalls', 390, 2, false),
('les-ids-03', 'mod-ceh-12', 'Uses of Firewall', 'uses-of-firewall', 360, 3, false),
('les-ids-04', 'mod-ceh-12', 'What is an IDS (Intrusion Detection System)?', 'what-is-ids', 420, 4, false),
('les-ids-05', 'mod-ceh-12', 'General Indications of System Intrusions', 'system-intrusion-indicators', 450, 5, false),
('les-ids-06', 'mod-ceh-12', 'Types of IDS', 'types-of-ids', 390, 6, false),
('les-ids-07', 'mod-ceh-12', 'Intrusion Detection Tool: Snort', 'snort-ids-tool', 480, 7, false),
('les-ids-08', 'mod-ceh-12', 'What is a Honeypot?', 'what-is-honeypot', 360, 8, false),
('les-ids-09', 'mod-ceh-12', 'Types of Honeypots', 'types-of-honeypots', 390, 9, false),
('les-ids-10', 'mod-ceh-12', 'Detecting Honeypots', 'detecting-honeypots', 420, 10, false),
-- IoT Hacking
('les-iot-01', 'mod-ceh-18', 'IoT Hacking Introduction', 'iot-hacking-intro', 420, 1, true),
('les-iot-02', 'mod-ceh-18', 'How Does IoT Work?', 'how-iot-works', 390, 2, false),
('les-iot-03', 'mod-ceh-18', 'Architecture of IoT', 'iot-architecture', 360, 3, false),
('les-iot-04', 'mod-ceh-18', 'IoT Technologies and Protocols', 'iot-technologies-protocols', 480, 4, false),
('les-iot-05', 'mod-ceh-18', 'IoT Communication Models', 'iot-communication-models', 565, 5, false),
('les-iot-06', 'mod-ceh-18', 'Understanding IoT Attacks', 'understanding-iot-attacks', 640, 6, false),
('les-iot-07', 'mod-ceh-18', 'IoT Attack Techniques', 'iot-attack-techniques', 587, 7, false),
('les-iot-08', 'mod-ceh-18', 'IoT Hacking Methodology', 'iot-hacking-methodology', 685, 8, false),
-- Burp Suite Practical
('les-burp-01', 'mod-ceh-14', 'Install Burp Suite Pro for Free', 'install-burp-suite-pro', 0, 1, true),
('les-burp-02', 'mod-ceh-14', 'Configure Burp Suite with Firefox Proxy', 'burp-firefox-proxy', 0, 2, false),
('les-burp-03', 'mod-ceh-14', 'OTP Bypass by Response Manipulation', 'otp-bypass-response-manipulation', 0, 3, false),
('les-burp-04', 'mod-ceh-14', 'OTP Bypass by Bruteforcing', 'otp-bypass-bruteforcing', 0, 4, false),
('les-burp-05', 'mod-ceh-14', 'Account Takeover by OTP Bypass', 'account-takeover-otp-bypass', 0, 5, false),
('les-burp-06', 'mod-ceh-14', 'Account Takeover by OTP Bypass at Frontend', 'account-takeover-otp-frontend', 0, 6, false),
('les-burp-07', 'mod-ceh-14', 'Account Takeover by IDOR', 'account-takeover-idor', 0, 7, false),
('les-burp-08', 'mod-ceh-14', 'Hacking Telegram Game Score with Burp', 'hacking-telegram-game-burp', 0, 8, false),
('les-burp-09', 'mod-ceh-14', 'Live Price Tampering Bugs on Websites', 'live-price-tampering', 0, 9, false),
('les-burp-10', 'mod-ceh-14', 'Automated Form Flooding with Burp', 'automated-form-flooding', 0, 10, false),
-- HTTP Debugger
('les-http-01', 'mod-ceh-14', 'Installing HTTP Debugger Pro', 'install-http-debugger', 0, 11, true),
('les-http-02', 'mod-ceh-14', 'Using HTTP Debugger Pro like a Pro', 'http-debugger-pro-advanced', 0, 12, false),
('les-http-03', 'mod-ceh-14', 'Price Tampering with TamperDev', 'price-tampering-tamperdev', 0, 13, false);

-- ─────────────────────────────────────────────────────────────
-- PATH ENROLLMENTS trigger table (populated at runtime by students)
-- ─────────────────────────────────────────────────────────────
-- student_path_progress is populated by the app, not seeded.
