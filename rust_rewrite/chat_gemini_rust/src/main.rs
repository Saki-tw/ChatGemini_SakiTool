use std::io::{self, Write};
use std::fs;
use colored::Colorize;
use futures_util::StreamExt;
use base64::prelude::*;
use base64::Engine;
use mime_guess::from_path;
use std::collections::HashMap;
use rust_i18n::i18n;
use rust_i18n::t;
use std::sync::Arc;

mod config;
mod client;
mod chat;
mod ui;
mod codegemini; 
mod mcp;

use config::Settings;
use client::rest::GeminiClient;
use client::auth::GoogleAuth;
use client::models::{GenerateContentRequest, Content, Part, GenerationConfig, ThinkingConfig, CachedContent, FunctionCall, FunctionResponse};
use client::cache::CacheManager;
use client::files::FileManager;
use client::imagen::ImagenClient;
use chat::session::ChatSession;
use chat::input_parser::parse_input;
use chat::pricing::PricingCalculator;
use chat::commands::{handle_command, AppState};
use codegemini::store::SimpleVectorStore;
use codegemini::embeddings::EmbeddingGenerator;
use ui::prompt::Repl;
use ui::theme::create_skin;
use ui::wizard;
use mcp::client::McpClient;
use mcp::mapper::map_mcp_tools_to_gemini;

