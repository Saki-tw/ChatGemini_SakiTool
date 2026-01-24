use super::models::*;
use crate::client::auth::GoogleAuth;
use reqwest::header::{HeaderMap, HeaderValue, CONTENT_TYPE, AUTHORIZATION};
use reqwest::{Client, Error};
use futures_util::StreamExt;
use std::pin::Pin;
use futures_util::Stream;
use bytes::Bytes;
use std::sync::Arc;

pub struct GeminiClient {
    pub client: Client, 
    pub auth: Arc<GoogleAuth>,
    pub base_url: String, 
}

impl GeminiClient {
    pub async fn new(auth: Arc<GoogleAuth>) -> Self {
        let mut headers = HeaderMap::new();
        headers.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));
        
        if let Some(key) = auth.get_api_key() {
             let mut api_key_value = HeaderValue::from_str(key).unwrap_or(HeaderValue::from_static(""));
             api_key_value.set_sensitive(true);
             headers.insert("x-goog-api-key", api_key_value);
        }

        let client = Client::builder()
            .default_headers(headers)
            .build()
            .expect("建構 HTTP 客戶端失敗");

        Self {
            client,
            auth,
            base_url: "https://generativelanguage.googleapis.com/v1beta".to_string(),
        }
    }
    
    pub fn api_key(&self) -> &str {
        self.auth.get_api_key().unwrap_or("")
    }

    async fn prepare_request(&self, request_builder: reqwest::RequestBuilder) -> reqwest::RequestBuilder {
        if let Ok(Some(token)) = self.auth.get_token().await {
            request_builder.header(AUTHORIZATION, format!("Bearer {}", token))
        } else if let Some(key) = self.auth.get_api_key() {
             // We can't easily append query params to an existing RequestBuilder securely without reconstructing URL.
             // However, `reqwest` allows calling `query` multiple times which merges params.
             // The previous error was `no method query`. 
             // Ah, `reqwest::RequestBuilder` HAS `query`. The error `E0599` "no method named query found" usually means trait `Sized` is not satisfied or similar, OR I was using a reference `&RequestBuilder`?
             // Ah, my previous code `req = self.prepare_request(req).await;` passes ownership.
             // Wait, `RequestBuilder::query` takes `&self` (mut) or `self`? It takes `self`.
             // The error might have been because `key` was `&str` and query expects `&Serialize`. `&[("key", key)]` IS `Serialize`.
             // Let's rely on `x-goog-api-key` header which we set in constructor.
             // So we might NOT need to add query param if header works.
             // Google API supports both. Header is cleaner.
             // So for API Key, we do nothing here (header is already set).
             request_builder
        } else {
            request_builder
        }
    }

    pub async fn stream_generate_content(
        &self,
        model: &str,
        request: &GenerateContentRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<Bytes, Error>> + Send>>, Error> {
        let url = format!("{}/models/{}:streamGenerateContent?alt=sse", self.base_url, model);

        let mut req = self.client.post(&url).json(request);
        req = self.prepare_request(req).await;

        let res = req.send().await?;
        let res = res.error_for_status()?;
        
        Ok(Box::pin(res.bytes_stream()))
    }
    
    pub async fn post(&self, url: &str) -> reqwest::RequestBuilder {
         let mut req = self.client.post(url);
         req = self.prepare_request(req).await;
         req
    }
    
    pub async fn put(&self, url: &str) -> reqwest::RequestBuilder {
         let mut req = self.client.put(url);
         req = self.prepare_request(req).await;
         req
    }
}
