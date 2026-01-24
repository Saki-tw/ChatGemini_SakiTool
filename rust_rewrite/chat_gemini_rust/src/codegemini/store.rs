use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct VectorDocument {
    pub id: String,
    pub content: String,
    pub vector: Vec<f32>,
    pub metadata: HashMap<String, String>,
}

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
        if self.documents.is_empty() {
            return Vec::new();
        }

        let mut scores: Vec<(&VectorDocument, f32)> = self.documents
            .iter()
            .map(|doc| {
                let score = cosine_similarity(&doc.vector, query_vector);
                (doc, score)
            })
            .collect();

        // 降序排序
        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scores.truncate(top_k);
        scores
    }
}

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    let dot_product: f32 = a.iter().zip(b).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    
    dot_product / (norm_a * norm_b)
}
