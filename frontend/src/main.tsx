import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./routes/App";
import "./index.css";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 2 } } });
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}><BrowserRouter><App /></BrowserRouter></QueryClientProvider>,
);
