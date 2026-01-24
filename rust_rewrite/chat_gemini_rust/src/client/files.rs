use crate::client::rest::GeminiClient;
use serde::{Deserialize, Serialize};
use anyhow::Result;
use std::path::Path;
use tokio::fs::File;
use tokio::io::AsyncReadExt;
use reqwest::{Body, Response};

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct FileData {
    pub name: String,
    pub display_name: Option<String>,
    pub mime_type: String,
    pub size_bytes: String,
    pub create_time: String,
    pub update_time: String,
    pub expiration_time: String,
    pub sha256_hash: String,
    pub uri: String,
    pub state: String, // PROCESSING, ACTIVE, FAILED
}

#[derive(Debug, Serialize)]
struct UploadMetadata {
    file: FileMetadata,
}

#[derive(Debug, Serialize)]
struct FileMetadata {
    display_name: String,
}

#[derive(Debug, Deserialize)]
struct UploadResponse {
    file: FileData,
}

pub struct FileManager<'a> {
    client: &'a GeminiClient,
}

impl<'a> FileManager<'a> {
    pub fn new(client: &'a GeminiClient) -> Self {
        Self { client }
    }

    pub async fn upload(&self, path: &Path, mime_type: &str) -> Result<FileData> {
        let upload_url_base = "https://generativelanguage.googleapis.com/upload/v1beta/files";
        
        // Use client wrapper but note upload URL is different base (upload/v1beta vs v1beta)
        // Client wrapper prepends auth logic.
        // We need to use `client.post` with the full URL.
        
        let file_name = path.file_name().unwrap_or_default().to_string_lossy().to_string();
        let metadata = UploadMetadata {
            file: FileMetadata { display_name: file_name },
        };
        
        let mut file = File::open(path).await?;
        let size = file.metadata().await?.len();
        
        // Step 1: Start Upload Session
        let res: Response = self.client.post(upload_url_base).await
            .header("X-Goog-Upload-Protocol", "resumable")
            .header("X-Goog-Upload-Command", "start")
            .header("X-Goog-Upload-Header-Content-Length", size.to_string())
            .header("X-Goog-Upload-Header-Content-Type", mime_type)
            .json(&metadata)
            .send()
            .await?;
            
        let res = res.error_for_status()?;
        let upload_url = res.headers().get("x-goog-upload-url")
            .ok_or_else(|| anyhow::anyhow!("No upload URL returned"))?
            .to_str()?;

        // Step 2: Upload Bytes
        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer).await?;
        
        // Step 2 uses PUT to a specific upload_url. Auth headers are usually NOT required for the session URL,
        // but let's check. Google Upload Protocol usually embeds token in the upload_url or session.
        // If we add auth header again it might be fine or redundant.
        // Let's use `client.put` which ADDS auth header. If it fails, we revert to raw client.
        
        let res: Response = self.client.put(upload_url).await
            .header("Content-Length", size.to_string())
            .header("X-Goog-Upload-Offset", "0")
            .header("X-Goog-Upload-Command", "upload, finalize")
            .body(Body::from(buffer))
            .send()
            .await?;
            
        let response: UploadResponse = res.error_for_status()?.json().await?;
        Ok(response.file)
    }
}
