import {
  ApiError
} from "./api";

export type ScanErrorKind =
  | "backend_unavailable"
  | "location_access_denied"
  | "unsupported_platform"
  | "native_wifi_api_error"
  | "database_persist_failed"
  | "scan_in_progress"
  | "unknown";

export interface ScanErrorView {
  kind: ScanErrorKind;
  title: string;
  message: string;
  settingsUri?: string;
  functionName?: string;
  win32Code?: number;
}

interface ErrorDetail {
  code?: string;
  message?: string;
  settings_uri?: string;
  function?: string;
  win32_code?: number;
  error?: string;
}

function detailFrom(
  payload: unknown
): ErrorDetail {
  if (
    typeof payload !== "object"
    || payload === null
  ) {
    return {};
  }

  const maybeDetail = (
    payload as {
      detail?: unknown;
    }
  ).detail;

  if (
    typeof maybeDetail !== "object"
    || maybeDetail === null
  ) {
    return {};
  }

  return maybeDetail as ErrorDetail;
}

export function classifyScanError(
  error: unknown
): ScanErrorView {
  if (error instanceof ApiError) {
    const detail = detailFrom(
      error.payload
    );

    switch (detail.code) {
      case "location_access_denied":
        return {
          kind: "location_access_denied",
          title: "Permissão de localização necessária",
          message:
            detail.message
            ?? "O Windows bloqueou o acesso às informações detalhadas das redes Wi-Fi.",
          settingsUri:
            detail.settings_uri
            ?? "ms-settings:privacy-location"
        };

      case "unsupported_platform":
        return {
          kind: "unsupported_platform",
          title: "Scanner disponível apenas no Windows",
          message:
            detail.message
            ?? "A integração Native Wi-Fi desta versão desktop requer Windows 10 ou 11."
        };

      case "native_wifi_api_error":
        return {
          kind: "native_wifi_api_error",
          title: "Falha na API Native Wi-Fi",
          message:
            detail.message
            ?? "O Windows retornou um erro durante a varredura Wi-Fi.",
          functionName: detail.function,
          win32Code: detail.win32_code
        };

      case "database_persist_failed":
        return {
          kind: "database_persist_failed",
          title: "Falha ao salvar a varredura",
          message:
            detail.message
            ?? "A varredura ocorreu, mas o histórico não pôde ser persistido localmente."
        };

      case "scan_in_progress":
        return {
          kind: "scan_in_progress",
          title: "Já existe uma varredura em andamento",
          message:
            "Aguarde o scan atual terminar antes de iniciar outra varredura."
        };

      default:
        return {
          kind: "unknown",
          title: `Falha ao executar a varredura (${error.status})`,
          message:
            detail.message
            ?? "O backend retornou um erro inesperado."
        };
    }
  }

  if (error instanceof TypeError) {
    return {
      kind: "backend_unavailable",
      title: "Backend local indisponível",
      message:
        "Não foi possível conectar ao serviço local em 127.0.0.1:8765. Verifique se o backend está em execução."
    };
  }

  return {
    kind: "unknown",
    title: "Não foi possível executar a varredura",
    message:
      error instanceof Error
        ? error.message
        : "Ocorreu um erro inesperado durante o scan."
  };
}
