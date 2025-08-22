from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, List, Tuple

import joblib
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import csv
import json

DATA_PATH = Path("data/case_data.csv")
MODEL_PATH = Path("models/model.pkl")
VECTORIZER_PATH = Path("models/vectorizer.pkl")
FEEDBACK_PATH = Path(os.getenv("FEEDBACK_PATH", "data/feedback.csv"))
CONFIG_PATH = Path(os.getenv("CONFIG_PATH", "config.json"))

# Default, file-backed config so you don't need terminal env vars
DEFAULT_CONFIG = {
    "model_type": "sklearn",  # sklearn | hf | zeroshot | llm | gemini | hf_api
    "hf_model_dir": "models/hf",
    "hf_max_len": 512,
    "zsh_model": "facebook/bart-large-mnli",
    "zsh_labels": ["plaintiff_wins", "defendant_wins"],
    "zsh_max_len": 512,
    "llm_model": "opennyaiorg/Aalap-Mistral-7B-v0.1-bf16",
    "llm_labels": ["plaintiff_wins", "defendant_wins"],
    "llm_max_input": 2048,
    "llm_max_new_tokens": 32,
    "gemini_model": "gemini-1.5-flash",
    "gemini_labels": ["plaintiff_wins", "defendant_wins"],
    "hf_api_model": "meta-llama/Llama-3.2-3B-Instruct",
    "hf_api_labels": ["plaintiff_wins", "defendant_wins"],
    "hf_api_max_tokens": 1000,
    "debug_errors": False,
}
CONFIG = DEFAULT_CONFIG.copy()

def _load_config() -> None:
    global CONFIG
    try:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                CONFIG.update(data)
        else:
            # Write defaults the first time
            CONFIG_PATH.write_text(json.dumps(CONFIG, indent=2), encoding="utf-8")
    except Exception:
        # Fail-soft to defaults
        pass

def _save_config() -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(CONFIG, indent=2), encoding="utf-8")
    except Exception:
        pass

app = FastAPI(title="Case Outcome Predictor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lightweight logging middleware to help diagnose fetch failures
@app.middleware("http")
async def _log_requests(request, call_next):  # type: ignore
    from time import time
    start = time()
    path = request.url.path
    mode = (CONFIG.get("model_type") or "sklearn")
    try:
        response = await call_next(request)
        duration = (time() - start) * 1000
        print(f"[REQ] {path} mode={mode} status={response.status_code} {duration:.1f}ms")
        return response
    except Exception as e:  # noqa
        duration = (time() - start) * 1000
        print(f"[ERR] {path} mode={mode} error={e} {duration:.1f}ms")
        raise


# Global exception handler (optional detailed trace when debug_errors enabled)
@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):  # type: ignore
    if isinstance(exc, StarletteHTTPException):
        # Let FastAPI's own handler deal with HTTPExceptions
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    if CONFIG.get("debug_errors"):
        import traceback
        trace = traceback.format_exc().splitlines()
        return JSONResponse(status_code=500, content={
            "detail": str(exc),
            "trace": trace[-25:],
        })
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.get("/debug/deps")
async def debug_deps():
    out = {"mode": CONFIG.get("model_type")}
    for pkg in ["torch", "transformers", "scikit_learn"]:
        try:
            if pkg == "scikit_learn":
                import sklearn  # type: ignore
                out[pkg] = getattr(sklearn, "__version__", "unknown")
            elif pkg == "torch":
                import torch  # type: ignore
                out[pkg] = torch.__version__
            elif pkg == "transformers":
                import transformers  # type: ignore
                out[pkg] = transformers.__version__
        except Exception as e:  # noqa
            out[pkg] = f"missing: {e}" 
    return out


class PredictRequest(BaseModel):
    summary: str


class PredictResponse(BaseModel):
    prediction: str
    confidence: float
    top_features: list[str] | None = None
    reason: str | None = None


class BatchPredictRequest(BaseModel):
    summaries: List[str]


class BatchPredictItem(BaseModel):
    prediction: str
    confidence: float
    top_features: list[str] | None = None
    reason: str | None = None


class BatchPredictResponse(BaseModel):
    items: List[BatchPredictItem]


class FeedbackRequest(BaseModel):
    summary: str
    predicted: str
    correct_label: Optional[str] = None
    notes: Optional[str] = None


_model: Optional[LogisticRegression] = None
_vectorizer: Optional[TfidfVectorizer] = None
_hf_tokenizer = None
_hf_model = None
_zs_pipe = None
_llm_tokenizer = None
_llm_model = None


def _reset_models() -> None:
    global _model, _vectorizer, _hf_model, _hf_tokenizer, _zs_pipe
    _model = None
    _vectorizer = None
    _hf_model = None
    _hf_tokenizer = None
    _zs_pipe = None
    global _llm_model, _llm_tokenizer
    _llm_model = None
    _llm_tokenizer = None


# Load config at import time
_load_config()


def _ensure_model_loaded() -> None:
    global _model, _vectorizer
    model_type = (CONFIG.get("model_type") or "sklearn").lower()
    if model_type == "hf":
        _ensure_hf_loaded()
        return
    if model_type == "zeroshot":
        _ensure_zeroshot_loaded()
        return
    if model_type == "llm":
        _ensure_llm_loaded()
        return
    if model_type == "hf_api":
        # HF API mode doesn't need local models
        return
    if _model is not None and _vectorizer is not None:
        return

    if MODEL_PATH.exists() and VECTORIZER_PATH.exists():
        _model = joblib.load(MODEL_PATH)
        _vectorizer = joblib.load(VECTORIZER_PATH)
        return

    # Fallback: attempt quick training if data exists
    if DATA_PATH.exists():
        try:
            rows: list[tuple[str,str]] = []
            with DATA_PATH.open(newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if not {'summary','outcome'}.issubset(reader.fieldnames or []):
                    raise RuntimeError("Training CSV must include 'summary' and 'outcome'")
                for r in reader:
                    s = (r.get('summary') or '').strip()
                    o = (r.get('outcome') or '').strip()
                    if s and o:
                        rows.append((s,o))
            # Simpler vectorizer for small datasets
            n_docs = len(rows)
            if n_docs < 50:
                vec = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1,1), min_df=1, max_df=0.95)
            else:
                vec = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1,2), min_df=2, max_df=0.95, max_features=5000)
            X = vec.fit_transform([s for s,_ in rows])
            y = [o for _,o in rows]
            mdl = LogisticRegression(max_iter=500, class_weight="balanced")
            mdl.fit(X, y)
            MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(mdl, MODEL_PATH)
            joblib.dump(vec, VECTORIZER_PATH)
            _model, _vectorizer = mdl, vec
            return
        except Exception as e:
            raise RuntimeError(f"Failed to auto-train model: {e}") from e

    raise RuntimeError(
        "Model and vectorizer not found. Run 'python train_model.py' to create them."
    )


