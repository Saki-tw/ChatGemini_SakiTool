pub struct Chunker;

impl Chunker {
    pub fn chunk(text: &str, max_lines: usize) -> Vec<String> {
        let lines: Vec<&str> = text.lines().collect();
        let mut chunks = Vec::new();
        
        for chunk in lines.chunks(max_lines) {
            let joined = chunk.join("\n");
            if !joined.trim().is_empty() {
                chunks.push(joined);
            }
        }
        chunks
    }
}
