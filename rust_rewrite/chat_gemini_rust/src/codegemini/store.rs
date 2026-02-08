use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::{BufReader, BufWriter};
use std::path::Path;
use anyhow::{Result, Context};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct VectorDocument {
    pub file_path: String,
    pub content: String,
    pub embedding: Vec<f32>,
}

#[derive(Serialize, Deserialize)]
pub struct SimpleVectorStore {
    documents: Vec<VectorDocument>,
}

impl SimpleVectorStore {
    pub fn new() -> Self {
        Self { documents: Vec::new() }
    }

    pub fn add(&mut self, doc: VectorDocument) {
        self.documents.push(doc);
    }

    pub fn search(&self, query_vector: &[f32], top_k: usize) -> Vec<(&VectorDocument, f32)> {
        let mut scores: Vec<(&VectorDocument, f32)> = self.documents.iter()
            .map(|doc| {
                let score = cosine_similarity(&doc.embedding, query_vector);
                (doc, score)
            })
            .collect();

        // Sort desc
        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scores.into_iter().take(top_k).collect()
    }
    
    pub fn clear(&mut self) {
        self.documents.clear();
    }
    
    pub fn count(&self) -> usize {
        self.documents.len()
    }

    pub fn save<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let file = File::create(path)?;
        let writer = BufWriter::new(file);
        serde_json::to_writer(writer, &self)?;
        Ok(())
    }

    pub fn load<P: AsRef<Path>>(path: P) -> Result<Self> {
        let file = File::open(path)?;
        let reader = BufReader::new(file);
        let store = serde_json::from_reader(reader).context("Failed to parse vector store JSON")?;
        Ok(store)
    }
}

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    let dot_product: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    
    if norm_a == 0.0 || norm_b == 0.0 {
        0.0
    } else {
        dot_product / (norm_a * norm_b)
    }
}