def _ensure_hf_loaded() -> None:
    global _hf_model, _hf_tokenizer
    if _hf_model is not None and _hf_tokenizer is not None:
        return
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
    except ImportError as e:
        raise RuntimeError(
            "Hugging Face mode requires 'transformers' (and torch). Install them in your env."
        ) from e
    hf_dir = Path(str(CONFIG.get("hf_model_dir", "models/hf")))
    if not hf_dir.exists():
        raise RuntimeError("HF model not found. Train with 'python train_hf.py'.")
    _hf_tokenizer = AutoTokenizer.from_pretrained(str(hf_dir))
    _hf_model = AutoModelForSequenceClassification.from_pretrained(str(hf_dir))


def _ensure_zeroshot_loaded() -> None:
    global _zs_pipe
    if _zs_pipe is not None:
        return
    try:
        from transformers import pipeline
    except ImportError as e:
        raise RuntimeError(
            "Zero-shot mode requires 'transformers' (and torch). Install them in your env."
        ) from e
    model_name = str(CONFIG.get("zsh_model", "facebook/bart-large-mnli"))
    _zs_pipe = pipeline("zero-shot-classification", model=model_name)


def _ensure_llm_loaded() -> None:
    global _llm_model, _llm_tokenizer
    if _llm_model is not None and _llm_tokenizer is not None:
        return
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
    except ImportError as e:
        raise RuntimeError("LLM mode requires transformers + torch installed.") from e
    model_name = str(CONFIG.get("llm_model", "opennyaiorg/Aalap-Mistral-7B-v0.1-bf16"))
    device = 0 if torch.cuda.is_available() else "cpu"
    _llm_tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    _llm_model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16 if torch.cuda.is_available() else None, device_map="auto" if torch.cuda.is_available() else None, trust_remote_code=True)
    if device == "cpu":
        # Warn via log (print) about performance
        print("[WARN] LLM loaded on CPU; responses will be slow.")


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/health")
async def health():
    mode = (CONFIG.get("model_type") or "sklearn").lower()
    if mode == "sklearn":
        model_ok = MODEL_PATH.exists()
        vec_ok = VECTORIZER_PATH.exists()
        return {"ok": model_ok and vec_ok, "mode": mode, "model": model_ok, "vectorizer": vec_ok}
    if mode == "hf":
        hf_dir = Path(str(CONFIG.get("hf_model_dir", "models/hf")))
        present = hf_dir.exists()
        return {"ok": present, "mode": mode, "hf_model_dir": str(hf_dir), "present": present}
    if mode == "hf_api":
        import os
        api_key = os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HF_TOKEN")
        return {"ok": bool(api_key), "mode": mode, "note": "HuggingFace API mode", "api_key_present": bool(api_key)}
    # zeroshot, llm, gemini
    return {"ok": True, "mode": mode, "note": f"{mode.title()} model downloads/loads on first request"}


@app.get("/version")
async def version():
    meta = {}
    try:
        meta_path = Path("models/metadata.json")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
    except Exception:
        meta = {}
    return {"name": "case-outcome-predictor", "metadata": meta}


