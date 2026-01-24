use regex::Regex;
use std::path::PathBuf;
use glob::glob;

#[derive(Debug)]
pub struct ParsedInput {
    pub text: String,
    pub thinking_budget: Option<i32>, // -1 for auto, 0 for off, >0 for specific
    pub files: Vec<PathBuf>,
    pub cache_action: Option<String>, // "now", "off"
}

impl ParsedInput {
    pub fn new() -> Self {
        Self {
            text: String::new(),
            thinking_budget: None,
            files: Vec::new(),
            cache_action: None,
        }
    }
}

pub fn parse_input(input: &str) -> ParsedInput {
    let mut parsed = ParsedInput::new();
    let mut clean_text = input.to_string();

    // 1. Parse [think:N] or [no-think]
    let think_regex = Regex::new(r"(?i)\[think:(-?\d+|auto)\]").unwrap();
    if let Some(caps) = think_regex.captures(&clean_text) {
        let val = &caps[1];
        parsed.thinking_budget = if val == "auto" { Some(-1) } else { val.parse().ok() };
        clean_text = think_regex.replace(&clean_text, "").to_string();
    }
    
    let no_think_regex = Regex::new(r"(?i)\[no-think\]").unwrap();
    if no_think_regex.is_match(&clean_text) {
        parsed.thinking_budget = Some(0);
        clean_text = no_think_regex.replace(&clean_text, "").to_string();
    }

    // 2. Parse [cache:now/off]
    let cache_regex = Regex::new(r"(?i)\[cache:(now|off)\]").unwrap();
    if let Some(caps) = cache_regex.captures(&clean_text) {
        parsed.cache_action = Some(caps[1].to_string());
        clean_text = cache_regex.replace(&clean_text, "").to_string();
    }

    // 3. Parse @filename or 附加 filename
    let file_regex = Regex::new(r"(?i)(?:@|附加\s+)(\S+)").unwrap();
    
    let mut files_to_remove = Vec::new();
    for caps in file_regex.captures_iter(&clean_text) {
        let path_str = &caps[1];
        
        // Glob expansion
        if let Ok(paths) = glob(path_str) {
            for entry in paths {
                if let Ok(path) = entry {
                    if path.exists() {
                        parsed.files.push(path);
                    }
                }
            }
        } else {
            // Direct path (no glob patterns)
            let path = PathBuf::from(path_str);
            if path.exists() {
                parsed.files.push(path);
            }
        }
        files_to_remove.push(caps[0].to_string());
    }

    for tag in files_to_remove {
        clean_text = clean_text.replace(&tag, "");
    }

    parsed.text = clean_text.trim().to_string();
    parsed
}