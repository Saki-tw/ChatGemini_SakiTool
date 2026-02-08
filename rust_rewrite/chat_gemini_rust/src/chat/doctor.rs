use colored::Colorize;
use reqwest::Client;
use std::path::Path;
use anyhow::Result;
use crate::config::Settings;
use crate::client::auth::GoogleAuth;

pub struct Doctor;

impl Doctor {
    pub async fn check(settings: &Settings) -> Result<()> {
        println!("{}", "🩺 ChatGemini Doctor - 自我診斷報告".purple().bold());
        println!("{}", "─".repeat(40).dimmed());

        // 1. API Connectivity
        print!("• 連接 Google API ... ");
        let client = Client::new();
        match client.get("https://generativelanguage.googleapis.com").send().await {
            Ok(_) => println!("{}", "OK".green()),
            Err(e) => println!("{} ({})", "FAIL".red(), e),
        }

        // 2. Auth Status
        print!("• 認證狀態 ... ");
        if !settings.gemini_api_key.is_empty() {
            println!("{}", "API Key (Present)".green());
        } else {
            // Check ADC
            match GoogleAuth::new(settings).await {
                Ok(_) => println!("{}", "OAuth/ADC (Active)".green()),
                Err(_) => println!("{} (請執行 .env 或 ADC 設定)", "MISSING".red()),
            }
        }

        // 3. File System
        print!("• 圖像輸出目錄 (generated_images/) ... ");
        let img_dir = Path::new("generated_images");
        if img_dir.exists() {
             if img_dir.metadata()?.permissions().readonly() {
                 println!("{}", "READ-ONLY (Error)".red());
             } else {
                 println!("{}", "OK".green());
             }
        } else {
             match std::fs::create_dir(img_dir) {
                 Ok(_) => println!("{}", "CREATED".yellow()),
                 Err(e) => println!("{} ({})", "FAIL".red(), e),
             }
        }

        println!("\n診斷完成。若有錯誤，請參考文件修復。");
        Ok(())
    }
}