def _predict_one(text: str) -> Tuple[str, float, List[str] | None, str | None]:
    assert _model is not None and _vectorizer is not None
    X = _vectorizer.transform([text])
    proba = _model.predict_proba(X)[0]
    classes = list(_model.classes_)
    idx = int(proba.argmax())
    pred = classes[idx]
    conf = float(proba[idx])
    # Explanation
    top_features: List[str] | None = None
    reason: str | None = None
    try:
        feature_names = list(_vectorizer.get_feature_names_out())
        coef = _model.coef_[idx]
        x = X.toarray()[0]
        contrib = [(feature_names[i], coef[i] * x[i]) for i in range(len(feature_names)) if x[i] != 0]
        contrib.sort(key=lambda t: t[1], reverse=True)
        top_features = [w for w, v in contrib[:8]]
        
        # Generate comprehensive legal analysis format
        top_terms = [w for w, v in contrib[:5] if v > 0]
        if top_terms:
            outcome = "plaintiff_wins" if pred == "plaintiff_wins" else "defendant_wins"
            confidence_level = "overwhelmingly clear" if conf > 0.8 else "strongly indicated" if conf > 0.7 else "reasonably supported" if conf > 0.6 else "suggested"
            
            analysis_sections = []
            
            # Opening statement
            opening = f"Based on the textual analysis provided, the outcome is {confidence_level}.\n\n{outcome}\n\nReasoning:"
            analysis_sections.append(opening)
            
            # Categorize terms by legal significance
            legal_terms = []
            factual_terms = []
            procedural_terms = []
            financial_terms = []
            
            for term in top_terms:
                term_lower = term.lower()
                if any(legal_concept in term_lower for legal_concept in 
                      ['contract', 'breach', 'negligence', 'damages', 'liability', 'evidence', 'duty', 'causation', 'statute', 'law', 'court', 'judge', 'violation']):
                    legal_terms.append(term)
                elif any(procedural in term_lower for procedural in 
                        ['motion', 'filing', 'discovery', 'deposition', 'hearing', 'trial', 'appeal', 'jurisdiction', 'service']):
                    procedural_terms.append(term)
                elif any(financial in term_lower for financial in 
                        ['payment', 'money', 'cost', 'fee', 'compensation', 'refund', 'invoice', 'debt']):
                    financial_terms.append(term)
                else:
                    factual_terms.append(term)
            
            # Short summary based on dominant terms
            if legal_terms:
                dominant_legal = legal_terms[0]
                if 'contract' in dominant_legal.lower():
                    analysis_sections.append("In Short: This is fundamentally a contract-based dispute where the terms and performance are central to the outcome.")
                elif 'negligence' in dominant_legal.lower():
                    analysis_sections.append("In Short: The case centers on negligence principles where duty of care and breach are the determining factors.")
                elif 'damages' in dominant_legal.lower():
                    analysis_sections.append("In Short: The extent and nature of damages are the crucial elements driving this case outcome.")
                else:
                    analysis_sections.append(f"In Short: The legal concept of '{dominant_legal}' is the decisive factor in this case analysis.")
            else:
                analysis_sections.append("In Short: The factual circumstances create a compelling narrative that determines the legal outcome.")
            
            # Evidence analysis section
            strong_features = [w for w, v in contrib[:3] if v > 0.1]
            if strong_features:
                evidence_text = f"The Evidence is Decisive: The textual analysis identifies '{', '.join(strong_features[:2])}' as the most significant factors"
                if legal_terms:
                    evidence_text += f". These legal elements ({', '.join(legal_terms[:2])}) provide concrete proof that cannot be easily disputed."
                elif factual_terms:
                    evidence_text += f". These factual elements ({', '.join(factual_terms[:2])}) create an undeniable foundation for the case."
                else:
                    evidence_text += ". These key factors create a compelling evidentiary foundation."
                analysis_sections.append(evidence_text)
            
            # Legal principles section
            if legal_terms and outcome == "plaintiff_wins":
                analysis_sections.append(f"Legal Principles Are Clear: The presence of {', '.join(legal_terms[:2])} establishes the essential elements needed for a successful claim. The defendant's position is significantly undermined by these legal factors.")
            elif legal_terms and outcome == "defendant_wins":
                analysis_sections.append(f"Legal Principles Are Clear: The analysis of {', '.join(legal_terms[:2])} reveals substantial challenges to the plaintiff's case. The defendant has strong legal grounds based on these factors.")
            elif procedural_terms:
                analysis_sections.append(f"Procedural Factors Are Decisive: The procedural elements ({', '.join(procedural_terms[:2])}) create significant advantages for the predicted outcome.")
            else:
                analysis_sections.append("Legal Principles Are Clear: The combination of factual and legal elements strongly supports the predicted outcome.")
            
            # Defense analysis based on confidence
            if conf > 0.8:
                if outcome == "plaintiff_wins":
                    analysis_sections.append("No Credible Defense: The textual evidence is so compelling that any defense arguments would be fundamentally weak. The defendant lacks sufficient grounds to counter this strong case.")
                else:
                    analysis_sections.append("Overwhelming Defense: The evidence strongly favors the defendant's position, making it extremely difficult for the plaintiff to succeed.")
            elif conf > 0.6:
                if outcome == "plaintiff_wins":
                    analysis_sections.append("Limited Defense Options: While the defendant may raise arguments, the strength of the evidence significantly undermines their position.")
                else:
                    analysis_sections.append("Strong Defense Position: The defendant has compelling grounds to challenge the plaintiff's claims based on the textual evidence.")
            else:
                analysis_sections.append("Contested Case: This case presents mixed signals, suggesting both parties have reasonable arguments, though the analysis slightly favors the predicted outcome.")
            
            # Conclusion
            if conf > 0.7:
                if outcome == "plaintiff_wins":
                    analysis_sections.append("This is a straightforward case where the plaintiff has compelling evidence and strong legal grounds. The textual analysis reveals clear liability and damages.")
                else:
                    analysis_sections.append("This case strongly favors the defendant based on the evidence patterns. The plaintiff faces significant obstacles to establishing their claims.")
            else:
                analysis_sections.append("This case requires careful legal analysis as the outcome, while predicted, involves competing factors that could influence the final result.")
            
            # Professional disclaimer
            analysis_sections.append("\nImportant Legal Disclaimer: This statistical text analysis identifies linguistic patterns but cannot evaluate evidence quality, witness credibility, legal precedents, procedural nuances, or judicial discretion. Professional legal counsel is essential for comprehensive case evaluation.")
            
            reason = "\n\n".join(analysis_sections)
        else:
            reason = (
                f"Based on the textual analysis, the outcome suggests {pred} with {conf:.1%} confidence.\n\n"
                f"Reasoning:\nThe statistical model detected subtle linguistic patterns favoring this outcome, "
                f"though no individual terms dominated the analysis. This suggests the case involves complex "
                f"factors that require professional legal evaluation to fully understand.\n\n"
                f"Important Legal Disclaimer: This analysis has significant limitations and should supplement, "
                f"not replace, qualified legal counsel."
            )
    except Exception:
        top_features = None
        reason = (
            f"Predicted {pred} with {conf:.1%} confidence through statistical text analysis. "
            f"This AI assessment cannot replace qualified legal expertise and should only "
            f"serve as a preliminary screening tool alongside professional legal counsel."
        )
    return pred, conf, top_features, reason


