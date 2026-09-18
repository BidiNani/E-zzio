"""
E-ZZIO V7.34 — Impact Analyzer
Analyse la complexité, le coût en ressources estimé et le risque de régression d'un candidat.
"""

import ast


class ImpactAnalyzer:
    @staticmethod
    def analyze_impact(content: str) -> dict:
        tree = ast.parse(content)

        # Métriques basées sur l'AST
        function_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
        loop_count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.For, ast.While)))
        lines_of_code = len(content.splitlines())

        # Calculs heuristiques de complexité et de coût
        complexity_score = min(1.0, (function_count * 0.1) + (loop_count * 0.2) + (lines_of_code * 0.01))
        resource_cost = "LOW" if lines_of_code < 50 else ("MEDIUM" if lines_of_code < 200 else "HIGH")
        regression_probability = min(1.0, loop_count * 0.15)

        return {
            "lines_of_code": lines_of_code,
            "function_count": function_count,
            "complexity_score": round(complexity_score, 2),
            "resource_cost": resource_cost,
            "regression_probability": round(regression_probability, 2),
        }


impact_analyzer = ImpactAnalyzer()
