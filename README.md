# Cloudflare SMTP demo

This local Python service sends a fixed welcome email from `welcome@scherger.cloud` through Cloudflare Email Sending. It uses the Python standard library and uv.

## Run

Put `TOKEN=<your Cloudflare API token>` in `.env.secret` in this directory. The token needs **Email Sending: Edit** for the account that owns the sending domain. SMTP uses the token as the password for `api_token` at `smtp.mx.cloudflare.net:465` over implicit TLS. [Cloudflare SMTP documentation](https://developers.cloudflare.com/email-service/api/send-emails/smtp/)

```sh
uv run --env-file .env.secret app.py
```

## Send

Open [the web form](http://127.0.0.1:8000/), enter an email address you control, and select **Send test email**.

### Send from the terminal

Replace `recipient@example.com` with an inbox you control, then run this in another terminal.

```sh
curl -sS http://127.0.0.1:8000/send \
  -H 'Content-Type: application/json' \
  --data '{"to":"recipient@example.com"}'
```

HTTP `200` with `"status": "accepted"` means Cloudflare accepted the message for delivery. Check the recipient inbox to confirm delivery. HTTP `502` indicates an SMTP failure and includes the SMTP reply code when available.
