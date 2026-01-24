use crossterm::style::{Color, Attribute};
use termimad::{MadSkin, StyledChar};

// Saki Studio Color Palette
pub const MACARON_PURPLE: Color = Color::Rgb { r: 181, g: 101, b: 216 }; // #B565D8
pub const MACARON_PURPLE_LIGHT: Color = Color::Rgb { r: 232, g: 196, b: 240 }; // #E8C4F0
pub const FORGET_ME_NOT: Color = Color::Rgb { r: 135, g: 206, b: 235 }; // #87CEEB (Sky Blueish)
pub const FORGET_ME_NOT_LIGHT: Color = Color::Rgb { r: 176, g: 224, b: 230 }; // #B0E0E6

pub fn create_skin() -> MadSkin {
    let mut skin = MadSkin::default();
    
    // Headers: Macaron Purple
    skin.bold.set_fg(MACARON_PURPLE);
    skin.headers[0].set_fg(MACARON_PURPLE);
    skin.headers[0].add_attr(Attribute::Bold);
    
    // Code blocks: Dark background with Forget-me-not text (or default syntax highlighting if termimad supports)
    skin.code_block.set_fg(FORGET_ME_NOT_LIGHT);
    skin.code_block.set_bg(Color::Rgb { r: 30, g: 30, b: 30 }); // Dark Grey
    
    // Inline code
    skin.inline_code.set_fg(MACARON_PURPLE_LIGHT);
    skin.inline_code.set_bg(Color::Rgb { r: 40, g: 40, b: 40 });

    // Quote
    skin.quote_mark = StyledChar::from_fg_char(FORGET_ME_NOT, '▌');
    skin.quote_mark.set_fg(FORGET_ME_NOT);

    skin
}