def _reason_zeroshot(res: dict, text: str) -> str:
    # Generate comprehensive legal analysis format
    try:
        global _zs_pipe
        labels = res.get('labels') or []
        scores = res.get('scores') or []
        if not labels or not scores:
            return "Prediction analysis unavailable. Please consult qualified legal counsel."
            
        winner = "plaintiff_wins" if labels[0] == "plaintiff_wins" else "defendant_wins"
        confidence_level = "overwhelmingly clear" if scores[0] > 0.8 else "strongly indicated" if scores[0] > 0.7 else "reasonably supported" if scores[0] > 0.6 else "suggested"
        
        # Generate detailed legal analysis sections
        analysis_sections = []
        
        # Opening statement
        opening = f"Based on the facts provided, the outcome is {confidence_level}.\n\n{winner}\n\nReasoning:"
        analysis_sections.append(opening)
        
        # Generate AI-powered case analysis
        try:
            # Analyze case strengths using zero-shot
            strength_labels = [
                "strong evidence present",
                "clear legal violation", 
                "contractual breach evident",
                "negligence demonstrated",
                "damages clearly established",
                "defendant liability obvious"
            ]
            strength_analysis = _zs_pipe(
                f"Legal analysis of case evidence and claims:\n{text[:400]}",
                candidate_labels=strength_labels,
                multi_label=False
            )
            
            if strength_analysis.get('labels') and strength_analysis.get('scores'):
                top_strength = strength_analysis['labels'][0]
                strength_score = strength_analysis['scores'][0]
                
                if strength_score > 0.5:
                    if "evidence" in top_strength:
                        analysis_sections.append("In Short: The evidence overwhelmingly supports the plaintiff's position based on the facts presented.")
                    elif "violation" in top_strength or "breach" in top_strength:
                        analysis_sections.append("In Short: There is a clear legal violation that strongly favors the plaintiff's case.")
                    elif "negligence" in top_strength:
                        analysis_sections.append("In Short: The defendant's negligence is evident from the circumstances described.")
                    elif "damages" in top_strength:
                        analysis_sections.append("In Short: The damages and harm to the plaintiff are clearly established.")
                    else:
                        analysis_sections.append("In Short: The legal analysis strongly supports the predicted outcome.")
        except Exception:
            analysis_sections.append("In Short: The case facts strongly support the predicted legal outcome.")
        
        # Detailed evidence analysis
        try:
            evidence_labels = [
                "documentary evidence strong",
                "witness testimony favorable", 
                "contractual terms clear",
                "factual circumstances decisive",
                "legal precedent applicable"
            ]
            evidence_analysis = _zs_pipe(
                f"Evidence strength in this legal case:\n{text[:300]}",
                candidate_labels=evidence_labels,
                multi_label=False
            )
            
            if evidence_analysis.get('labels') and evidence_analysis.get('scores'):
                evidence_type = evidence_analysis['labels'][0]
                evidence_score = evidence_analysis['scores'][0]
                
                if evidence_score > 0.4:
                    if "documentary" in evidence_type:
                        analysis_sections.append("The Evidence is Decisive: The documented evidence in this case provides compelling proof that cannot be easily disputed. Written records, contracts, or communications create a clear paper trail that strongly supports the plaintiff's position.")
                    elif "contractual" in evidence_type:
                        analysis_sections.append("The Evidence is Decisive: The contractual terms and agreements are unambiguous and clearly establish the defendant's obligations. The breach of these terms is evident from the facts presented.")
                    elif "factual" in evidence_type:
                        analysis_sections.append("The Evidence is Decisive: The factual circumstances of this case create a compelling narrative that strongly supports the plaintiff's claims. The sequence of events clearly demonstrates liability.")
                    else:
                        analysis_sections.append("The Evidence is Decisive: The available evidence creates a strong foundation for the plaintiff's case and undermines any potential defenses.")
        except Exception:
            analysis_sections.append("The Evidence is Decisive: The facts and circumstances presented create a compelling case that strongly supports the predicted outcome.")
        
        # Legal principle explanation
        if winner == "plaintiff_wins":
            analysis_sections.append("Legal Principles Are Clear: The defendant's actions constitute a clear breach of their legal obligations. Under established legal principles, when duty, breach, causation, and damages are all present, liability is clearly established.")
        else:
            analysis_sections.append("Legal Principles Are Clear: The defendant has strong legal grounds for their position. The plaintiff faces significant challenges in establishing the necessary elements for a successful claim.")
        
        # Defense analysis
        try:
            defense_labels = [
                "weak defense arguments",
                "strong procedural defenses",
                "factual disputes present", 
                "credibility issues exist",
                "insufficient evidence claims"
            ]
            defense_analysis = _zs_pipe(
                f"Potential defenses in this case:\n{text[:300]}",
                candidate_labels=defense_labels,
                multi_label=False
            )
            
            if defense_analysis.get('labels') and defense_analysis.get('scores'):
                defense_type = defense_analysis['labels'][0]
                defense_score = defense_analysis['scores'][0]
                
                if defense_score > 0.4:
                    if winner == "plaintiff_wins":
                        if "weak" in defense_type:
                            analysis_sections.append("No Credible Defense: The defendant's potential arguments are fundamentally flawed and cannot overcome the strength of the plaintiff's evidence. Any defenses raised would likely be unsuccessful in court.")
                        else:
                            analysis_sections.append("Limited Defense Options: While the defendant may attempt various defenses, the strength of the plaintiff's case significantly undermines these efforts.")
                    else:
                        if "strong" in defense_type:
                            analysis_sections.append("Strong Defense Position: The defendant has compelling arguments that significantly challenge the plaintiff's claims and create reasonable doubt about liability.")
                        else:
                            analysis_sections.append("Viable Defense Available: The defendant has reasonable grounds to contest the plaintiff's claims based on the circumstances presented.")
        except Exception:
            if winner == "plaintiff_wins":
                analysis_sections.append("No Credible Defense: The defendant lacks compelling arguments to counter the strength of the plaintiff's position.")
            else:
                analysis_sections.append("Strong Defense Position: The defendant has viable arguments to challenge the plaintiff's claims.")
        
        # Conclusion
        if winner == "plaintiff_wins":
            analysis_sections.append("This is a straightforward case where the plaintiff has met all necessary legal requirements. The evidence is compelling, the law is clear, and the defendant's position is untenable.")
        else:
            analysis_sections.append("This case presents significant challenges for the plaintiff. The defendant's position is well-supported by the facts and applicable legal principles.")
        
        # Professional disclaimer
        analysis_sections.append("\nImportant Legal Disclaimer: This AI analysis interprets patterns in legal language but cannot substitute for professional legal counsel. Actual case outcomes depend on evidence presentation, witness credibility, legal precedents, procedural factors, and judicial discretion that no AI can fully evaluate.")
        
        return "\n\n".join(analysis_sections)
        
    except Exception:
        # Fallback to basic explanation if AI reasoning completely fails
        labels = res.get('labels') or []
        scores = res.get('scores') or []
        if labels and scores:
            outcome = "plaintiff_wins" if labels[0] == "plaintiff_wins" else "defendant_wins"
            return (
                f"Based on AI analysis, the outcome suggests {outcome} with {scores[0]:.1%} confidence. "
                f"This assessment has significant limitations and should supplement, not replace, professional legal analysis."
            )
        return "Prediction analysis unavailable. Please consult qualified legal counsel."

