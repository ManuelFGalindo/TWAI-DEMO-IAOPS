/**
 * mcpService.ts
 *
 * Servicio para comunicarse con el servidor FastAPI MCP (main_api.py)
 * que orquesta los MCP Servers de AWS (diagrama + CloudFormation).
 *
 * Puerto por defecto: 8001 (configurable via VITE_MCP_API_URL)
 */

import axios from 'axios';

const MCP_BASE_URL =
  (import.meta.env.VITE_MCP_API_URL || 'http://localhost:8001') + '/api/ai/aws';

const mcpApi = axios.create({
  baseURL: MCP_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120_000, // 2 min: MCP servers pueden tardar en iniciar
});

// ─── Tipos ────────────────────────────────────────────────────────────────────

export type ChatMode = 'auto' | 'diagram' | 'infrastructure' | 'both';

export interface ChatRequest {
  message: string;
  session_id?: string;
  mode?: ChatMode;
}

export interface ChatResponse {
  mode: 'answer' | 'tool' | 'raw';
  text: string;
  diagram_path?: string | null;
  cfn_data?: Record<string, unknown> | null;
  session_id: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  mode?: ChatResponse['mode'];
  cfn_data?: Record<string, unknown> | null;
  timestamp: Date;
}

export interface McpStatus {
  status: string;
  servers: Array<{ name: string; alive: boolean }>;
  active_sessions: number;
}

// ─── API calls ────────────────────────────────────────────────────────────────

/**
 * Envía un mensaje al MCP y devuelve la respuesta del asistente.
 */
export async function sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
  const response = await mcpApi.post<ChatResponse>('/chat', req);
  return response.data;
}

/**
 * Limpia el historial de conversación en el servidor.
 */
export async function resetSession(session_id = 'default'): Promise<void> {
  await mcpApi.post('/reset', null, { params: { session_id } });
}

/**
 * Obtiene el estado de los servidores MCP.
 */
export async function getMcpStatus(): Promise<McpStatus> {
  const response = await mcpApi.get<McpStatus>('/status');
  return response.data;
}

/**
 * Obtiene el historial guardado en el servidor para una sesión.
 */
export async function getHistory(
  session_id = 'default'
): Promise<{ session_id: string; messages: Array<{ role: string; content: string }> }> {
  const response = await mcpApi.get('/history', { params: { session_id } });
  return response.data;
}
