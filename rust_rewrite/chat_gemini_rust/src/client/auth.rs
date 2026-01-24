use yup_oauth2::{ApplicationDefaultCredentialsAuthenticator, InstalledFlowAuthenticator, InstalledFlowReturnMethod};
use yup_oauth2::authenticator::Authenticator;
use yup_oauth2::authenticator::ApplicationDefaultCredentialsTypes;
use hyper_rustls::HttpsConnector;
use hyper_util::client::legacy::connect::HttpConnector;
use anyhow::{Result, Context};
use std::sync::Arc;
use colored::Colorize;
use crate::config::Settings;

// Scope for Gemini API
const SCOPE: &str = "https://www.googleapis.com/auth/generativelanguage";
const CLOUD_PLATFORM_SCOPE: &str = "https://www.googleapis.com/auth/cloud-platform";

#[derive(Clone)]
pub enum AuthMethod {
    ApiKey(String),
    OAuth(Arc<Authenticator<HttpsConnector<HttpConnector>>>),
}

pub struct GoogleAuth {
    method: AuthMethod,
}

impl GoogleAuth {
    pub async fn new(settings: &Settings) -> Result<Self> {
        // 1. API Key Priority
        if !settings.gemini_api_key.is_empty() {
            return Ok(Self { method: AuthMethod::ApiKey(settings.gemini_api_key.clone()) });
        }

        println!("{}", "正在嘗試 Application Default Credentials (ADC)...".yellow());
        
        // 2. Try ADC
        let opts = yup_oauth2::ApplicationDefaultCredentialsFlowOpts::default();
        let authenticator = ApplicationDefaultCredentialsAuthenticator::builder(opts).await;
        
        let adc_result = match authenticator {
             ApplicationDefaultCredentialsTypes::InstanceMetadata(auth) => auth.build().await,
             ApplicationDefaultCredentialsTypes::ServiceAccount(auth) => auth.build().await,
        };

        if let Ok(auth) = adc_result {
             println!("{}", "已連接 ADC 憑證。".green());
             return Ok(Self { method: AuthMethod::OAuth(Arc::new(auth)) });
        }

        // 3. Try Interactive Flow (OAuth 2.0 Client ID)
        println!("{}", "未檢測到 ADC，正在檢查 OAuth Client 配置...".yellow());

        let app_secret = if let Some(path) = &settings.oauth_secret_file {
            println!("讀取 Client Secret 檔案: {}", path);
            yup_oauth2::read_application_secret(path).await
                .context("讀取 client_secret.json 失敗")?
        } else if let (Some(id), Some(secret)) = (&settings.oauth_client_id, &settings.oauth_client_secret) {
            println!("使用環境變數中的 Client ID/Secret");
            yup_oauth2::ApplicationSecret {
                client_id: id.clone(),
                client_secret: secret.clone(),
                token_uri: "https://oauth2.googleapis.com/token".to_string(),
                auth_uri: "https://accounts.google.com/o/oauth2/auth".to_string(),
                redirect_uris: vec!["http://localhost".to_string()],
                ..Default::default()
            }
        } else {
            return Err(anyhow::anyhow!("認證失敗：未提供 API Key，未檢測到 ADC，且未提供 OAuth Client Secret。\n請參閱 README 設定 'GEMINI_API_KEY' 或 'client_secret.json'。"));
        };

        println!("{}", "啟動瀏覽器互動登入流程...".blue());
        let auth = InstalledFlowAuthenticator::builder(
            app_secret,
            InstalledFlowReturnMethod::HTTPRedirect,
        )
        .persist_tokens_to_disk("token_cache.json")
        .build()
        .await?;

        println!("{}", "OAuth 初始化完成。請在瀏覽器中完成登入。".green());
        Ok(Self { method: AuthMethod::OAuth(Arc::new(auth)) })
    }

    pub async fn get_token(&self) -> Result<Option<String>> {
        match &self.method {
            AuthMethod::ApiKey(_) => Ok(None),
            AuthMethod::OAuth(auth) => {
                let token = auth.token(&[SCOPE]).await;
                
                let token = match token {
                    Ok(t) => t,
                    Err(_) => auth.token(&[CLOUD_PLATFORM_SCOPE]).await.context("無法獲取 OAuth Token")?,
                };
                
                let token_str = token.token().ok_or_else(|| anyhow::anyhow!("Empty token"))?;
                Ok(Some(token_str.to_string()))
            }
        }
    }
    
    pub fn get_api_key(&self) -> Option<&str> {
        match &self.method {
            AuthMethod::ApiKey(key) => Some(key),
            AuthMethod::OAuth(_) => None,
        }
    }
}
