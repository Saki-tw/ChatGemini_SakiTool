use rust_i18n::i18n;

i18n!("locales", fallback = "zh-TW");

pub fn set_locale(lang: &str) {
    rust_i18n::set_locale(lang);
}
