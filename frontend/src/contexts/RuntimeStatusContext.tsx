import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import type { HealthResponse } from "../types/api";
import type { AutoScanSchedulerStatus } from "../types/desktop";
import type { RuntimeStatusSnapshot } from "../types/runtime";

const DEFAULT_REFRESH_SECONDS=10;
const DISCONNECTED_RETRY_MS=2000;
const DISCONNECTED_AFTER_FAILURES=3;
interface RuntimeStatusContextValue extends RuntimeStatusSnapshot { refresh:()=>Promise<boolean>; }
const RuntimeStatusContext=createContext<RuntimeStatusContextValue|null>(null);

function boundedRefreshSeconds(value:number|null|undefined):number {
  if (!Number.isFinite(value)) return DEFAULT_REFRESH_SECONDS;
  return Math.min(300,Math.max(2,Number(value)));
}

export function RuntimeStatusProvider({children}:{children:ReactNode}) {
  const desktop=Boolean(window.evilTwinDesktop?.desktop);
  const [snapshot,setSnapshot]=useState<RuntimeStatusSnapshot>({connection:"connecting",health:null,scheduler:null,refreshIntervalSeconds:DEFAULT_REFRESH_SECONDS,consecutiveFailures:0,lastCheckedAt:null,lastConnectedAt:null,recoveredAt:null,checking:false,desktop});
  const hadConnectionRef=useRef(false); const failuresRef=useRef(0); const refreshSecondsRef=useRef(DEFAULT_REFRESH_SECONDS); const requestRef=useRef<Promise<boolean>|null>(null); const mountedRef=useRef(true);

  const performRefresh=useCallback(async():Promise<boolean>=>{
    if (requestRef.current) return requestRef.current;
    const request=(async()=>{
      if (mountedRef.current) setSnapshot(previous=>({...previous,checking:true}));
      const checkedAt=new Date().toISOString();
      try {
        const health:HealthResponse=await api.health();
        const [settingsResult,schedulerResult]=await Promise.allSettled([
          api.settings(),
          window.evilTwinDesktop?.getAutoScanSchedulerStatus ? window.evilTwinDesktop.getAutoScanSchedulerStatus() : Promise.resolve(null)
        ]);
        const refreshSeconds=settingsResult.status==="fulfilled" ? boundedRefreshSeconds(settingsResult.value.values.frontend_refresh_seconds) : refreshSecondsRef.current;
        refreshSecondsRef.current=refreshSeconds;
        const scheduler:AutoScanSchedulerStatus|null=schedulerResult.status==="fulfilled" ? schedulerResult.value : null;
        const wasDisconnected=hadConnectionRef.current && failuresRef.current>0;
        failuresRef.current=0; hadConnectionRef.current=true;
        if (mountedRef.current) setSnapshot(previous=>({...previous,connection:"connected",health,scheduler,refreshIntervalSeconds:refreshSeconds,consecutiveFailures:0,lastCheckedAt:checkedAt,lastConnectedAt:checkedAt,recoveredAt:wasDisconnected?checkedAt:previous.recoveredAt,checking:false}));
        return true;
      } catch {
        failuresRef.current += 1;
        const failureCount=failuresRef.current;
        const connection=failureCount>=DISCONNECTED_AFTER_FAILURES ? "disconnected" : hadConnectionRef.current ? "reconnecting" : "connecting";
        if (mountedRef.current) setSnapshot(previous=>({...previous,connection,consecutiveFailures:failureCount,lastCheckedAt:checkedAt,checking:false}));
        return false;
      }
    })();
    requestRef.current=request;
    try { return await request; } finally { requestRef.current=null; }
  },[]);

  useEffect(()=>{
    mountedRef.current=true; let cancelled=false; let timer:number|null=null;
    async function cycle(){
      const connected=await performRefresh();
      if(cancelled) return;
      const delay=connected ? refreshSecondsRef.current*1000 : DISCONNECTED_RETRY_MS;
      timer=window.setTimeout(()=>{void cycle();},delay);
    }
    void cycle();
    return ()=>{cancelled=true; mountedRef.current=false; if(timer!==null) window.clearTimeout(timer);};
  },[performRefresh]);

  useEffect(()=>{
    const unsubscribe=window.evilTwinDesktop?.onAutoScanCompleted?.(()=>{void performRefresh();});
    const onFocus=()=>{void performRefresh();};
    window.addEventListener("focus",onFocus);
    return ()=>{unsubscribe?.();window.removeEventListener("focus",onFocus);};
  },[performRefresh]);

  return <RuntimeStatusContext.Provider value={{...snapshot,refresh:performRefresh}}>{children}</RuntimeStatusContext.Provider>;
}

export function useRuntimeStatus():RuntimeStatusContextValue {
  const value=useContext(RuntimeStatusContext);
  if(!value) throw new Error("useRuntimeStatus must be used inside RuntimeStatusProvider.");
  return value;
}
