use crate::client::rest::GeminiClient;
use crate::client::models::CachedContent;
use anyhow::Result;
use reqwest::Response;

pub struct CacheManager<'a> {
    client: &'a GeminiClient,
}

impl<'a> CacheManager<'a> {
    pub fn new(client: &'a GeminiClient) -> Self {
        Self { client }
    }

    pub async fn create(&self, cached_content: &CachedContent) -> Result<CachedContent> {
        let url = format!("{}/cachedContents", self.client.base_url);
        
        let res: Response = self.client.post(&url).await
            .json(cached_content)
            .send()
            .await?;

        let response: CachedContent = res.error_for_status()?.json().await?;
        Ok(response)
    }
}
