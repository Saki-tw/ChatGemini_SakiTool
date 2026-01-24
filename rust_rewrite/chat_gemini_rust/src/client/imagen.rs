use crate::client::rest::GeminiClient;
use serde::{Deserialize, Serialize};
use anyhow::Result;
use reqwest::Response;
use std::path::PathBuf;
use tokio::fs;
use base64::prelude::*;
use chrono::Local;

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct ImagenRequest {
    instances: Vec<ImagenInstance>,
    parameters: ImagenParameters,
}

#[derive(Debug, Serialize)]
struct ImagenInstance {
    prompt: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct ImagenParameters {
    sample_count: u32,
    aspect_ratio: String, // "1:1", "16:9", "9:16"
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ImagenResponse {
    predictions: Option<Vec<ImagenPrediction>>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ImagenPrediction {
    bytes_base64_encoded: String,
    #[allow(dead_code)]
    mime_type: String,
}

pub struct ImagenClient<'a> {
    client: &'a GeminiClient,
}

impl<'a> ImagenClient<'a> {
    pub fn new(client: &'a GeminiClient) -> Self {
        Self { client }
    }

    pub async fn generate_image(&self, prompt: &str) -> Result<PathBuf> {
        let url = format!("{}/models/imagen-3.0-generate-001:predict", self.client.base_url);

        let request = ImagenRequest {
            instances: vec![ImagenInstance { prompt: prompt.to_string() }],
            parameters: ImagenParameters {
                sample_count: 1,
                aspect_ratio: "1:1".to_string(),
            },
        };

        let res: Response = self.client.post(&url).await
            .json(&request)
            .send()
            .await?;

        let response: ImagenResponse = res.error_for_status()?.json().await?;

        if let Some(predictions) = response.predictions {
            if let Some(first) = predictions.first() {
                let bytes = BASE64_STANDARD.decode(&first.bytes_base64_encoded)?;
                
                let dir = PathBuf::from("generated_images");
                if !dir.exists() {
                    fs::create_dir(&dir).await?;
                }

                let filename = format!("imagen_{}.png", Local::now().format("%Y%m%d_%H%M%S"));
                let path = dir.join(filename);
                
                fs::write(&path, bytes).await?;
                return Ok(path);
            }
        }

        Err(anyhow::anyhow!("No image generated"))
    }
}