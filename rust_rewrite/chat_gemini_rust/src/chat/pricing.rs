pub struct PricingModel {
    pub input_price_per_1m: f64,
    pub output_price_per_1m: f64,
}

pub struct PricingCalculator {
    pub usd_to_twd: f64,
}

impl PricingCalculator {
    pub fn new(usd_to_twd: f64) -> Self {
        Self { usd_to_twd }
    }

    pub fn get_model_pricing(&self, model_name: &str) -> PricingModel {
        // 2025-11-29 費率基準 (USD)
        if model_name.contains("flash") {
            // Gemini 2.5 Flash / 2.0 Flash
            // Input: $0.10 / 1M, Output: $0.40 / 1M (Lite 費率參考)
            // 標準 Flash: Input $0.075, Output $0.30 (<=128k)
            // 簡化使用標準 Flash 費率
            PricingModel {
                input_price_per_1m: 0.075,
                output_price_per_1m: 0.30,
            }
        } else if model_name.contains("pro") || model_name.contains("3-pro") {
            // Gemini 2.5 Pro / 3.0 Pro
            // Input: $1.25 / 1M, Output: $5.00 / 1M
            PricingModel {
                input_price_per_1m: 1.25,
                output_price_per_1m: 5.00,
            }
        } else {
            // 預設 (Flash)
            PricingModel {
                input_price_per_1m: 0.075,
                output_price_per_1m: 0.30,
            }
        }
    }

    pub fn calculate(&self, model: &str, input_tokens: u32, output_tokens: u32) -> (f64, f64) {
        let pricing = self.get_model_pricing(model);
        
        let input_cost_usd = (input_tokens as f64 / 1_000_000.0) * pricing.input_price_per_1m;
        let output_cost_usd = (output_tokens as f64 / 1_000_000.0) * pricing.output_price_per_1m;
        
        let total_usd = input_cost_usd + output_cost_usd;
        let total_twd = total_usd * self.usd_to_twd;
        
        (total_usd, total_twd)
    }
}
