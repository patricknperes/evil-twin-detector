import type { ScannerStatus } from "../types/api";
import type { AutoScanSchedulerStatus } from "../types/desktop";
import type { BackendConnectionState } from "../types/runtime";

export type RuntimeTone = "positive" | "neutral" | "warning" | "danger";
export interface RuntimeLabel { label:string; detail:string; tone:RuntimeTone; }

export function backendLabel(connection: BackendConnectionState): RuntimeLabel {
  if (connection === "connected") return {label:"Conectado",detail:"FastAPI local respondendo",tone:"positive"};
  if (connection === "reconnecting") return {label:"Reconectando",detail:"Tentando recuperar o serviço local",tone:"warning"};
  if (connection === "disconnected") return {label:"Desconectado",detail:"Serviço local sem resposta",tone:"danger"};
  return {label:"Conectando",detail:"Verificando o serviço local",tone:"neutral"};
}

export function scannerLabel(status: ScannerStatus | null, backendConnected:boolean): RuntimeLabel {
  if (!backendConnected) return {label:"Sem backend",detail:"Estado atual não pode ser verificado",tone:"neutral"};
  switch(status) {
    case "ready": return {label:"Pronto",detail:"Última varredura Native Wi-Fi foi concluída",tone:"positive"};
    case "not_initialized": return {label:"Aguardando scan",detail:"Native Wi-Fi ainda não foi exercitado nesta execução",tone:"neutral"};
    case "location_access_denied": return {label:"Permissão necessária",detail:"O Windows bloqueou o acesso exigido pelo Native Wi-Fi",tone:"warning"};
    case "unsupported_platform": return {label:"Indisponível",detail:"Scanner desktop disponível apenas no Windows",tone:"neutral"};
    case "error": return {label:"Erro",detail:"A última tentativa do Native Wi-Fi falhou",tone:"danger"};
    default: return {label:"Desconhecido",detail:"Sem informação do scanner",tone:"neutral"};
  }
}

export function modelLabel(status:"ready"|"not_ready"|null, backendConnected:boolean): RuntimeLabel {
  if (!backendConnected) return {label:"Sem backend",detail:"Estado atual não pode ser verificado",tone:"neutral"};
  return status === "ready" ? {label:"Pronto",detail:"Bundle científico congelado disponível",tone:"positive"} : {label:"Não pronto",detail:"Artefatos científicos reais ainda não estão disponíveis",tone:"neutral"};
}

export function schedulerLabel(status:AutoScanSchedulerStatus|null, backendConnected:boolean, desktop:boolean): RuntimeLabel {
  if (!desktop) return {label:"Somente Electron",detail:"Scheduler não roda no navegador",tone:"neutral"};
  if (!backendConnected) return {label:"Aguardando backend",detail:"O scheduler depende do serviço local",tone:"warning"};
  switch(status?.status) {
    case "waiting": return {label:"Ativo",detail:status.nextRunAt?"Próxima varredura já agendada":"Aguardando próximo ciclo",tone:"positive"};
    case "scanning": return {label:"Escaneando",detail:"Varredura automática em andamento",tone:"positive"};
    case "disabled": return {label:"Desativado",detail:"Preferência de scan automático está desligada",tone:"neutral"};
    case "stopped": return {label:"Parado",detail:"Scheduler ainda não foi iniciado",tone:"neutral"};
    case "unsupported_platform": return {label:"Indisponível",detail:"Scheduler Native Wi-Fi disponível apenas no Windows",tone:"neutral"};
    case "settings_error": return {label:"Erro de configuração",detail:"Não foi possível ler as preferências do scheduler",tone:"danger"};
    case "scan_error": return {label:"Erro no scan",detail:"A última varredura automática falhou",tone:"danger"};
    default: return {label:"Consultando",detail:"Aguardando estado do processo principal",tone:"neutral"};
  }
}
