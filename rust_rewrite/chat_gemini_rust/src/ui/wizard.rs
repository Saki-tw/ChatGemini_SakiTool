use std::io::{self, Write};
use std::fs;
use colored::Colorize;
use anyhow::Result;
use crate::config::Settings;

pub fn run_onboarding() -> Result<Settings> {
    println!("{}", "┌──────────────────────────────────────────────┐".purple());
    println!("{}", "│      SakiTool - Authentication Wizard        │".purple());
    println!("{}", "└──────────────────────────────────────────────┘".purple());
    println!("\n偵測不到有效的認證憑證。請選擇連接方式：\n");
    
    println!("1. {} (推薦個人使用)", "輸入 Gemini API Key".cyan().bold());
    println!("2. {} (需要 client_secret.json)", "Google 帳號登入 (OAuth)".yellow().bold());
    println!("3. 離開\n");

    print!("請選擇 [1-3]: ");
    io::stdout().flush()?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)?;
    let choice = input.trim();

    match choice {
        "1" => setup_api_key(),
        "2" => setup_oauth(),
        _ => Err(anyhow::anyhow!("操作已取消")),
    }
}

fn setup_api_key() -> Result<Settings> {
    print!("\n請輸入您的 Gemini API Key: ");
    io::stdout().flush()?;
    
    let mut key = String::new();
    io::stdin().read_line(&mut key)?;
    let key = key.trim().to_string();

    if key.is_empty() {
        return Err(anyhow::anyhow!("API Key 不能為空"));
    }

    // Ask to save
    print!("是否儲存至 .env 檔案以供未來使用？ (y/n): ");
    io::stdout().flush()?;
    let mut save = String::new();
    io::stdin().read_line(&mut save)?;
    
    if save.trim().eq_ignore_ascii_case("y") {
        let content = format!("GEMINI_API_KEY={}\nGEMINI_MODEL=gemini-2.0-flash\nGEMINI_LANG=zh-TW\n", key);
        fs::write(".env", content)?;
        println!("{}", "設定已儲存至 .env".green());
    }

    // Reload settings by setting env var temporarily
    // Safety: Only safe if single threaded. At startup main thread, it is.
    unsafe {
        std::env::set_var("GEMINI_API_KEY", &key);
    }
    
    // Reload settings
    Settings::new().map_err(|e| anyhow::anyhow!(e))
}

fn setup_oauth() -> Result<Settings> {
    println!("\n請輸入 'client_secret.json' 的路徑 (預設為 ./client_secret.json):");
    print!("路徑: ");
    io::stdout().flush()?;
    
    let mut path = String::new();
    io::stdin().read_line(&mut path)?;
    let mut path = path.trim().to_string();
    if path.is_empty() {
        path = "client_secret.json".to_string();
    }

    if !std::path::Path::new(&path).exists() {
        return Err(anyhow::anyhow!("找不到檔案: {}", path));
    }

    print!("是否儲存路徑至 .env？ (y/n): ");
    io::stdout().flush()?;
    let mut save = String::new();
    io::stdin().read_line(&mut save)?;
    
    if save.trim().eq_ignore_ascii_case("y") {
        let content = format!("GEMINI_OAUTH_SECRET_FILE={}\nGEMINI_MODEL=gemini-2.0-flash\nGEMINI_LANG=zh-TW\n", path);
        fs::write(".env", content)?;
        println!("{}", "設定已儲存至 .env".green());
    }

    unsafe {
        std::env::set_var("GEMINI_OAUTH_SECRET_FILE", &path);
    }
    Settings::new().map_err(|e| anyhow::anyhow!(e))
}