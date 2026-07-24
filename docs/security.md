# Security Notes

Authentication

- Set `GOV_API_KEY` to require `X-API-Key` on governance endpoints.
- Rotate keys through your secrets manager and avoid hardcoding keys.

Network controls

- Restrict ingress to trusted CI/CD and internal services.
- Use TLS termination at ingress/load balancer.

Operational controls

- Enable request logging and correlation via `x-request-id`.
- Enable in-service rate limiting via `GOV_RATE_LIMIT_*`.
- Place internet-facing deployments behind ingress rate limits and WAF.

Data handling

- Do not send sensitive run payloads to external LLM services unless approved.
- Keep `GOV_LLM_URL` empty in high-security environments.
