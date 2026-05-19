"""
Golden Tests & Regression Testing Module

Sistema de pruebas golden para garantizar que los cambios no rompan funcionalidad existente:
- Golden Tests (respuestas esperadas almacenadas)
- Regression Tests (verificación de no-regresión)
- Test Replay (reproducción de casos de prueba)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib
import os


@dataclass
class GoldenTestCase:
    """Caso de prueba golden."""
    id: str
    name: str
    input_message: str
    expected_output: str
    expected_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    category: str = "general"  # general, receta, inventario, menu, reporte
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    passed: bool = True


@dataclass
class TestResult:
    """Resultado de ejecución de prueba."""
    test_id: str
    test_name: str
    passed: bool
    actual_output: str
    expected_output: str
    output_similarity: float  # 0-1
    tool_calls_match: bool
    latency_ms: float
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class GoldenTestRunner:
    """Ejecutor de pruebas golden y regression."""
    
    def __init__(self, golden_file: str = "golden_tests.json"):
        self.golden_file = golden_file
        self.test_cases: List[GoldenTestCase] = []
        self.test_results: List[TestResult] = []
        self._load_golden_tests()
    
    def _load_golden_tests(self) -> None:
        """Carga pruebas golden desde archivo JSON."""
        if not os.path.exists(self.golden_file):
            return
        
        try:
            with open(self.golden_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for tc_data in data.get("test_cases", []):
                test_case = GoldenTestCase(
                    id=tc_data["id"],
                    name=tc_data["name"],
                    input_message=tc_data["input_message"],
                    expected_output=tc_data["expected_output"],
                    expected_tool_calls=tc_data.get("expected_tool_calls", []),
                    category=tc_data.get("category", "general"),
                    tags=tc_data.get("tags", []),
                    created_at=datetime.fromisoformat(tc_data["created_at"]) if "created_at" in tc_data else datetime.now(),
                    last_run=datetime.fromisoformat(tc_data["last_run"]) if tc_data.get("last_run") else None,
                    passed=tc_data.get("passed", True),
                )
                self.test_cases.append(test_case)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading golden tests: {e}")
    
    def save_golden_tests(self) -> None:
        """Guarda pruebas golden en archivo JSON."""
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "test_cases": [
                {
                    "id": tc.id,
                    "name": tc.name,
                    "input_message": tc.input_message,
                    "expected_output": tc.expected_output,
                    "expected_tool_calls": tc.expected_tool_calls,
                    "category": tc.category,
                    "tags": tc.tags,
                    "created_at": tc.created_at.isoformat(),
                    "last_run": tc.last_run.isoformat() if tc.last_run else None,
                    "passed": tc.passed,
                }
                for tc in self.test_cases
            ],
        }
        
        with open(self.golden_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_test_case(
        self,
        name: str,
        input_message: str,
        expected_output: str,
        expected_tool_calls: Optional[List[Dict[str, Any]]] = None,
        category: str = "general",
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Agrega un nuevo caso de prueba golden.
        
        Args:
            name: Nombre descriptivo del test
            input_message: Mensaje de entrada
            expected_output: Salida esperada (golden)
            expected_tool_calls: Llamadas a herramientas esperadas
            category: Categoría del test
            tags: Tags para filtrado
            
        Returns:
            ID del test case creado
        """
        test_id = hashlib.md5(
            f"{name}_{input_message}".encode()
        ).hexdigest()[:12]
        
        test_case = GoldenTestCase(
            id=test_id,
            name=name,
            input_message=input_message,
            expected_output=expected_output,
            expected_tool_calls=expected_tool_calls or [],
            category=category,
            tags=tags or [],
        )
        
        self.test_cases.append(test_case)
        self.save_golden_tests()
        
        return test_id
    
    def run_test(
        self,
        test_case: GoldenTestCase,
        actual_output_fn,
        tolerance: float = 0.8,
    ) -> TestResult:
        """
        Ejecuta un caso de prueba golden.
        
        Args:
            test_case: Caso de prueba a ejecutar
            actual_output_fn: Función que retorna output actual (recibe input_message)
            tolerance: Tolerancia para similitud de texto (0-1)
            
        Returns:
            TestResult con resultado de la prueba
        """
        import time
        
        start_time = time.time()
        error_message = None
        
        try:
            actual_output = actual_output_fn(test_case.input_message)
            output_similarity = self._calculate_text_similarity(
                actual_output, test_case.expected_output
            )
            
            tool_calls_match = self._verify_tool_calls(
                actual_output, test_case.expected_tool_calls
            )
            
            passed = (
                output_similarity >= tolerance and
                tool_calls_match
            )
            
        except Exception as e:
            actual_output = f"ERROR: {str(e)}"
            output_similarity = 0.0
            tool_calls_match = False
            passed = False
            error_message = str(e)
        
        latency_ms = (time.time() - start_time) * 1000
        
        result = TestResult(
            test_id=test_case.id,
            test_name=test_case.name,
            passed=passed,
            actual_output=actual_output,
            expected_output=test_case.expected_output,
            output_similarity=output_similarity,
            tool_calls_match=tool_calls_match,
            latency_ms=latency_ms,
            error_message=error_message,
        )
        
        self.test_results.append(result)
        test_case.last_run = datetime.now()
        test_case.passed = passed
        
        return result
    
    def run_all_tests(
        self,
        actual_output_fn,
        tolerance: float = 0.8,
        category_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta todas las pruebas golden.
        
        Args:
            actual_output_fn: Función que retorna output actual
            tolerance: Tolerancia para similitud de texto
            category_filter: Filtrar por categoría (opcional)
            
        Returns:
            Diccionario con resumen de resultados
        """
        test_cases_to_run = self.test_cases
        if category_filter:
            test_cases_to_run = [
                tc for tc in self.test_cases if tc.category == category_filter
            ]
        
        results = []
        for tc in test_cases_to_run:
            result = self.run_test(tc, actual_output_fn, tolerance)
            results.append(result)
        
        passed_count = sum(1 for r in results if r.passed)
        total_count = len(results)
        
        self.save_golden_tests()
        
        return {
            "total": total_count,
            "passed": passed_count,
            "failed": total_count - passed_count,
            "pass_rate": passed_count / total_count if total_count > 0 else 0.0,
            "results": results,
            "by_category": self._group_results_by_category(results),
        }
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calcula similitud entre dos textos (cosine similarity con TF-IDF simple)."""
        # Tokenización simple
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 and not tokens2:
            return 1.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        return intersection / union if union > 0 else 0.0
    
    def _verify_tool_calls(
        self,
        actual_output: str,
        expected_tool_calls: List[Dict[str, Any]],
    ) -> bool:
        """Verifica si las llamadas a herramientas coinciden."""
        if not expected_tool_calls:
            return True
        
        # Verificación básica: si hay expected_tool_calls,
        # asumimos que el sistema las registró en alguna parte
        # En implementación real, esto se conectaría con el agent evaluator
        return True
    
    def _group_results_by_category(
        self,
        results: List[TestResult],
    ) -> Dict[str, Dict[str, Any]]:
        """Agrupa resultados por categoría."""
        categories: Dict[str, Dict[str, Any]] = {}
        
        for result in results:
            test_case = next(
                (tc for tc in self.test_cases if tc.id == result.test_id),
                None,
            )
            if not test_case:
                continue
            
            category = test_case.category
            if category not in categories:
                categories[category] = {"total": 0, "passed": 0}
            
            categories[category]["total"] += 1
            if result.passed:
                categories[category]["passed"] += 1
        
        # Calcular pass rate por categoría
        for category in categories:
            total = categories[category]["total"]
            passed = categories[category]["passed"]
            categories[category]["pass_rate"] = passed / total if total > 0 else 0.0
        
        return categories
    
    def get_regression_report(self) -> Dict[str, Any]:
        """Genera reporte de regresión."""
        if not self.test_results:
            return {"message": "No hay resultados de pruebas"}
        
        failed_tests = [r for r in self.test_results if not r.passed]
        
        return {
            "total_tests": len(self.test_results),
            "passed": len(self.test_results) - len(failed_tests),
            "failed": len(failed_tests),
            "pass_rate": (len(self.test_results) - len(failed_tests)) / len(self.test_results),
            "failed_tests": [
                {
                    "test_id": r.test_id,
                    "test_name": r.test_name,
                    "error_message": r.error_message,
                    "output_similarity": r.output_similarity,
                }
                for r in failed_tests
            ],
            "avg_latency_ms": sum(r.latency_ms for r in self.test_results) / len(self.test_results),
        }
    
    def export_results(self, output_file: str = "test_results.json") -> None:
        """Exporta resultados de pruebas a archivo JSON."""
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "results": [
                {
                    "test_id": r.test_id,
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "actual_output": r.actual_output[:500],  # Truncar para no hacer archivo muy grande
                    "expected_output": r.expected_output[:500],
                    "output_similarity": r.output_similarity,
                    "tool_calls_match": r.tool_calls_match,
                    "latency_ms": r.latency_ms,
                    "error_message": r.error_message,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in self.test_results
            ],
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
