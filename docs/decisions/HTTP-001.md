# HTTP-001: Remote HTTP safety activation

**Status:** Implemented; real-target validation pending  
**Date:** 2026-09-13  
**Owner:** Dipuraj Thapa

## Implemented boundary

The optional `http` package adds `RemoteHttpTransport` behind the existing provider-neutral transport contract. Core/reference execution remains network-free and does not import the HTTP module.

The transport enforces HTTPS and port 443, exact host allowlisting, public-address DNS validation, relative predeclared operation paths, GET/POST method allowlisting, TLS verification, disabled environment proxies, disabled redirects, bounded timeouts, streamed response limits, JSON content/schema checks, opaque credential lookup, and typed sanitized failures.

## Claim boundary

Passing local tests proves the safety-policy implementation against controlled transports. It does not prove a customer target, DNS environment, certificate, authentication method, proxy, firewall, provider, or production network. `externally_verified` remains prohibited until an approved target and its authentication are exercised successfully.

## Activation inputs still required per target

- Exact HTTPS hostname allowlist.
- Operation-to-path mapping and permitted methods.
- Credential provider and secret owner, when authentication is required.
- Target authorization and data classification.
- Target-specific rate limits and any lower response/timeout limits.

## Validation evidence

Tests cover non-HTTPS URLs, URL credentials/fragments, unlisted hosts, private/loopback addresses, unsafe paths, unknown operations, unavailable credentials, redirects, upstream failures, response size, content type, JSON/schema validation, proxy isolation, successful mapping, and secret non-persistence.

