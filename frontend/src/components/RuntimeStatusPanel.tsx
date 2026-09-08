import { Activity, Cpu, RadioTower, RefreshCw, Server } from "lucide-react";
import { useRuntimeStatus } from "../contexts/RuntimeStatusContext";
import { backendLabel, modelLabel, scannerLabel, schedulerLabel, type RuntimeLabel, type RuntimeTone } from "../lib/runtimeUi";

const toneClasses:Record<RuntimeTone,string>={positive:"bg-emerald-500",neutral:"bg-slate-400",warning:"bg-amber-500",danger:"bg-rose-500"};

export function RuntimeStatusPanel(){
  const runtime=useRuntimeStatus(); const connected=runtime.connection==="connected";
  const items=[
    {icon:Server,label:"Backend",value:backendLabel(runtime.connection)},
    {icon:RadioTower,label:"Scanner",value:scannerLabel(runtime.health?.scanner_status??null,connected)},
    {icon:Cpu,label:"Modelo",value:modelLabel(runtime.health?.model_status??null,connected)},
    {icon:Activity,label:"Scheduler",value:schedulerLabel(runtime.scheduler,connected,runtime.desktop)}
  ];
  return <section className="rounded-xl border border-slate-200 bg-slate-50 p-3">
    <div className="flex items-center justify-between gap-2"><div><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Estado do aplicativo</p><p className="mt-1 text-[11px] text-slate-400">{runtime.lastCheckedAt?"Monitoramento ativo":"Inicializando"}</p></div>
    <button type="button" className="grid size-8 place-items-center rounded-lg text-slate-400 transition hover:bg-white hover:text-slate-700 disabled:opacity-50" disabled={runtime.checking} title="Atualizar estado agora" onClick={()=>void runtime.refresh()}><RefreshCw size={14} className={runtime.checking?"animate-spin":""}/></button></div>
    <div className="mt-3 space-y-1">{items.map(item=><RuntimeRow key={item.label} {...item}/>)}</div>
  </section>;
}

function RuntimeRow({icon:Icon,label,value}:{icon:typeof Server;label:string;value:RuntimeLabel}){
 return <div className="flex items-center gap-2 rounded-lg px-2 py-2" title={value.detail}><Icon size={14} className="shrink-0 text-slate-400"/><span className="min-w-0 flex-1 truncate text-[11px] text-slate-500">{label}</span><span className="flex min-w-0 items-center gap-1.5"><span className={["size-1.5 shrink-0 rounded-full",toneClasses[value.tone]].join(" ")}/><span className="max-w-[104px] truncate text-[11px] font-medium text-slate-700">{value.label}</span></span></div>;
}
