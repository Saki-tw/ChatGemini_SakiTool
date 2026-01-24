use crate::client::rest::GeminiClient;
use anyhow::Result;
use reqwest::Response;
use serde::Serialize;
use serde::Deserialize;

#[derive(Debug, Serialize)]
struct EmbedContentRequest {
    content: ContentPart,
    model: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct ContentPart {
    parts: Vec<TextPart>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct TextPart {
    text: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct EmbedContentResponse {
    embedding: EmbeddingValues,
}

#[derive(Debug, Deserialize)]
struct EmbeddingValues {
    values: Vec<f32>,
}

pub struct EmbeddingGenerator<'a> {
    client: &'a GeminiClient,
    model: String,
}

impl<'a> EmbeddingGenerator<'a> {
    pub fn new(client: &'a GeminiClient) -> Self {
        Self {
            client,
            model: "models/embedding-001".to_string(), // Default embedding model
        }
    }

    #[allow(dead_code)]
    pub async fn generate_embedding(&self, text: &str) -> Result<Vec<f32>> {
        let url = format!("{}/{}:embedContent", self.client.base_url, self.model);
        
        // Fix: Use client.post which handles auth
        // Previous error: self.client.api_key field access (it's now a method or hidden)
        
        let request = EmbedContentRequest {
            model: self.model.clone(),
            content: ContentPart {
                parts: vec![TextPart { text: text.to_string() }],
            },
        };

        let res: Response = self.client.post(&url).await
            .json(&request)
            .send()
            .await?;

        let response: EmbedContentResponse = res.error_for_status()?.json().await?;
        Ok(response.embedding.values)
    }
}
