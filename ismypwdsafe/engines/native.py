from .. import patterns
from ..metrics import calc_charset, calc_combinations
from .base import EngineScore


class NativeEngine:
    name = "native"

    def score(self, password: str) -> EngineScore:
        charset, _, _, _, _, _ = calc_charset(password)
        _, log10_value = calc_combinations(charset, len(password))
        
        base_score = int(min(100, max(0, log10_value * 5)))
        
        pattern_result = patterns.detect_pattern(password)
        if pattern_result.detected:
            base_score = min(base_score, 30)
            
        if pattern_result.detected or log10_value < 10:
            rating = "weak"
        elif log10_value < 14:
            rating = "medium"
        else:
            rating = "strong"
            
        return EngineScore(
            value=base_score, 
            rating=rating, 
            raw_score_0_4=None,
            engine_name="native"
        )