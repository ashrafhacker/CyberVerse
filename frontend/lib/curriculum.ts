export const CURRICULUM: Record<string, {
  title: string;
  courseSlug: string;
  lessons: Array<{ id: string; title: string; type: 'video' | 'pdf'; asset: string; free: boolean; duration?: string }>;
}> = {
  'course-ceh-pdf-modules': {
    title: 'CEH v12 — Official Module PDFs',
    courseSlug: 'ceh-v12/pdfs',
    lessons: Array.from({ length: 20 }, (_, i) => ({
      id: `mod-ceh-${String(i + 1).padStart(2, '0')}`,
      title: `Module ${String(i + 1).padStart(2, '0')} — ${[
        'Introduction to Ethical Hacking', 'Footprinting and Reconnaissance',
        'Scanning Networks', 'Enumeration', 'Vulnerability Analysis',
        'System Hacking', 'Malware Threats', 'Sniffing', 'Social Engineering',
        'Denial-of-Service', 'Session Hijacking', 'Evading IDS, Firewalls & Honeypots',
        'Hacking Web Servers', 'Hacking Web Applications', 'SQL Injection',
        'Hacking Wireless Networks', 'Hacking Mobile Platforms',
        'IoT and OT Hacking', 'Cloud Computing', 'Cryptography',
      ][i]}`,
      type: 'pdf' as const,
      asset: `ceh-v12/pdfs/CEH v12 - Module${String(i + 1).padStart(2, '0')}.pdf`,
      free: i === 0,
    })),
  },
  'course-ceh-system-network': {
    title: 'CEH v12 — System & Network Security',
    courseSlug: 'ceh-v12-specialization/system-and-network-security',
    lessons: [
      { id: 'les-sn-01', title: 'System Hacking Introduction', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/02_1-2-system-penetration-testing/01_introduction-to-system-hacking.mp4', free: true, duration: '7:00' },
      { id: 'les-sn-02', title: 'Password Cracking Techniques', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/02_1-2-system-penetration-testing/04_tools-for-password-attack.mp4', free: false, duration: '8:00' },
      { id: 'les-sn-03', title: 'Types of Password Attacks', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/02_1-2-system-penetration-testing/03_types-of-password-attacks.mp4', free: false, duration: '6:00' },
      { id: 'les-sn-04', title: 'Microsoft Authentication', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/02_1-2-system-penetration-testing/05_microsoft-authentication.mp4', free: false, duration: '7:30' },
      { id: 'les-sn-05', title: 'Password Salting', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/02_1-2-system-penetration-testing/06_password-salting.mp4', free: false, duration: '5:00' },
      { id: 'les-sn-06', title: 'Demo: Cracking Passwords with VMs', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/02_1-2-system-penetration-testing/07_demo-how-attackers-crack-passwords-with-virtual-machines.mp4', free: false, duration: '10:00' },
      { id: 'les-ml-01', title: 'Malware Threats Overview', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/03_1-3-malware-threats/01_malware-threats.mp4', free: true, duration: '8:00' },
      { id: 'les-ml-02', title: 'Ways of Malware Propagation', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/03_1-3-malware-threats/02_ways-of-malware-propagation.mp4', free: false, duration: '6:30' },
      { id: 'les-ml-03', title: 'What is a Virus?', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/03_1-3-malware-threats/03_what-is-a-virus.mp4', free: false, duration: '6:00' },
      { id: 'les-ml-07', title: 'What is a Rootkit?', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/03_1-3-malware-threats/07_what-is-rootkit.mp4', free: false, duration: '6:30' },
      { id: 'les-ml-10', title: 'Trojan and Trojan Horse', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/03_1-3-malware-threats/10_trojan-and-trojan-horse.mp4', free: false, duration: '7:00' },
      { id: 'les-ids-01', title: 'Firewall, Evading IDS & Honeypots', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/01_2-1-evading-ids-firewalls-and-honeypots/01_firewall-evading-ids-and-honeypots.mp4', free: true, duration: '8:00' },
      { id: 'les-ids-02', title: 'Types of Firewalls', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/01_2-1-evading-ids-firewalls-and-honeypots/02_types-of-firewalls.mp4', free: false, duration: '6:30' },
      { id: 'les-ids-07', title: 'Intrusion Detection Tool: Snort', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/01_2-1-evading-ids-firewalls-and-honeypots/07_intrusion-detection-tool-snort.mp4', free: false, duration: '8:00' },
      { id: 'les-ids-08', title: 'What is a Honeypot?', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/01_2-1-evading-ids-firewalls-and-honeypots/08_what-is-honeypot.mp4', free: false, duration: '6:00' },
      { id: 'les-iot-01', title: 'IoT Hacking Introduction', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/02_2-2-iot-hacking/01_iot-hacking.mp4', free: true, duration: '7:00' },
      { id: 'les-iot-04', title: 'IoT Technologies and Protocols', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/02_2-2-iot-hacking/04_iot-technologies-and-protocols.mp4', free: false, duration: '8:05' },
      { id: 'les-iot-08', title: 'IoT Hacking Methodology', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/02_2-2-iot-hacking/08_iot-hacking-methodology.mp4', free: false, duration: '11:25' },
    ],
  },
  'course-burp-suite': {
    title: 'Burp Suite Live Practical',
    courseSlug: 'hands-on-hacking/burp-suite',
    lessons: [
      { id: 'les-burp-01', title: 'Install Burp Suite Pro for Free', type: 'video', asset: 'hands-on-hacking/burp-suite/1 -Install Burp Suite Pro for free.mp4', free: true, duration: '~103MB' },
      { id: 'les-burp-02', title: 'Configure Burp Suite with Firefox Proxy', type: 'video', asset: 'hands-on-hacking/burp-suite/2 -Configure Burp Suite with Firefox Proxy.mp4', free: false },
      { id: 'les-burp-03', title: 'OTP Bypass by Response Manipulation', type: 'video', asset: 'hands-on-hacking/burp-suite/3 -OTP Bypass by Response Manipulation.mp4', free: false },
      { id: 'les-burp-04', title: 'OTP Bypass by Bruteforcing', type: 'video', asset: 'hands-on-hacking/burp-suite/4 -OTP Bypass by Bruteforcing.mp4', free: false },
      { id: 'les-burp-05', title: 'Account Takeover by OTP Bypass', type: 'video', asset: 'hands-on-hacking/burp-suite/5 -Account Takeover by OTP Bypass.mp4', free: false },
      { id: 'les-burp-07', title: 'Account Takeover by IDOR', type: 'video', asset: 'hands-on-hacking/burp-suite/7 -Account Takeover by IDOR.mp4', free: false },
      { id: 'les-burp-09', title: 'Live Price Tampering Bugs on Websites', type: 'video', asset: 'hands-on-hacking/burp-suite/9 -Live Price Tampering Bugs on Websites.mp4', free: false },
      { id: 'les-burp-10', title: 'Automated Form Flooding with Burp', type: 'video', asset: 'hands-on-hacking/burp-suite/10 -Automated Form Flooding with Burp.mp4', free: false },
    ],
  },
  'course-http-debugger': {
    title: 'HTTP Debugger Pro Basics',
    courseSlug: 'hands-on-hacking/http-debugger',
    lessons: [
      { id: 'les-http-01', title: 'Installing HTTP Debugger Pro', type: 'video', asset: 'hands-on-hacking/http-debugger/1 -Installing HTTP Debugger Pro.mp4', free: true },
      { id: 'les-http-02', title: 'Using HTTP Debugger Pro Like a Pro', type: 'video', asset: 'hands-on-hacking/http-debugger/2 -Using HTTP Debugger Pro like a Pro.mp4', free: false },
      { id: 'les-http-03', title: 'Price Tampering with TamperDev', type: 'video', asset: 'hands-on-hacking/bonus/1 -Price Tampering with TamperDev.mp4', free: false },
    ],
  },
};

