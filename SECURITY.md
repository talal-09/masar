# Security Policy

## Supported version

Security fixes are applied to the latest commit on `main`.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's
private vulnerability reporting feature on this repository instead. Include:

- the affected component and route;
- steps to reproduce the issue;
- the expected and actual behavior;
- the potential impact; and
- any suggested mitigation.

Do not include production credentials, personal data, or customer records in
the report. This portfolio project uses synthetic local data and is not offered
as a hosted production service.

## Security baseline

Masar uses Django's CSRF and password protections, role-based authorization,
customer ownership checks, environment-based secrets, secure production
cookies, HTTPS redirection, HSTS, and database transactions for multi-step
inventory and financial operations.

