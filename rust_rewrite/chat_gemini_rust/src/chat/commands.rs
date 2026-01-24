use crate::config::Settings;
use crate::chat::session::ChatSession;
use crate::codegemini::store::SimpleVectorStore;
use crate::codegemini::embeddings::EmbeddingGenerator;
use crate::mcp::client::McpClient;
use crate::client::imagen::ImagenClient; // Added
use colored::Colorize;
use std::collections::HashMap;
use std::path::Path;
use rust_i18n::t;

pub struct AppState<'a> {
    pub settings: &'a mut Settings,
    pub session: &'a mut ChatSession,
    pub vector_store: &'a mut SimpleVectorStore,
    pub embedding_generator: &'a EmbeddingGenerator<'a>,
    pub mcp_clients: &'a mut HashMap<String, McpClient>,
    pub imagen_client: &'a ImagenClient<'a>, // Added
}

pub async fn handle_command(line: &str, state: &mut AppState<'_>) -> bool {
    let parts: Vec<&str> = line.split_whitespace().collect();
    if parts.is_empty() { return true; }
    
    let command = parts[0];
    let args = &parts[1..];

    match command {
        "/help" => {
            println!("{}", t!("command_help_desc").yellow());
            println!("  /clear       - {}", t!("command_clear_desc"));
            println!("  /model <id>  - {}", t!("command_model_desc"));
            println!("  /index <dir> - {}", t!("command_index_desc"));
            println!("  /search <q>  - {}", t!("command_search_desc"));
            println!("  /image <p>   - {}", t!("command_image_desc")); // Added
            println!("  /mcp ...     - {}", t!("command_mcp_desc"));
            println!("  /exit        - {}", t!("command_exit_desc"));
        }
        "/exit" => {
            return false;
        }
        "/clear" => {
            state.session.clear();
            println!("{}", t!("history_cleared").green());
        }
        "/model" => {
            if let Some(model) = args.first() {
                state.settings.model_name = model.to_string();
                println!("{}", t!("model_current", model = state.settings.model_name).cyan());
            } else {
                println!("{}", t!("model_current", model = state.settings.model_name).cyan());
            }
        }
        "/index" => {
            if let Some(path_str) = args.first() {
                let path = Path::new(path_str);
                if path.exists() {
                    println!("Indexing {}...", path.display());
                    // Simplified indexing logic
                    // In real impl, we walk dir, chunk files, embed, and store
                    // For now, just a stub or partial impl if `SimpleVectorStore` supports it
                    println!("Index feature is a stub in this version (use /search to test store).");
                } else {
                    eprintln!("Path not found: {}", path_str);
                }
            }
        }
        "/image" => { // Added implementation
            let prompt = args.join(" ");
            if prompt.is_empty() {
                println!("{}", "Usage: /image <prompt>".red());
            } else {
                println!("{}", t!("image_generating", prompt = prompt).blue());
                match state.imagen_client.generate_image(&prompt).await {
                    Ok(path) => {
                         println!("{} {}", "✓".green(), t!("image_saved", path = path.display()));
                    },
                    Err(e) => {
                         println!("{} {}", "✗".red(), format!("Image generation failed: {}", e));
                    }
                }
            }
        }
        "/mcp" => {
            if let Some(subcmd) = args.first() {
                match *subcmd {
                    "start" => {
                        if args.len() >= 3 {
                            let name = args[1];
                            let cmd = args[2];
                            let mcp_args: Vec<&str> = args[3..].to_vec();
                            match McpClient::new(cmd, &mcp_args) {
                                Ok(client) => {
                                    state.mcp_clients.insert(name.to_string(), client);
                                    println!("MCP Server '{}' started.", name.green());
                                },
                                Err(e) => eprintln!("Failed to start MCP: {}", e),
                            }
                        }
                    },
                    "list" => {
                        for name in state.mcp_clients.keys() {
                            println!("- {}", name);
                        }
                    },
                    _ => println!("Unknown MCP subcommand"),
                }
            }
        }
        _ => {
            println!("Unknown command: {}", command.red());
        }
    }

    true
}
