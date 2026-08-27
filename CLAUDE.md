# Azeon Systems - Multi-Tenant SaaS Project Context

## Project Overview
Azeon Systems is an all-in-one business suite for SMEs offering CRM, Finance, Payroll, HR, and Inventory management with real-time CEO dashboards.

## Brand Identity Tokens
- Primary Color (Orange / High Energy): `#F57C00`
- Secondary Color (Navy Blue / Professional): `#0D47A1`
- Supporting Colors: White `#FFFFFF`, Gray `#9E9E9E`
- Headings Font: Montserrat Bold
- Body Text Font: Open Sans Regular
- Subdomain Pattern: `https://{tenant_slug}.azeonsystems.com.ng`

## System Architecture
- Local Machine: Windows 11 using WSL 2 (Ubuntu 22.04)
- Code Assistant: Claude Code CLI running inside WSL 2
- Production VPS: Ubuntu 22.04 LTS with Frappe Bench / ERPNext
- Provisioner: Flask Python API handling incoming webhooks to generate `bench new-site`
- Frontend: Next.js 14 + Tailwind CSS (using Azeon Systems color tokens)

## Developer Guidelines
1. Never execute `bench` commands directly inside Windows PowerShell; always run inside Linux/WSL or SSH to VPS.
2. Sanitize user inputs into lowercase, alphanumeric slugs for site names.
3. Apply Navy Blue (`#0D47A1`) for app headers/navbars and Orange (`#F57C00`) for primary action buttons.
