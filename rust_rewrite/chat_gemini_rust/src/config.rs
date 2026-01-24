use config::{Config, ConfigError, File, Environment};
use serde::Deserialize;
use std::env;
use dotenvy::dotenv;
use std::collections::HashMap;

#[derive(Debug, Deserialize, Clone)]
pub struct Settings {
    pub gemini_api_key: String,
    pub model_name: String,
    pub temperature: f32,
    pub max_output_tokens: u32,
    pub system_instruction: Option<String>,
    #[allow(dead_code)]
    pub language: String,
    
    // OAuth 2.0 Configuration
    pub oauth_client_id: Option<String>,
    pub oauth_client_secret: Option<String>,
    pub oauth_secret_file: Option<String>, // Path to client_secret.json
    
    #[serde(default)]
    pub mcp: McpConfig,
}

#[derive(Debug, Deserialize, Clone, Default)]
pub struct McpConfig {
    pub servers: HashMap<String, McpServerConfig>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct McpServerConfig {
    pub command: String,
    pub args: Vec<String>,
}

impl Settings {
    pub fn new() -> Result<Self, ConfigError> {
        dotenv().ok();

        let builder = Config::builder()
            .set_default("model_name", "gemini-2.0-flash")?
            .set_default("temperature", 0.7)?
            .set_default("max_output_tokens", 8192)?
            .set_default("language", "zh-TW")?
            .set_default("gemini_api_key", "")? 
            .set_default("oauth_client_id", None::<String>)?
            .set_default("oauth_client_secret", None::<String>)?
            .set_default("oauth_secret_file", None::<String>)?
            
            .add_source(File::with_name("config").required(false))
            .add_source(Environment::with_prefix("GEMINI").separator("_"));

        let config = builder.build()?;
        let mut settings: Settings = config.try_deserialize()?;
        
        if settings.gemini_api_key.is_empty() {
             if let Ok(key) = env::var("GEMINI_API_KEY") {
                 settings.gemini_api_key = key;
             } else if let Ok(key) = env::var("GOOGLE_API_KEY") {
                 settings.gemini_api_key = key;
             }
        }

        Ok(settings)
    }
}