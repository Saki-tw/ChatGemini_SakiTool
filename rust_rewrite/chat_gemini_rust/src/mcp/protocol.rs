use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Serialize, Deserialize)]
#[serde(tag = "method", content = "params")]
pub enum JsonRpcMessage {
    #[serde(rename = "initialize")]
    Initialize { 
        protocol_version: String,
        capabilities: Value,
        client_info: ClientInfo,
    },
    #[serde(rename = "tools/list")]
    ListTools { }, // params is empty or optional
    #[serde(rename = "tools/call")]
    CallTool { 
        name: String,
        arguments: Value,
    },
}

// Custom serializer for JsonRpcMessage to match JSON-RPC 2.0 strictly
// "method": "...", "params": {...}, "id": ...
// The default enum serialization might be tricky. Let's use a struct wrapper or manual serialization.
// Actually, `serde(tag="method")` puts method inside. But JSON-RPC has ID at top level.
// Let's redefine for simplicity.

#[derive(Debug, Serialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub method: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub params: Option<Value>,
    pub id: u64,
}

#[derive(Debug, Deserialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: Option<u64>,
    pub result: Option<Value>,
    pub error: Option<JsonRpcError>,
}

#[derive(Debug, Deserialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
    pub data: Option<Value>,
}

// --- Params ---

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct InitializeParams {
    pub protocol_version: String,
    pub capabilities: Value,
    pub client_info: ClientInfo,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ClientInfo {
    pub name: String,
    pub version: String,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CallToolParams {
    pub name: String,
    pub arguments: Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ListToolsResult {
    pub tools: Vec<Tool>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Tool {
    pub name: String,
    pub description: Option<String>,
    pub input_schema: Value,
}

// Override Message enum to use Request struct in Client
impl JsonRpcMessage {
    // Redefinition as helper, but we use JsonRpcRequest for wire
}
