---
name: opentelemetry
license: Apache-2.0
description: Instrument any app with OpenTelemetry and ship metrics / logs / traces to Grafana Cloud or self-hosted Mimir / Loki / Tempo / Pyroscope. Covers SDK auto-instrumentation for Python and Node.js, env-var config, Alloy / OTel-Collector pipelines, and head + tail sampling. Use when instrumenting a service, pointing OTLP at Grafana, or debugging telemetry issues.
---

# OpenTelemetry with Grafana

Vendor-neutral instrumentation pipeline. Apps speak OTLP to Grafana stack (Mimir / Loki / Tempo / Pyroscope).

See full guide at: https://github.com/grafana/skills/tree/main/skills/grafana-core/opentelemetry

## References

- [Instrumentation Guide](references/instrumentation.md) - Language-specific SDK instrumentation
- [Collector Config](references/collector-config.md) - Alloy and OTel Collector configuration examples
