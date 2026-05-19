"""
RAG Evaluation Module

Métricas de evaluación para sistemas RAG:
- Faithfulness (Fidelidad)
- Context Precision (Precisión de contexto)
- Context Recall (Recall de contexto)
- Answer Relevance (Relevancia de respuesta)
- Hallucination Detection (Detección de alucinaciones)

Compatible con:
- RAGAS (Retrieval Augmented Generation Assessment)
- TruLens
- DeepEval
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re
import json


@dataclass
class RAGEvaluationResult:
    """Resultado de evaluación RAG."""
    faithfulness: float  # 0-1, qué tanto se basa la respuesta en el contexto
    context_precision: float  # 0-1, qué relevante es el contexto recuperado
    context_recall: float  # 0-1, qué tanto del contexto relevante se recuperó
    answer_relevance: float  # 0-1, qué relevante es la respuesta a la pregunta
    hallucination_score: float  # 0-1, probabilidad de alucinación (menor es mejor)
    overall_score: float  # Promedio ponderado


class RAGEvaluator:
    """Evaluador de sistemas RAG."""
    
    def __init__(self):
        self.evaluation_history: List[RAGEvaluationResult] = []
        
    def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> RAGEvaluationResult:
        """
        Evalúa una respuesta RAG.
        
        Args:
            question: Pregunta del usuario
            answer: Respuesta generada
            contexts: Contextos recuperados de la base de conocimiento
            ground_truth: Respuesta correcta (opcional, para cálculo de recall)
            
        Returns:
            RAGEvaluationResult con todas las métricas
        """
        faithfulness = self._calculate_faithfulness(answer, contexts)
        context_precision = self._calculate_context_precision(question, contexts)
        context_recall = self._calculate_context_recall(
            question, contexts, ground_truth
        ) if ground_truth else 0.0
        answer_relevance = self._calculate_answer_relevance(question, answer)
        hallucination_score = self._detect_hallucinations(answer, contexts)
        
        overall_score = (
            faithfulness * 0.25 +
            context_precision * 0.20 +
            context_recall * 0.20 +
            answer_relevance * 0.20 +
            (1 - hallucination_score) * 0.15
        )
        
        result = RAGEvaluationResult(
            faithfulness=faithfulness,
            context_precision=context_precision,
            context_recall=context_recall,
            answer_relevance=answer_relevance,
            hallucination_score=hallucination_score,
            overall_score=overall_score,
        )
        
        self.evaluation_history.append(result)
        return result
    
    def _calculate_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """
        Calcula qué tanto se basa la respuesta en los contextos proporcionados.
        
        Heurísticas:
        - Verifica si la información en la respuesta está en los contextos
        - Detecta afirmaciones no verificables
        - Penaliza información externa no presente en el contexto
        """
        if not contexts or not answer:
            return 0.0
        
        context_text = " ".join(contexts).lower()
        answer_sentences = self._split_sentences(answer)
        
        if not answer_sentences:
            return 0.0
        
        verified_count = 0
        for sentence in answer_sentences:
            if self._sentence_in_context(sentence.lower(), context_text):
                verified_count += 1
        
        return verified_count / len(answer_sentences)
    
    def _calculate_context_precision(
        self, 
        question: str, 
        contexts: List[str]
    ) -> float:
        """
        Calcula la precisión del contexto recuperado.
        
        Mide qué tan relevantes son los contextos para la pregunta.
        Usa overlap de palabras clave como proxy.
        """
        if not contexts or not question:
            return 0.0
        
        question_keywords = self._extract_keywords(question)
        
        precision_scores = []
        for context in contexts:
            context_keywords = self._extract_keywords(context)
            overlap = len(question_keywords & context_keywords)
            precision = overlap / len(question_keywords) if question_keywords else 0
            precision_scores.append(precision)
        
        return sum(precision_scores) / len(precision_scores) if precision_scores else 0.0
    
    def _calculate_context_recall(
        self,
        question: str,
        contexts: List[str],
        ground_truth: str,
    ) -> float:
        """
        Calcula el recall del contexto.
        
        Mide qué información de la ground_truth está presente en los contextos.
        """
        if not contexts or not ground_truth:
            return 0.0
        
        context_text = " ".join(contexts).lower()
        gt_keywords = self._extract_keywords(ground_truth)
        
        found_keywords = 0
        for keyword in gt_keywords:
            if keyword in context_text:
                found_keywords += 1
        
        return found_keywords / len(gt_keywords) if gt_keywords else 0.0
    
    def _calculate_answer_relevance(self, question: str, answer: str) -> float:
        """
        Calcula la relevancia de la respuesta para la pregunta.
        
        Verifica:
        - Overlap de keywords
        - Longitud apropiada de respuesta
        - Presencia de términos de la pregunta en la respuesta
        """
        if not question or not answer:
            return 0.0
        
        question_keywords = self._extract_keywords(question)
        answer_keywords = self._extract_keywords(answer)
        
        keyword_overlap = len(question_keywords & answer_keywords)
        keyword_score = keyword_overlap / max(len(question_keywords), 1)
        
        # Bonus si la respuesta contiene la pregunta o variaciones
        contains_question_bonus = 0.1 if question.lower() in answer.lower() else 0.0
        
        # Penalizar respuestas muy cortas o muy largas
        answer_len = len(answer.split())
        if answer_len < 5:
            length_penalty = 0.8
        elif answer_len > 500:
            length_penalty = 0.9
        else:
            length_penalty = 1.0
        
        return min(1.0, (keyword_score + contains_question_bonus) * length_penalty)
    
    def _detect_hallucinations(self, answer: str, contexts: List[str]) -> float:
        """
        Detecta posibles alucinaciones en la respuesta.
        
        Retorna score 0-1 donde 1 es alta probabilidad de alucinación.
        """
        if not contexts or not answer:
            return 0.5
        
        context_text = " ".join(contexts).lower()
        
        # Patrones que indican posible alucinación
        hallucination_patterns = [
            r"según.*estudios?",
            r"investigaciones?.*demuestran",
            r"expertos.*afirman",
            r"datos.*muestran que",
            r"porcentaje.*%",
            r"\d{4}.*año",
        ]
        
        hallucination_indicators = 0
        for pattern in hallucination_patterns:
            if re.search(pattern, answer.lower()):
                matches = re.findall(pattern, answer.lower())
                for match in matches:
                    if match not in context_text:
                        hallucination_indicators += 1
        
        # Entidades nombradas no presentes en contexto
        answer_entities = set(re.findall(r'\b[A-Z][a-z]+\b', answer))
        context_entities = set(re.findall(r'\b[A-Z][a-z]+\b', " ".join(contexts)))
        unknown_entities = answer_entities - context_entities
        
        entity_penalty = len(unknown_entities) / max(len(answer_entities), 1)
        
        return min(1.0, (hallucination_indicators * 0.1) + (entity_penalty * 0.5))
    
    def _split_sentences(self, text: str) -> List[str]:
        """Divide texto en oraciones."""
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _sentence_in_context(self, sentence: str, context: str) -> bool:
        """Verifica si una oración (o sus keywords) están en el contexto."""
        keywords = self._extract_keywords(sentence)
        if not keywords:
            return False
        
        matches = sum(1 for kw in keywords if kw in context)
        return matches >= len(keywords) * 0.5
    
    def _extract_keywords(self, text: str) -> set:
        """Extrae palabras clave de un texto."""
        stop_words = {
            "el", "la", "los", "las", "un", "una", "unos", "unas",
            "de", "del", "al", "en", "con", "sin", "para", "por",
            "que", "se", "lo", "le", "la", "las", "los",
            "es", "son", "ser", "estar", "esta", "este",
            "y", "o", "pero", "porque", "como", "cuando",
            "su", "sus", "mi", "mis", "tu", "tus",
            "a", "ante", "bajo", "cabe", "contra", "desde",
            "entre", "hacia", "hasta", "para", "según", "sobre", "tras",
        }
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = {w for w in words if w not in stop_words and len(w) > 2}
        return keywords
    
    def get_summary(self) -> Dict[str, float]:
        """Obtiene resumen estadístico de evaluaciones."""
        if not self.evaluation_history:
            return {}
        
        n = len(self.evaluation_history)
        return {
            "total_evaluations": n,
            "avg_faithfulness": sum(r.faithfulness for r in self.evaluation_history) / n,
            "avg_context_precision": sum(r.context_precision for r in self.evaluation_history) / n,
            "avg_context_recall": sum(r.context_recall for r in self.evaluation_history) / n,
            "avg_answer_relevance": sum(r.answer_relevance for r in self.evaluation_history) / n,
            "avg_hallucination_score": sum(r.hallucination_score for r in self.evaluation_history) / n,
            "avg_overall_score": sum(r.overall_score for r in self.evaluation_history) / n,
        }
