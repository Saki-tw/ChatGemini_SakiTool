use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader, Write};
use anyhow::{Result, Context};
use crate::mcp::protocol::*;
use serde_json::Value;

pub struct McpClient {
    child: std::process::Child,
    next_id: u64,
}

impl McpClient {
    pub fn new(command: &str, args: &[&str]) -> Result<Self> {
        let child = Command::new(command)
            .args(args)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .context(format!("Failed to spawn MCP server: {}", command))?;

        let mut client = Self { child, next_id: 1 };
        client.initialize()?;
        Ok(client)
    }

    fn initialize(&mut self) -> Result<()> {
        let params = InitializeParams {
            protocol_version: "2024-11-05".to_string(),
            capabilities: serde_json::json!({}),
            client_info: ClientInfo {
                name: "ChatGemini_Rust".to_string(),
                version: "2.0.0".to_string(),
            },
        };

        self.send_request("initialize", Some(serde_json::to_value(params)?))?;
        let _resp = self.read_response()?; 
        
        // MCP requires a notification after init
        self.send_notification("notifications/initialized", None)?;
        
        Ok(())
    }

    pub fn list_tools(&mut self) -> Result<ListToolsResult> {
        self.send_request("tools/list", None)?;
        let resp = self.read_response()?;
        
        if let Some(res) = resp.result {
            let tools: ListToolsResult = serde_json::from_value(res)?;
            Ok(tools)
        } else {
            Err(anyhow::anyhow!("No result in list_tools response"))
        }
    }

    pub fn call_tool(&mut self, name: &str, args: Value) -> Result<Value> {
        let params = CallToolParams {
            name: name.to_string(),
            arguments: args,
        };
        
        self.send_request("tools/call", Some(serde_json::to_value(params)?))?;
        let resp = self.read_response()?;
        
        if let Some(err) = resp.error {
            Err(anyhow::anyhow!("MCP Error {}: {}", err.code, err.message))
        } else if let Some(res) = resp.result {
            Ok(res)
        } else {
            Ok(Value::Null)
        }
    }

    fn send_request(&mut self, method: &str, params: Option<Value>) -> Result<()> {
        let id = self.next_id;
        self.next_id += 1;
        
        let req = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            method: method.to_string(),
            params,
            id,
        };
        
        let stdin = self.child.stdin.as_mut().context("Failed to get stdin")?;
        let json = serde_json::to_string(&req)?;
        writeln!(stdin, "{}", json)?;
        stdin.flush()?;
        Ok(())
    }

    fn send_notification(&mut self, method: &str, params: Option<Value>) -> Result<()> {
        // Notification implies no ID (or null ID in some specs, but usually just omitted)
        // We'll treat it as request but ignore ID for now or implement struct
        // Basic JSON-RPC 2.0 notification: no id.
        #[derive(serde::Serialize)]
        struct Notification {
            jsonrpc: String,
            method: String,
            #[serde(skip_serializing_if = "Option::is_none")]
            params: Option<Value>,
        }
        
        let notif = Notification {
            jsonrpc: "2.0".to_string(),
            method: method.to_string(),
            params,
        };
        
        let stdin = self.child.stdin.as_mut().context("Failed to get stdin")?;
        let json = serde_json::to_string(&notif)?;
        writeln!(stdin, "{}", json)?;
        stdin.flush()?;
        Ok(())
    }

    fn read_response(&mut self) -> Result<JsonRpcResponse> {
        let stdout = self.child.stdout.as_mut().context("Failed to get stdout")?;
        let mut reader = BufReader::new(stdout);
        let mut line = String::new();
        reader.read_line(&mut line)?;
        
        if line.is_empty() {
            return Err(anyhow::anyhow!("MCP Server closed connection unexpectedly"));
        }

        // dbg!(&line); // Debug
        
        let response: JsonRpcResponse = serde_json::from_str(&line)
            .context(format!("Failed to parse MCP response: {}", line))?;
        Ok(response)
    }
}

impl Drop for McpClient {
    fn drop(&mut self) {
        let _ = self.child.kill();
    }
}