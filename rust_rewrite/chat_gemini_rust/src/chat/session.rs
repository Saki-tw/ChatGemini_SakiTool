use crate::client::models::{Content, Part};
use chrono::{DateTime, Local};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    pub parts: Vec<Part>, // Changed from String content to Vec<Part> to support multimodal/function
    pub timestamp: DateTime<Local>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatSession {
    pub history: Vec<ChatMessage>,
    pub total_cost: f64,
}

impl ChatSession {
    pub fn new() -> Self {
        Self {
            history: Vec::new(),
            total_cost: 0.0,
        }
    }

    pub fn add_user_message(&mut self, text: &str) {
        self.history.push(ChatMessage {
            role: "user".to_string(),
            parts: vec![Part::text(text.to_string())],
            timestamp: Local::now(),
        });
    }

    pub fn add_model_message(&mut self, text: &str) {
        self.history.push(ChatMessage {
            role: "model".to_string(),
            parts: vec![Part::text(text.to_string())],
            timestamp: Local::now(),
        });
    }

    // Generic add for complex parts (files, functions)
    pub fn add_message(&mut self, role: &str, parts: Vec<Part>) {
        self.history.push(ChatMessage {
            role: role.to_string(),
            parts,
            timestamp: Local::now(),
        });
    }

    pub fn to_gemini_history(&self) -> Vec<Content> {
        self.history.iter().map(|msg| Content {
            role: msg.role.clone(),
            parts: msg.parts.clone(),
        }).collect()
    }

    pub fn clear(&mut self) {
        self.history.clear();
        self.total_cost = 0.0;
    }
}