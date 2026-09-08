import { createHashRouter, RouterProvider } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { RuntimeStatusProvider } from "./contexts/RuntimeStatusContext";
import { DashboardPage } from "./pages/DashboardPage";
import { DiagnosticsPage } from "./pages/DiagnosticsPage";
import { HistoryPage } from "./pages/HistoryPage";
import { ModelPage } from "./pages/ModelPage";
import { NetworksPage } from "./pages/NetworksPage";
import { ScanPage } from "./pages/ScanPage";
import { SettingsPage } from "./pages/SettingsPage";

const router=createHashRouter([{ element:<AppShell/>, children:[
  { path:"/", element:<DashboardPage/> },
  { path:"/scan", element:<ScanPage/> },
  { path:"/networks", element:<NetworksPage/> },
  { path:"/history", element:<HistoryPage/> },
  { path:"/model", element:<ModelPage/> },
  { path:"/diagnostics", element:<DiagnosticsPage/> },
  { path:"/settings", element:<SettingsPage/> }
]}]);

export default function App(){return <RuntimeStatusProvider><RouterProvider router={router}/></RuntimeStatusProvider>;}
