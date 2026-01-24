use crate::mcp::protocol::{ListToolsResult, Tool as McpTool};
use crate::client::models::{Tool, FunctionDeclaration, Schema};
use serde_json::Value;
use std::collections::HashMap;

pub fn map_mcp_tools_to_gemini(server_name: &str, mcp_tools: &ListToolsResult) -> Tool {
    let mut declarations = Vec::new();

    for tool in &mcp_tools.tools {
        // Namespacing: server_name__tool_name to avoid collisions
        let unique_name = format!("{}__{}", server_name, tool.name);
        
        declarations.push(FunctionDeclaration {
            name: unique_name,
            description: tool.description.clone().unwrap_or_default(),
            parameters: Some(map_json_schema(&tool.input_schema)),
        });
    }

    Tool {
        function_declarations: declarations,
    }
}

fn map_json_schema(input: &Value) -> Schema {
    // Simplified mapping from JSON Schema (Draft 7/2020-12) to Gemini Schema
    // Gemini supports a subset of OpenAPI 3.0 schema
    
    let schema_type = input.get("type").and_then(|v| v.as_str()).unwrap_or("OBJECT").to_string().to_uppercase();
    
    let mut properties = None;
    if let Some(props) = input.get("properties").and_then(|v| v.as_object()) {
        let mut prop_map = HashMap::new();
        for (k, v) in props {
            prop_map.insert(k.clone(), map_json_schema(v));
        }
        properties = Some(prop_map);
    }

    let mut required = None;
    if let Some(req) = input.get("required").and_then(|v| v.as_array()) {
        let req_vec: Vec<String> = req.iter().filter_map(|v| v.as_str().map(String::from)).collect();
        if !req_vec.is_empty() {
            required = Some(req_vec);
        }
    }

    Schema {
        schema_type,
        properties,
        required,
    }
}
