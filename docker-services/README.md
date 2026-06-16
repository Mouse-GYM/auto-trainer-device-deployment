# Docker Services

Production Docker Compose stack for an Auto Trainer device. Unlike the
development services, these images are **pulled from the registry, not built
locally**. The stack runs the device API service behind a TLS certificate that
is obtained and kept renewed automatically.

## Services

| Service        | Image                                                  | Purpose |
| -------------- | ------------------------------------------------------ | ------- |
| `api`          | `ghcr.io/mouse-gym/auto-trainer-device-service:latest` | The device service. Listens on host port `5150` (container `443`), connects to the message/command queues at `<device-id>.mousegym.org`, and reads its TLS certificate from the shared `./certs` volume. |
| `cert-manager` | `alpine:3.21`                                           | Obtains and renews the Let's Encrypt certificate used by `api`. |

The `api` service `depends_on` `cert-manager` with `condition: service_healthy`,
so it will not start serving until a valid certificate has been written to the
shared volume.

## Usage

Create a `.env` file from `.env-template` and fill in the required values (see
below), then use the helper scripts:

```bash
./up.sh      # start the stack (docker compose up -d)
./logs.sh    # follow logs
./stop.sh    # stop containers (docker compose stop)
./down.sh    # stop and remove containers (docker compose down)
```

Each script sources `.env` (if present) and uses `AUTOTRAINER_COMPOSE_NAME` as
the Compose project name, defaulting to `autotrainer` when unset.

## How the cert manager works

`cert-manager` runs [`cert-manager/entrypoint.sh`](cert-manager/entrypoint.sh)
inside a plain Alpine container. On startup it:

1. **Validates the environment** — requires `CERT_DOMAIN`,
   `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY`; exits with an error if any
   are missing.
2. **Installs [`acme.sh`](https://github.com/acmesh-official/acme.sh)** the
   first time it runs. The install lives in the persistent `acme-data` volume
   (mounted at `/acme`), so subsequent starts skip this step.
3. **Issues a certificate** for `CERT_DOMAIN` from Let's Encrypt using the
   **DNS-01 challenge over AWS Route 53** (`acme.sh --dns dns_aws`). This
   requires a Route 53 hosted zone with an A record for `CERT_DOMAIN`, and AWS
   credentials permitted to change records in that zone. An EC-256 key is used.
   If a certificate already exists in `/acme` for the domain, issuance is
   skipped.
4. **Installs the certificate** into the shared `./certs` volume as
   `private_ca_cert.crt` (fullchain) and `private_ca_cert.key` (key). The `api`
   container mounts this volume read-only at `/certs`.
5. **Signals readiness** by touching `/tmp/certs-ready`. The Compose
   healthcheck polls for this file, which is what gates the `api` service.
6. **Renews automatically** — the script then loops forever, running
   `acme.sh --cron` once a day. `acme.sh` renews the certificate when it is
   within ~30 days of expiry (i.e. around the 60-day mark).

Because DNS-01 validation is used, no inbound HTTP/port-80 access is required to
issue or renew the certificate.

## Environment variables (`.env-template`)

### Required

| Variable                | Description |
| ----------------------- | ----------- |
| `AUTOTRAINER_DEVICE_ID` | Device identifier (e.g. `agx001`). Used for notifications and to build the message/command queue hostnames (`<device-id>.mousegym.org`). |
| `CERT_DOMAIN`           | Domain name for the dashboard TLS certificate, issued via Let's Encrypt. A Route 53 hosted zone and A record must exist for this domain (e.g. `dashboard.yourdomain.com`). |
| `AWS_ACCESS_KEY_ID`     | AWS access key used by the cert manager for Route 53 DNS-01 validation. Scope the IAM user to `ChangeResourceRecordSets` on the hosted zone. |
| `AWS_SECRET_ACCESS_KEY` | Secret for the AWS access key above. |

### Optional

| Variable                    | Default       | Description |
| --------------------------- | ------------- | ----------- |
| `AUTOTRAINER_COMPOSE_NAME`  | `autotrainer` | Docker Compose project name (prefix). |
| `AUTOTRAINER_LOG_VOLUME`    | `/var/log/autotrainer` | Host path mounted into the `api` container for log output. |
| `AUTOTRAINER_SNS_TOPIC_ARN` | _(blank)_     | AWS SNS topic ARN for emergency stop/resume notifications. Leave blank if not using emergency notifications. |
| `AUTOTRAINER_SNS_KEY_ID`    | _(blank)_     | AWS SNS access key ID for emergency notifications. Leave blank if unused. |
| `AUTOTRAINER_SNS_KEY`       | _(blank)_     | AWS SNS secret key for emergency notifications. Leave blank if unused. |

> **Note:** The SNS variables work together — to enable emergency
> stop/resume notifications, set all three (`AUTOTRAINER_SNS_TOPIC_ARN`,
> `AUTOTRAINER_SNS_KEY_ID`, `AUTOTRAINER_SNS_KEY`). Leave all blank to disable.