// Define locales
i18n!("locales", fallback = "zh-TW");

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 1. 載入設定
    let mut settings = Settings::new().unwrap_or_else(|e| {
        eprintln!("Config Error: {}", e);
        std::process::exit(1);
    });

    // 設定語言
    rust_i18n::set_locale(&settings.language);

    // Initialize Auth
    let auth = match GoogleAuth::new(&settings).await {
        Ok(a) => Arc::new(a),
        Err(_) => {
            println!("{}", "未偵測到有效憑證，進入引導模式...".yellow());
            match wizard::run_onboarding() {
                Ok(new_settings) => {
                    settings = new_settings;
                    match GoogleAuth::new(&settings).await {
                        Ok(a) => Arc::new(a),
                        Err(e) => {
                            eprintln!("{} {}", "設定後仍無法驗證:".red(), e);
                            std::process::exit(1);
                        }
                    }
                },
                Err(e) => {
                    eprintln!("{} {}", "設定取消:".red(), e);
                    std::process::exit(1);
                }
            }
        }
    };

    // 2. 初始化核心組件
    let client = GeminiClient::new(auth).await; 
    let mut session = ChatSession::new();
    let mut repl = Repl::new();
    let skin = create_skin(); 
    let pricing = PricingCalculator::new(32.5);
    
    // 初始化 CodeGemini 組件
    let mut vector_store = SimpleVectorStore::new();
    // Load persisted index if exists
    if let Ok(store) = SimpleVectorStore::load("codegemini_index.json") {
        vector_store = store;
        println!("Loaded CodeGemini index ({} docs).", vector_store.count());
    }

    let embedding_generator = EmbeddingGenerator::new(&client);

    // 初始化 Context Caching
    let cache_manager = CacheManager::new(&client);
    let mut active_cache_name: Option<String> = None;

    // 初始化 File Manager & Imagen Client
    let file_manager = FileManager::new(&client);
    let imagen_client = ImagenClient::new(&client);

    // 初始化 MCP Client Store
    let mut mcp_clients: HashMap<String, McpClient> = HashMap::new();

    println!("{}", t!("welcome").purple().bold());
    println!("{}", t!("model_current", model = settings.model_name).cyan());
    println!("{}\n", t!("exit_hint"));

    // 3. 主迴圈
    loop {
        let input_result = repl.read_line();
        match input_result {
            Ok(Some(line_buffer)) => {
                let line = line_buffer.trim();
                if line.is_empty() { continue; }

                // 處理斜線指令 (/command)
                if line.starts_with('/') {
                    let mut state = AppState {
                        settings: &mut settings,
                        session: &mut session,
                        vector_store: &mut vector_store,
                        embedding_generator: &embedding_generator,
                        mcp_clients: &mut mcp_clients,
                        imagen_client: &imagen_client,
                    };
                    
                    if !handle_command(line, &mut state).await {
                        break; 
                    }
                    continue; 
                }

                // --- 解析輸入 ---
                let parsed = parse_input(line);
                
                // 處理 Cache 指令
                if let Some(action) = parsed.cache_action {
                    if action == "now" {
                        println!("{}", t!("cache_building").blue());
                        // ... cache creation logic ...
                        let cache_payload = CachedContent {
                            name: None,
                            model: format!("models/{}", settings.model_name),
                            contents: session.to_gemini_history(),
                            system_instruction: settings.system_instruction.as_ref().map(|s| Content {
                                role: "user".to_string(),
                                parts: vec![Part::text(s.clone())],
                            }),
                            ttl: Some("3600s".to_string()),
                        };

                        match cache_manager.create(&cache_payload).await {
                            Ok(cached) => {
                                if let Some(name) = cached.name {
                                    println!("{} {}", "✓".green(), t!("cache_success", name = name));
                                    active_cache_name = Some(name);
                                }
                            },
                            Err(e) => {
                                println!("{} {}", "✗".red(), t!("cache_failed", error = e));
                            }
                        }
                    } else if action == "off" {
                        active_cache_name = None;
                        println!("{}", t!("cache_disabled").yellow());
                    }
                }

                // --- 構建訊息 ---
                let mut content_parts = Vec::new();
                
                if !parsed.text.is_empty() {
                    content_parts.push(Part::text(parsed.text.clone()));
                }

                for path in &parsed.files {
                    let mime = from_path(path).first_or_text_plain();
                    let mime_str = mime.to_string();

                    // 檔案大小判斷 (Inline vs File API)
                    let metadata = match fs::metadata(path) {
                        Ok(m) => m,
                        Err(e) => {
                            eprintln!("{}", format!("Error reading file metadata {:?}: {}", path, e).red());
                            continue;
                        }
                    };
                    
                    let size = metadata.len();
                    const MAX_INLINE_SIZE: u64 = 20 * 1024 * 1024; // 20MB

                    if size > MAX_INLINE_SIZE {
                         println!("{}", t!("file_uploading", path = path.display()).blue());
                         match file_manager.upload(path, &mime_str).await {
                            Ok(file_data) => {
                                println!("{} {}", "✓".green(), t!("file_uploaded", uri = file_data.uri));
                                content_parts.push(Part::file_data(mime_str.clone(), file_data.uri));
                            },
                            Err(e) => {
                                eprintln!("{} {}", "✗".red(), t!("file_upload_failed", error = e));
                            }
                        }
                    } else {
                        if mime_str.starts_with("image/") || mime_str.starts_with("audio/") || mime_str.starts_with("video/") || mime_str == "application/pdf" {
                             match fs::read(path) {
                                Ok(bytes) => {
                                    let b64_data = BASE64_STANDARD.encode(&bytes);
                                    content_parts.push(Part::inline_data(mime_str.clone(), b64_data));
                                    println!("{}", t!("media_added", path = path.display(), mime = mime_str).green());
                                }
                                Err(e) => {
                                    eprintln!("{}", format!("Error reading media file {:?}: {}", path, e).red());
                                }
                            }
                        } else {
                            match fs::read_to_string(path) {
                                Ok(content) => {
                                    let label = format!("\n\n[File: {}]\n```\n{}\n```\n", path.display(), content);
                                    content_parts.push(Part::text(label));
                                    println!("{}", t!("text_added", path = path.display()).green());
                                }
                                Err(e) => {
                                    eprintln!("{}", format!("Error reading text file {:?}: {}", path, e).red());
                                }
                            }
                        }
                    }
                }

                session.add_user_message(&parsed.text);

                // --- Agent Loop ---
                loop {
                    let mut gemini_tools = Vec::new();
                    for (name, client) in mcp_clients.iter_mut() {
                         if let Ok(mcp_list) = client.list_tools() {
                             gemini_tools.push(map_mcp_tools_to_gemini(name, &mcp_list));
                         }
                    }
                    let tools_option = if gemini_tools.is_empty() { None } else { Some(gemini_tools) };

                    let (request_contents, request_model) = if let Some(ref cache_name) = active_cache_name {
                        (vec![Content {
                            role: "user".to_string(),
                            parts: content_parts.clone(), 
                        }], cache_name.clone())
                    } else {
                        let mut full_contents = session.to_gemini_history();
                        (full_contents, settings.model_name.clone())
                    };
                    
                    let thinking_config = if let Some(budget) = parsed.thinking_budget {
                         if budget == 0 { None } else if budget == -1 { Some(ThinkingConfig { include_thoughts: true, thinking_budget_token_count: None }) } 
                         else { Some(ThinkingConfig { include_thoughts: true, thinking_budget_token_count: Some(budget as u32) }) }
                    } else if settings.model_name.contains("thinking") || settings.model_name.contains("pro") {
                        Some(ThinkingConfig { include_thoughts: true, thinking_budget_token_count: Some(2048) })
                    } else { None };

                    let request = GenerateContentRequest {
                        contents: request_contents,
                        system_instruction: if active_cache_name.is_some() { None } else {
                            settings.system_instruction.as_ref().map(|s| Content {
                                role: "user".to_string(), 
                                parts: vec![Part::text(s.clone())],
                            })
                        },
                        generation_config: GenerationConfig {
                            temperature: settings.temperature,
                            max_output_tokens: settings.max_output_tokens,
                            top_p: None,
                            top_k: None,
                            thinking_config,
                        },
                        tools: tools_option,
                    };

                    print!("{}", t!("input_prompt"));
                    io::stdout().flush()?;

                    let mut full_response_text = String::new();
                    let mut function_calls: Vec<FunctionCall> = Vec::new();
                    let mut usage_meta = None;

                    match client.stream_generate_content(&request_model, &request).await {
                        Ok(mut stream) => {
                            while let Some(chunk_result) = stream.next().await {
                                match chunk_result {
                                    Ok(bytes) => {
                                        let s = String::from_utf8_lossy(&bytes);
                                        for line in s.lines() {
                                            if line.starts_with("data: ") {
                                                let json_str = &line[6..];
                                                if json_str.trim() == "[DONE]" { continue; }
                                                
                                                if let Ok(response) = serde_json::from_str::<client::models::GenerateContentResponse>(json_str) {
                                                    if let Some(meta) = response.usage_metadata { usage_meta = Some(meta); }
                                                    if let Some(candidates) = response.candidates {
                                                        for candidate in candidates {
                                                            if let Some(content) = candidate.content {
                                                                for part in content.parts {
                                                                    if let Some(text) = part.text {
                                                                        print!("{}", text);
                                                                        io::stdout().flush()?;
                                                                        full_response_text.push_str(&text);
                                                                    }
                                                                    if let Some(fc) = part.function_call {
                                                                        function_calls.push(fc);
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    Err(e) => eprintln!("\nStream Error: {}", e),
                                }
                            }
                        }
                        Err(e) => {
                            eprintln!("\nAPI Error: {}", e);
                            break; 
                        }
                    }
                    println!();

                    if !function_calls.is_empty() {
                        let mut parts = Vec::new();
                        if !full_response_text.is_empty() {
                            parts.push(Part::text(full_response_text.clone()));
                        }
                        for fc in &function_calls {
                            parts.push(Part {
                                text: None, inline_data: None, file_data: None, function_response: None,
                                function_call: Some(fc.clone()),
                            });
                        }
                        session.add_message("model", parts);

                        let mut responses = Vec::new();
                        for call in function_calls {
                            println!("{}", format!("🛠 Executing Tool: {}", call.name).yellow());
                            
                            let parts: Vec<&str> = call.name.splitn(2, "__").collect();
                            if parts.len() == 2 {
                                let server_name = parts[0];
                                let tool_name = parts[1];
                                
                                if let Some(mcp_client) = mcp_clients.get_mut(server_name) {
                                    match mcp_client.call_tool(tool_name, call.args.clone()) {
                                        Ok(result) => {
                                            println!("  -> Result: {}", result.to_string().chars().take(50).collect::<String>());
                                            responses.push(FunctionResponse {
                                                name: call.name.clone(),
                                                response: serde_json::json!({ "result": result }),
                                            });
                                        },
                                        Err(e) => {
                                            eprintln!("  -> Error: {}", e);
                                            responses.push(FunctionResponse {
                                                name: call.name.clone(),
                                                response: serde_json::json!({ "error": e.to_string() }),
                                            });
                                        }
                                    }
                                } else {
                                     responses.push(FunctionResponse {
                                        name: call.name.clone(),
                                        response: serde_json::json!({ "error": "MCP Server not found" }),
                                    });
                                }
                            } else {
                                responses.push(FunctionResponse {
                                    name: call.name.clone(),
                                    response: serde_json::json!({ "error": "Invalid tool name format" }),
                                });
                            }
                        }

                        let mut response_parts = Vec::new();
                        for fr in responses {
                            response_parts.push(Part {
                                text: None, inline_data: None, file_data: None, function_call: None,
                                function_response: Some(fr),
                            });
                        }
                        session.add_message("function", response_parts);
                        continue;

                    } else {
                        if !full_response_text.is_empty() {
                             session.add_model_message(&full_response_text);
                        }

                        if let Some(meta) = usage_meta {
                            let (usd, twd) = pricing.calculate(&settings.model_name, meta.prompt_token_count, meta.candidates_token_count);
                            println!("{}", "─".repeat(60).truecolor(181, 101, 216));
                            println!("{}", t!("cost_info", twd = format!("{:.4}", twd), usd = format!("{:.6}", usd), total = meta.total_token_count, input = meta.prompt_token_count, output = meta.candidates_token_count));
                        }
                        
                        if !full_response_text.is_empty() {
                            println!("{}", "─".repeat(60).truecolor(181, 101, 216));
                            skin.print_text(&full_response_text);
                            println!("{}", "─".repeat(60).truecolor(181, 101, 216));
                        }
                        
                        break;
                    }
                } 
            }
            Ok(None) => break, 
            Err(e) => {
                eprintln!("{}", t!("error_read_input", error = e));
                break;
            }
        }
    }

    Ok(())
}