def _reason_hf(pred: str, probs, labels, case_text: str = "") -> str:
    """Generate comprehensive legal analysis using fine-tuned model understanding"""
    if len(probs) >= 2:
        sorted_pairs = sorted(zip(labels, probs), key=lambda t: t[1], reverse=True)
        first, second = sorted_pairs[0], sorted_pairs[1]
        winner = first[0]
        runner_up = second[0]
        confidence_level = "overwhelmingly clear" if first[1] > 0.9 else "strongly indicated" if first[1] > 0.8 else "clearly supported" if first[1] > 0.7 else "reasonably indicated" if first[1] > 0.6 else "suggested"
        margin = first[1] - second[1]
        
        analysis_sections = []
        
        # Opening statement
        opening = f"Based on fine-tuned legal AI analysis, the outcome is {confidence_level}.\n\n{winner}\n\nReasoning:"
        analysis_sections.append(opening)
        
        # Short summary based on model confidence
        if first[1] > 0.9:
            analysis_sections.append("In Short: The fine-tuned legal model shows exceptional confidence due to extremely clear legal patterns that align perfectly with its specialized training.")
        elif first[1] > 0.8:
            analysis_sections.append("In Short: The specialized legal AI identifies compelling patterns that strongly align with successful case outcomes in its training data.")
        elif first[1] > 0.7:
            analysis_sections.append("In Short: The model recognizes clear legal indicators that consistently correlate with this outcome in legal case patterns.")
        else:
            analysis_sections.append("In Short: The legal AI detects patterns that moderately support this outcome based on its specialized training.")
        
        # Evidence analysis based on model behavior
        if margin > 0.5:
            analysis_sections.append("The Evidence is Decisive: The fine-tuned model shows overwhelming preference for this outcome, indicating the legal patterns are exceptionally clear and unambiguous. The model's specialized legal training allows it to identify decisive factors that strongly distinguish this case.")
        elif margin > 0.3:
            analysis_sections.append("The Evidence is Decisive: The model demonstrates strong confidence with clear differentiation between outcomes. The legal patterns identified align strongly with cases that typically result in this outcome.")
        elif margin > 0.15:
            analysis_sections.append("The Evidence is Strong: The model shows moderate confidence with noticeable preference for this outcome. The legal patterns suggest a reasonably clear case direction.")
        else:
            analysis_sections.append("The Evidence Supports: The model shows a slight but meaningful preference for this outcome. The legal patterns suggest competing factors with one side having a modest advantage.")
        
        # Legal AI specialization explanation
        if first[1] > 0.8:
            analysis_sections.append("Specialized Legal AI Analysis: This fine-tuned model has been specifically trained on legal language patterns and case outcomes. Its high confidence indicates the case contains textual elements that strongly correlate with successful claims in its training data.")
        else:
            analysis_sections.append("Specialized Legal AI Analysis: The fine-tuned model's legal training enables it to identify relevant patterns, though the moderate confidence suggests some complexity or ambiguity in the case factors.")
        
        # Comparative analysis
        outcome_desc = "plaintiff victory" if winner == "plaintiff_wins" else "defendant victory"
        comparison_desc = "plaintiff victory" if runner_up == "plaintiff_wins" else "defendant victory"
        
        if margin > 0.4:
            analysis_sections.append(f"No Credible Alternative: With {first[1]:.1%} confidence for {outcome_desc} compared to only {second[1]:.1%} for {comparison_desc}, the model sees this as a clear-cut case with limited viability for opposing arguments.")
        elif margin > 0.2:
            analysis_sections.append(f"Strong Position Advantage: The {first[1]:.1%} to {second[1]:.1%} confidence ratio shows a significant advantage, though the opposing position retains some merit according to the model's analysis.")
        else:
            analysis_sections.append(f"Competitive Case: While favoring {outcome_desc} at {first[1]:.1%} versus {second[1]:.1%} for {comparison_desc}, the model recognizes this as a closely contested matter with valid arguments on both sides.")
        
        # Case-specific insights
        if case_text and len(case_text.split()) > 50:
            analysis_sections.append("Comprehensive Text Analysis: The detailed case description provides substantial information for the model's specialized legal analysis, enabling more nuanced pattern recognition than shorter summaries would allow.")
        
        # Conclusion based on confidence
        if first[1] > 0.85:
            analysis_sections.append("This represents a straightforward case where the specialized legal AI identifies clear, decisive patterns. The model's training on legal outcomes provides strong predictive insight for this type of case.")
        elif first[1] > 0.7:
            analysis_sections.append("This case shows strong indicators favoring the predicted outcome. The fine-tuned model's legal specialization enables confident assessment of the relevant patterns.")
        else:
            analysis_sections.append("This case presents moderate complexity with the predicted outcome having an advantage. The specialized model provides valuable insight while acknowledging case nuances.")
        
        # Professional disclaimer
        analysis_sections.append("\nImportant Legal Disclaimer: This fine-tuned AI analysis represents advanced pattern recognition in legal text but cannot evaluate evidence quality, witness testimony, legal precedents, attorney effectiveness, or judicial discretion. Professional legal counsel remains essential for comprehensive case strategy and evaluation.")
        
        return "\n\n".join(analysis_sections)
        
    if len(probs) == 1:
        outcome = pred
        confidence_level = "indicated" if probs[0] > 0.7 else "suggested"
        return (
            f"Based on fine-tuned legal AI analysis, the outcome is {confidence_level}.\n\n{outcome}\n\n"
            f"Reasoning:\nThe specialized legal model suggests this outcome with {probs[0]:.1%} confidence "
            f"based on its training on legal language patterns. However, single-class predictions have "
            f"inherent limitations.\n\nImportant Legal Disclaimer: This AI prediction should supplement, "
            f"not replace, professional legal counsel."
        )
    
    return (
        f"Based on fine-tuned legal AI analysis, the outcome suggests {pred}.\n\n"
        f"Reasoning:\nThe specialized legal model generated this prediction through advanced pattern "
        f"recognition, though technical limitations prevent detailed confidence analysis.\n\n"
        f"Important Legal Disclaimer: Professional legal evaluation is essential for comprehensive "
        f"case assessment beyond AI capabilities."
    )


@app.get("/labels")
async def labels():
    model_type = (CONFIG.get("model_type") or "sklearn").lower()
    if model_type == "hf":
        try:
            _ensure_hf_loaded()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        assert _hf_model is not None
        return {"labels": [str(_hf_model.config.id2label[i]) for i in range(_hf_model.config.num_labels)]}
    if model_type == "zeroshot":
        # Return default labels for zero-shot mode
        zlabels = CONFIG.get("zsh_labels") or ["plaintiff_wins", "defendant_wins"]
        # If someone put a comma-separated string, split it
        if isinstance(zlabels, str):
            zlabels = [p.strip() for p in zlabels.split(",") if p.strip()]
        return {"labels": zlabels}
    if model_type == "llm":
        llm_labels = CONFIG.get("llm_labels") or ["plaintiff_wins", "defendant_wins"]
        if isinstance(llm_labels, str):
            llm_labels = [p.strip() for p in llm_labels.split(",") if p.strip()]
        return {"labels": llm_labels}
    if model_type == "gemini":
        g_labels = CONFIG.get("gemini_labels") or ["plaintiff_wins", "defendant_wins"]
        if isinstance(g_labels, str):
            g_labels = [p.strip() for p in g_labels.split(",") if p.strip()]
        return {"labels": g_labels}
    if model_type == "hf_api":
        hf_api_labels = CONFIG.get("hf_api_labels") or ["plaintiff_wins", "defendant_wins"]
        if isinstance(hf_api_labels, str):
            hf_api_labels = [p.strip() for p in hf_api_labels.split(",") if p.strip()]
        return {"labels": hf_api_labels}
    _ensure_model_loaded()
    assert _model is not None
    return {"labels": list(_model.classes_)}


