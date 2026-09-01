/**
 * OpenTelemetry Web SDK — auto-instrumentacao para o frontend.
 *
 * Captura:
 *   - Traces de fetch (API calls)
 *   - Document load performance
 *   - Propagacao de contexto (W3C TraceContext) para correlacionar com o backend
 *
 * Configuracao via variaveis do Vite (build time):
 *   VITE_OTEL_ENDPOINT — URL do collector OTLP HTTP (ex: https://dominio/otel)
 *
 * Se VITE_OTEL_ENDPOINT nao estiver definido, a instrumentacao fica inativa.
 */

import { resourceFromAttributes } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from '@opentelemetry/semantic-conventions';
import { WebTracerProvider, BatchSpanProcessor } from '@opentelemetry/sdk-trace-web';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { registerInstrumentations } from '@opentelemetry/instrumentation';

const OTEL_ENDPOINT = import.meta.env.VITE_OTEL_ENDPOINT as string | undefined;

export function initTelemetry(): void {
  if (!OTEL_ENDPOINT) {
    return; // OTel desabilitado — sem endpoint configurado
  }

  const resource = resourceFromAttributes({
    [ATTR_SERVICE_NAME]: 'otrs-mcp-frontend',
    [ATTR_SERVICE_VERSION]: '0.2.0',
    'deployment.environment': import.meta.env.MODE || 'production',
  });

  const exporter = new OTLPTraceExporter({
    url: `${OTEL_ENDPOINT}/v1/traces`,
  });

  const provider = new WebTracerProvider({
    resource,
    spanProcessors: [new BatchSpanProcessor(exporter)],
  });

  provider.register({
    contextManager: new ZoneContextManager(),
  });

  registerInstrumentations({
    instrumentations: [
      new FetchInstrumentation({
        // Instrumentar apenas chamadas para a propria API
        ignoreUrls: [/^https?:\/\/(?!.*\/api\/).*/],
        propagateTraceHeaderCorsUrls: [/\/api\//],
        clearTimingResources: true,
      }),
      new DocumentLoadInstrumentation(),
    ],
  });
}
