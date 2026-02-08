use ignore::WalkBuilder;
use std::path::Path;
use anyhow::Result;
use std::fs;

pub struct FileWalker;

impl FileWalker {
    pub fn walk(path: &Path) -> Result<Vec<(String, String)>> {
        let mut files = Vec::new();
        let walker = WalkBuilder::new(path)
            .hidden(false) // Allow hidden files if gitignore doesn't hide them? No, usually keep defaults.
            .git_ignore(true)
            .build();

        for result in walker {
            match result {
                Ok(entry) => {
                    if entry.file_type().map_or(false, |ft| ft.is_file()) {
                        let path = entry.path();
                        // Filter binary files naively by extension or mimetype check?
                        // For MVP, allow common code extensions or try to read as utf8.
                        if let Ok(content) = fs::read_to_string(path) {
                            if !content.trim().is_empty() {
                                files.push((path.to_string_lossy().to_string(), content));
                            }
                        }
                    }
                }
                Err(err) => eprintln!("Walk error: {}", err),
            }
        }
        Ok(files)
    }
}