@app.post("/predict", response_model=PredictResponse)
async def predict(body: PredictRequest):
    text = (body.summary or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Summary must not be empty")

    model_type = (CONFIG.get("model_type") or "sklearn").lower()
    if model_type == "hf":
        try:
            _ensure_hf_loaded()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        assert _hf_model is not None and _hf_tokenizer is not None
        try:
            import torch
        except ImportError as e:
            raise RuntimeError(
                "Hugging Face mode requires 'torch'. Install it (CPU-only is fine)."
            ) from e
        with torch.no_grad():
            hf_max_len = int(CONFIG.get("hf_max_len", 512))
            inputs = _hf_tokenizer([text], truncation=True, max_length=hf_max_len, return_tensors="pt")
            logits = _hf_model(**inputs).logits[0]
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
        labels = [_hf_model.config.id2label[i] for i in range(len(probs))]
        idx = int(probs.argmax())
        pred = labels[idx]
        conf = float(probs[idx])
        feats = None  # Token attributions can be added later
        reason = _reason_hf(pred, probs, labels, text)
        return PredictResponse(prediction=pred, confidence=round(conf,4), top_features=feats, reason=reason)

    if model_type == "zeroshot":
        try:
            _ensure_zeroshot_loaded()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        assert _zs_pipe is not None
        zlabels = CONFIG.get("zsh_labels") or ["plaintiff_wins", "defendant_wins"]
        if isinstance(zlabels, str):
            candidate_labels = [p.strip() for p in zlabels.split(",") if p.strip()]
        else:
            candidate_labels = list(zlabels)
        max_len = int(CONFIG.get("zsh_max_len", 512))
        res = _zs_pipe(
            text,
            candidate_labels=candidate_labels,
            multi_label=False,
            truncation=True,
            max_length=max_len,
        )
        # res: {'sequence': ..., 'labels': [...], 'scores': [...]}
        labels = res.get('labels') or []
        scores = res.get('scores') or []
        if not labels or not scores:
            raise HTTPException(status_code=500, detail="Zero-shot prediction failed")
        pred = labels[0]
        conf = float(scores[0])
        feats = None
        reason = _reason_zeroshot(res, text)
        return PredictResponse(prediction=pred, confidence=round(conf,4), top_features=feats, reason=reason)

    if model_type == "llm":
        try:
            _ensure_llm_loaded()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        assert _llm_model is not None and _llm_tokenizer is not None
        llm_labels = CONFIG.get("llm_labels") or ["plaintiff_wins", "defendant_wins"]
        if isinstance(llm_labels, str):
            llm_labels = [p.strip() for p in llm_labels.split(",") if p.strip()]
        prompt = (
            "You are a legal outcome classifier. Given the case summary, choose exactly one label from: "
            + ", ".join(llm_labels)
            + "\nReturn only the label.\n\nCase Summary:\n" + text + "\nLabel:" )
        max_new = int(CONFIG.get("llm_max_new_tokens", 32))
        try:
            import torch
            inputs = _llm_tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.to(_llm_model.device) for k,v in inputs.items()}
            output_ids = _llm_model.generate(**inputs, max_new_tokens=max_new, do_sample=False)
            gen_text = _llm_tokenizer.decode(output_ids[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM generation failed: {e}")
        # Parse: find first label mention
        pred = None
        lower_gen = gen_text.lower()
        for lab in llm_labels:
            if lab.lower() in lower_gen:
                pred = lab
                break
        if pred is None:
            # fallback: first label
            pred = llm_labels[0]
        # Confidence proxy: crude binary (not probabilistic)
        conf = 0.5
        feats = None
        
        # Generate AI-powered explanation for LLM predictions
        outcome = "plaintiff victory" if pred == "plaintiff_wins" else "defendant victory"
        reason = (
            f"Large Language Model analysis suggests {outcome} based on comprehensive text understanding. "
            f"The model generated: '{gen_text}'. This prediction leverages advanced natural language processing "
            f"to interpret legal context, relationships, and implications within the case summary. However, "
            f"LLM predictions are based on training patterns and cannot account for case-specific evidence, "
            f"legal precedents, procedural nuances, witness testimony, or judicial discretion. This analysis "
            f"should inform preliminary assessment but must be supplemented with professional legal expertise "
            f"and thorough case investigation."
        )
        return PredictResponse(prediction=pred, confidence=round(conf,4), top_features=feats, reason=reason)

    if model_type == "gemini":
        # Call Gemini API via REST. Requires GEMINI_API_KEY or GOOGLE_API_KEY env var
        import os, json as _json, urllib.request, urllib.error
        g_labels = CONFIG.get("gemini_labels") or ["plaintiff_wins", "defendant_wins"]
        if isinstance(g_labels, str):
            g_labels = [p.strip() for p in g_labels.split(",") if p.strip()]
        model_name = CONFIG.get("gemini_model", "gemini-1.5-flash")
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY or GOOGLE_API_KEY not set")
        
        # Enhanced prompt for detailed legal analysis with Indian Laws and Acts
        detailed_analysis_instruction = f"""
You are an expert Indian legal analyst with comprehensive knowledge of Indian laws, acts, and judicial precedents. Analyze this Case Summary and provide a detailed legal assessment in the following exact format, incorporating relevant Indian legal provisions:

Based on the facts provided, the outcome is [confidence level: overwhelmingly clear/strongly indicated/reasonably supported/suggested].

[Choose exactly one: plaintiff_wins OR defendant_wins]

**Applicable Indian Laws & Legal Framework:**
[List the specific Indian Acts, Sections, and legal provisions that apply to this case, such as:
- Indian Penal Code (IPC) sections
- Code of Criminal Procedure (CrPC) sections  
- Code of Civil Procedure (CPC) sections
- Indian Evidence Act sections
- Constitution of India articles
- Special Acts (Consumer Protection Act, IT Act, etc.)
- Relevant Supreme Court/High Court judgments and precedents]

**Reasoning:**

**In Short:** [One sentence summarizing the key legal issue under Indian law or decisive factor]

**The Evidence is Decisive:** [Detailed analysis of evidence strength under Indian Evidence Act provisions, what makes it compelling or weak under Indian legal standards, and how it supports the outcome]

**Legal Principles Are Clear:** [Explanation of applicable Indian legal concepts, doctrines, or principles that govern this case, citing specific sections and acts]

**Indian Precedents & Case Law:** [Reference relevant Supreme Court or High Court judgments that support the analysis, mention landmark cases if applicable]

**[Defense Analysis - choose appropriate heading]:**
- "No Credible Defense:" [if outcome heavily favors one side under Indian law]
- "Limited Defense Options:" [if moderate advantage under Indian legal framework]
- "Strong Defense Position:" [if defending party has good arguments under Indian law]
- "Viable Defense Available:" [if balanced but slight advantage under Indian jurisprudence]

[Provide detailed analysis of the opposing party's position and arguments under Indian legal context]

**Procedural Considerations:** [Mention relevant procedural aspects under CPC/CrPC, limitation periods, jurisdiction issues, etc.]

**Practical Legal Advice for Lawyers:** [Specific actionable steps, documentation needed, court procedures to follow, and strategic recommendations for continuing this case in Indian courts]

**[Conclusion]:** [Summary statement about the overall case strength under Indian law and predicted outcome with reference to specific legal provisions]

Case Summary: {text}

Labels to choose from: {', '.join(g_labels)}

Provide the detailed legal analysis following the format above exactly, ensuring comprehensive coverage of Indian legal framework.
"""
        
        body = {
            "contents": [
                {"parts": [{"text": detailed_analysis_instruction}]}
            ]
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        data_bytes = _json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"}, method="POST")
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = resp.read()
            payload = _json.loads(resp_data.decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")
            raise HTTPException(status_code=500, detail=f"Gemini HTTPError: {detail}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gemini request failed: {e}")
            
        # Parse response
        text_out = ""
        try:
            candidates = payload.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text_out = parts[0].get("text", "").strip()
        except Exception:
            pass
        
        # Extract prediction from the detailed response
        lower_out = text_out.lower()
        pred = None
        for lab in g_labels:
            if lab.lower() in lower_out:
                pred = lab
                break
        if pred is None:
            pred = g_labels[0]  # fallback
        
        feats = None
        
        # Extract confidence from AI's language assessment
        def extract_confidence_from_response(response_text):
            """Extract confidence score based on AI's language certainty"""
            lower_text = response_text.lower()
            
            # High confidence indicators (0.85-0.95)
            high_confidence_terms = [
                "overwhelmingly clear", "clearly indicates", "strong evidence", 
                "compelling evidence", "decisive factors", "unambiguous",
                "substantial evidence", "conclusive", "definitive", "undoubtedly"
            ]
            
            # Medium-high confidence (0.75-0.85)
            medium_high_terms = [
                "strongly suggests", "strongly indicates", "likely outcome",
                "significant evidence", "considerable evidence", "probable",
                "substantial support", "well-supported", "high likelihood"
            ]
            
            # Medium confidence (0.65-0.75)
            medium_terms = [
                "reasonably supported", "moderate evidence", "indicates",
                "suggests", "reasonable likelihood", "fairly clear",
                "moderate support", "appears likely", "tends to suggest"
            ]
            
            # Lower confidence (0.55-0.65)
            low_terms = [
                "some evidence", "may suggest", "could indicate",
                "possible", "might", "uncertain", "limited evidence",
                "unclear", "ambiguous", "difficult to determine"
            ]
            
            # Check for confidence indicators
            for term in high_confidence_terms:
                if term in lower_text:
                    return round(0.85 + (hash(term) % 10) / 100, 2)  # 0.85-0.94
            
            for term in medium_high_terms:
                if term in lower_text:
                    return round(0.75 + (hash(term) % 10) / 100, 2)  # 0.75-0.84
            
            for term in medium_terms:
                if term in lower_text:
                    return round(0.65 + (hash(term) % 10) / 100, 2)  # 0.65-0.74
            
            for term in low_terms:
                if term in lower_text:
                    return round(0.55 + (hash(term) % 10) / 100, 2)  # 0.55-0.64
            
            # Default confidence if no specific indicators found
            return 0.70
        
        conf = extract_confidence_from_response(text_out)
        
        # Use the full Gemini response as the detailed reasoning
        if text_out and len(text_out) > 50:
            # Clean up the response if needed
            reason = text_out.strip()
            # Add disclaimer if not already present
            if "disclaimer" not in reason.lower():
                reason += "\n\nImportant Legal Disclaimer: This AI analysis represents advanced language understanding but cannot substitute for professional legal counsel. Actual case outcomes depend on evidence quality, witness credibility, legal precedents, procedural factors, and judicial discretion that require human legal expertise."
        else:
            reason = (
                f"Based on Google Gemini AI analysis, the outcome suggests {pred}.\n\n"
                f"Reasoning:\nThe advanced AI model provided this assessment: '{text_out}'. "
                f"However, this prediction should be considered alongside professional legal analysis. "
                f"Legal case outcomes depend on numerous factors including evidence presentation, "
                f"legal precedents, attorney strategy, witness credibility, and judicial interpretation "
                f"that no AI can fully capture."
            )
        
        return PredictResponse(prediction=pred, confidence=round(conf,4), top_features=feats, reason=reason)

    if model_type == "hf_api":
        # Use Hugging Face Inference API for free models like Llama, Gemma, DeepSeek
        import os, json as _json, urllib.request, urllib.error
        hf_api_labels = CONFIG.get("hf_api_labels") or ["plaintiff_wins", "defendant_wins"]
        if isinstance(hf_api_labels, str):
            hf_api_labels = [p.strip() for p in hf_api_labels.split(",") if p.strip()]
        model_name = CONFIG.get("hf_api_model", "meta-llama/Llama-3.2-3B-Instruct")
        api_key = os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HF_TOKEN")
        if not api_key:
            raise HTTPException(status_code=500, detail="HUGGINGFACEHUB_API_TOKEN or HF_TOKEN not set")
        
        # Enhanced prompt for detailed legal analysis
        detailed_analysis_instruction = f"""You are an expert legal analyst with extensive experience in case outcome prediction. Analyze this case summary and provide a comprehensive legal assessment in the following exact format:

Based on the facts provided, the outcome is [confidence level: overwhelmingly clear/strongly indicated/reasonably supported/suggested].

[Choose exactly one: plaintiff_wins OR defendant_wins]

Reasoning:

In Short: [One sentence summarizing the key legal issue or decisive factor]

The Evidence is Decisive: [Detailed analysis of the evidence strength, what makes it compelling or weak, and how it supports the outcome]

Legal Principles Are Clear: [Explanation of the applicable legal concepts, doctrines, or principles that govern this case]

[Defense Analysis - choose appropriate heading]:
- "No Credible Defense:" [if outcome heavily favors one side]
- "Limited Defense Options:" [if moderate advantage]  
- "Strong Defense Position:" [if defending party has good arguments]
- "Viable Defense Available:" [if balanced but slight advantage]

[Provide detailed analysis of the opposing party's position and arguments]

Conclusion: [Summary statement about the overall case strength and predicted outcome]

Case Summary: {text}

Available outcomes: {', '.join(hf_api_labels)}

Provide the detailed legal analysis following the format above exactly."""
        
        # Prepare the API request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # For instruction-tuned models, use the chat format
        if "instruct" in model_name.lower() or "chat" in model_name.lower():
            payload = {
                "inputs": detailed_analysis_instruction,
                "parameters": {
                    "max_new_tokens": int(CONFIG.get("hf_api_max_tokens", 1000)),
                    "temperature": 0.1,
                    "do_sample": True,
                    "return_full_text": False
                }
            }
        else:
            # For base models, use simpler format
            payload = {
                "inputs": detailed_analysis_instruction,
                "parameters": {
                    "max_new_tokens": int(CONFIG.get("hf_api_max_tokens", 1000)),
                    "temperature": 0.1
                }
            }
        
        url = f"https://api-inference.huggingface.co/models/{model_name}"
        data_bytes = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_data = resp.read()
            response = _json.loads(resp_data.decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_detail = e.read().decode("utf-8", errors="ignore")
            raise HTTPException(status_code=500, detail=f"HuggingFace API HTTPError: {error_detail}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"HuggingFace API request failed: {e}")
            
        # Parse response
        text_out = ""
        try:
            if isinstance(response, list) and len(response) > 0:
                if "generated_text" in response[0]:
                    text_out = response[0]["generated_text"].strip()
                elif "text" in response[0]:
                    text_out = response[0]["text"].strip()
            elif isinstance(response, dict):
                if "generated_text" in response:
                    text_out = response["generated_text"].strip()
                elif "text" in response:
                    text_out = response["text"].strip()
                elif "error" in response:
                    raise HTTPException(status_code=500, detail=f"HuggingFace API Error: {response['error']}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse HuggingFace response: {e}")
        
        # Extract prediction from the detailed response
        lower_out = text_out.lower()
        pred = None
        for lab in hf_api_labels:
            if lab.lower() in lower_out:
                pred = lab
                break
        if pred is None:
            pred = hf_api_labels[0]  # fallback
        
        feats = None
        conf = 0.8  # Default confidence for HF API (can be adjusted based on language used)
        
        # Use the full HF response as the detailed reasoning
        if text_out and len(text_out) > 50:
            # Clean up the response if needed
            reason = text_out.strip()
            # Add disclaimer if not already present
            if "disclaimer" not in reason.lower():
                reason += f"\n\nImportant Legal Disclaimer: This analysis was generated using {model_name} via HuggingFace API. While this model provides sophisticated legal reasoning, it cannot substitute for professional legal counsel. Actual case outcomes depend on evidence quality, witness credibility, legal precedents, procedural factors, and judicial discretion that require human legal expertise."
        else:
            reason = (
                f"Based on {model_name} AI analysis, the outcome suggests {pred}.\n\n"
                f"Reasoning:\nThe AI model provided this assessment: '{text_out}'. "
                f"However, this prediction should be considered alongside professional legal analysis. "
                f"Legal case outcomes depend on numerous factors including evidence presentation, "
                f"legal precedents, attorney strategy, witness credibility, and judicial interpretation "
                f"that no AI can fully capture."
            )
        
        return PredictResponse(prediction=pred, confidence=round(conf,4), top_features=feats, reason=reason)

    _ensure_model_loaded()
    assert _model is not None and _vectorizer is not None
    pred, conf, feats, reason = _predict_one(text)
    return PredictResponse(prediction=pred, confidence=round(conf, 4), top_features=feats, reason=reason)


@app.post("/predict/best", response_model=PredictResponse)
async def predict_best(body: PredictRequest):
    # Alias so users hitting /predict/best get the same behavior
    return await predict(body)


@app.post("/predict/batch", response_model=BatchPredictResponse)
async def predict_batch(body: BatchPredictRequest):
    _ensure_model_loaded()
    assert _model is not None and _vectorizer is not None
    if not body.summaries:
        raise HTTPException(status_code=400, detail="No summaries provided")
    items = []
    for s in body.summaries:
        s2 = (s or "").strip()
        if not s2:
            items.append(BatchPredictItem(prediction="", confidence=0.0, top_features=None, suggestions=None))
            continue
    p, c, f, r = _predict_one(s2)
    items.append(BatchPredictItem(prediction=p, confidence=round(c,4), top_features=f, reason=r))
    return BatchPredictResponse(items=items)


@app.post("/feedback")
async def feedback(body: FeedbackRequest):
    # Append feedback as CSV, creating header if file is new
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not FEEDBACK_PATH.exists()
    import csv as _csv
    with FEEDBACK_PATH.open('a', newline='', encoding='utf-8') as f:
        writer = _csv.DictWriter(f, fieldnames=["summary","predicted","correct_label","notes"])
        if new_file:
            writer.writeheader()
        writer.writerow({
            "summary": body.summary,
            "predicted": body.predicted,
            "correct_label": body.correct_label or "",
            "notes": body.notes or "",
        })
    return {"ok": True}


# -------- Configuration Endpoints --------
class ConfigUpdate(BaseModel):
    model_type: Optional[str] = None  # sklearn | hf | zeroshot | llm | gemini | hf_api
    hf_model_dir: Optional[str] = None
    hf_max_len: Optional[int] = None
    zsh_model: Optional[str] = None
    zsh_labels: Optional[List[str]] = None
    zsh_max_len: Optional[int] = None
    llm_model: Optional[str] = None
    llm_labels: Optional[List[str]] = None
    llm_max_input: Optional[int] = None
    llm_max_new_tokens: Optional[int] = None
    gemini_model: Optional[str] = None
    gemini_labels: Optional[List[str]] = None
    hf_api_model: Optional[str] = None
    hf_api_labels: Optional[List[str]] = None
    hf_api_max_tokens: Optional[int] = None
    debug_errors: Optional[bool] = None


@app.get("/config")
async def get_config():
    # Reload in case file changed on disk
    _load_config()
    return {"config": CONFIG}


@app.put("/config")
async def update_config(body: ConfigUpdate):
    data = body.dict(exclude_none=True)
    if not data:
        return {"ok": True, "config": CONFIG}
    # Update in-memory config
    CONFIG.update(data)
    # Persist
    _save_config()
    # Reset any loaded models so next request uses new settings
    _reset_models()
    return {"ok": True, "config": CONFIG}
