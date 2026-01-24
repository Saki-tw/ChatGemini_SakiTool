use reedline::{DefaultPrompt, Reedline, Signal};
use std::io;

pub struct Repl {
    line_editor: Reedline,
    prompt: DefaultPrompt,
}

impl Repl {
    pub fn new() -> Self {
        Self {
            line_editor: Reedline::create(),
            prompt: DefaultPrompt::default(),
        }
    }

    pub fn read_line(&mut self) -> Result<Option<String>, io::Error> {
        let sig = self.line_editor.read_line(&self.prompt);
        match sig {
            Ok(Signal::Success(buffer)) => Ok(Some(buffer)),
            Ok(Signal::CtrlD) | Ok(Signal::CtrlC) => Ok(None),
            Err(e) => Err(e),
        }
    }
}
