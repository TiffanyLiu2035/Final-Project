from typing import Tuple, Optional
import warnings
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.linear_model import SGDClassifier, LogisticRegression
from sklearn.metrics import roc_auc_score, log_loss
from joblib import dump, load

class CTRModel:
    def __init__(self, model_type: str = "sgd_log", random_state: int = 42):
        self.model_type = model_type
        if model_type == "sgd_log":
            self.model = SGDClassifier(loss="log_loss", penalty="l2", alpha=1e-5, max_iter=5, random_state=random_state)
        elif model_type == "logreg":
            self.model = LogisticRegression(max_iter=200, n_jobs=-1)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")
    
    def fit(self, X: csr_matrix, y: np.ndarray):
        self.model.fit(X, y)
        return self
    
    def predict_proba(self, X: csr_matrix) -> np.ndarray:
        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(X)[:, 1]
        else:
            # decision_function to probability via sigmoid
            scores = self.model.decision_function(X)
            proba = 1.0 / (1.0 + np.exp(-scores))
        return proba
    
    def evaluate(self, X: csr_matrix, y: np.ndarray) -> Tuple[float, float]:
        p = self.predict_proba(X)
        auc = roc_auc_score(y, p) if y.sum() > 0 and y.sum() < len(y) else float("nan")
        ll = log_loss(y, np.clip(p, 1e-6, 1-1e-6))
        return auc, ll
    
    def save(self, path: str):
        dump({"model_type": self.model_type, "model": self.model}, path)
    
    @staticmethod
    def load(path: str) -> "CTRModel":
        with warnings.catch_warnings():
            try:
                from sklearn.exceptions import InconsistentVersionWarning
                warnings.simplefilter("ignore", InconsistentVersionWarning)
            except ImportError:
                warnings.filterwarnings("ignore", message="Trying to unpickle estimator")
            obj = load(path)
        m = CTRModel(model_type=obj["model_type"])  # will construct default
        m.model = obj["model"]
        return m


