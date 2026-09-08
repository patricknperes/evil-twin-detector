import { CheckCircle2, LoaderCircle, RefreshCw, ServerCrash } from "lucide-react";
import { useEffect, useState } from "react";
import { useRuntimeStatus } from "../contexts/RuntimeStatusContext";
import { formatDateTime } from "../lib/format";

export function RuntimeConnectionBanner(){
 const runtime=useRuntimeStatus(); const [showRecovery,setShowRecovery]=useState(false);
 useEffect(()=>{if(!runtime.recoveredAt)return;setShowRecovery(true);const timer=window.setTimeout(()=>setShowRecovery(false),4500);return()=>window.clearTimeout(timer);},[runtime.recoveredAt]);
 if(runtime.connection==="connected") return showRecovery ? <div className="mb-5 flex items-center gap-3 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800"><CheckCircle2 size={17} className="shrink-0"/><div><p className="font-medium">Conexão com o backend restaurada</p><p className="mt-0.5 text-xs text-sky-700">O estado global voltou a ser atualizado pelo serviço local.</p></div></div> : null;
 if(runtime.connection==="connecting") return <div className="mb-5 flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600"><LoaderCircle size={17} className="shrink-0 animate-spin"/>Verificando o backend local…</div>;
 return <div className="mb-5 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3"><div className="flex items-start gap-3"><ServerCrash size={18} className="mt-0.5 shrink-0 text-amber-700"/><div><p className="text-sm font-semibold text-amber-900">{runtime.connection==="disconnected"?"Backend local desconectado":"Reconectando ao backend local"}</p><p className="mt-1 text-xs leading-5 text-amber-700">O aplicativo mantém os dados já carregados, mas o estado de scanner, modelo e scheduler não deve ser interpretado como atual até a conexão voltar.{runtime.lastConnectedAt?` Última conexão: ${formatDateTime(runtime.lastConnectedAt)}.`:""}</p></div></div><button type="button" className="btn-secondary" disabled={runtime.checking} onClick={()=>void runtime.refresh()}><RefreshCw size={15} className={runtime.checking?"animate-spin":""}/>Tentar agora</button></div>;
}
