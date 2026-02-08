use crate::config::Settings;
use crate::chat::session::ChatSession;
use crate::codegemini::store::{SimpleVectorStore, VectorDocument};
use crate::codegemini::embeddings::EmbeddingGenerator;
use crate::codegemini::walker::FileWalker;
use crate::codegemini::chunker::Chunker;
use crate::mcp::client::McpClient;
use crate::client::imagen::ImagenClient;
use crate::chat::doctor::Doctor;
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
    pub imagen_client: &'a ImagenClient<'a>,
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
            println!("  /image <p>   - {}", t!("command_image_desc"));
            println!("  /doctor      - System diagnostics");
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
        "/doctor" => {
            let _ = Doctor::check(state.settings).await;
        }
        "/index" => {
            if let Some(path_str) = args.first() {
                let path = Path::new(path_str);
                if path.exists() {
                    println!("Indexing {}...", path.display());
                    match FileWalker::walk(path) {
                        Ok(files) => {
                            println!("Found {} files. Processing...", files.len());
                            state.vector_store.clear();
                            
                            for (fpath, content) in files {
                                let chunks = Chunker::chunk(&content, 100);
                                for chunk in chunks {
                                    match state.embedding_generator.generate_embedding(&chunk).await {
                                        Ok(embedding) => {
                                            state.vector_store.add(VectorDocument {
                                                file_path: fpath.clone(),
                                                content: chunk,
                                                embedding,
                                            });
                                        },
                                        Err(e) => eprintln!("Failed to embed {}: {}", fpath, e),
                                    }
                                }
                                print!("."); 
                                use std::io::Write;
                                let _ = std::io::stdout().flush();
                            }
                            println!("\nIndexing complete. {} chunks stored.", state.vector_store.count());
                            
                            // Save to disk
                            if let Err(e) = state.vector_store.save("codegemini_index.json") {
                                eprintln!("Failed to save index: {}", e);
                            } else {
                                println!("Index saved to codegemini_index.json");
                            }
                        },
                        Err(e) => eprintln!("Walk failed: {}", e),
                    }
                } else {
                    eprintln!("Path not found: {}", path_str);
                }
            }
        }
        "/search" => {
            let query = args.join(" ");
            if query.is_empty() {
                println!("Usage: /search <query>");
            } else {
                println!("Searching for '{}'...", query);
                match state.embedding_generator.generate_embedding(&query).await {
                    Ok(vec) => {
                        let results = state.vector_store.search(&vec, 3);
                        for (doc, score) in results {
                            println!("--- Score: {:.4} ---", score);
                            println!("File: {}", doc.file_path.cyan());
                            println!("{}\n", doc.content.trim().chars().take(200).collect::<String>());
                        }
                    },
                    Err(e) => eprintln!("Embedding failed: {}", e),
                }
            }
        }
        "/image" => {
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
                        for (name, _) in state.mcp_clients.iter() {
                            println!("- {}", name);
                        }
                    },
                    "resources" => {
                        if let Some(name) = args.get(1) {
                            if let Some(client) = state.mcp_clients.get_mut(*name) {
                                match client.list_resources() {
                                    Ok(res) => {
                                        for r in res.resources {
                                            println!("- {} ({})", r.name, r.uri);
                                        }
                                    },
                                    Err(e) => eprintln!("Error: {}", e),
                                }
                            } else {
                                eprintln!("Server not found: {}", name);
                            }
                        } else {
                            println!("Usage: /mcp resources <server_name>");
                        }
                    },
                    "prompts" => {
                        if let Some(name) = args.get(1) {
                            if let Some(client) = state.mcp_clients.get_mut(*name) {
                                match client.list_prompts() {
                                    Ok(res) => {
                                        for p in res.prompts {
                                            println!("- {} : {}", p.name, p.description.unwrap_or_default());
                                        }
                                    },
                                    Err(e) => eprintln!("Error: {}", e),
                                }
                            } else {
                                eprintln!("Server not found: {}", name);
                            }
                        } else {
                            println!("Usage: /mcp prompts <server_name>");
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
