import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    from scipy import stats as sp_stats
    _SCIPY = True
except ImportError:
    _SCIPY = False


def _safe_float(v) -> Optional[float]:
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _looks_like_date(series: pd.Series) -> bool:
    name = str(series.name).lower()
    if any(k in name for k in ("date", "time", "month", "year", "week", "day", "period", "quarter")):
        return True
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    sample = series.dropna().head(5)
    if sample.empty:
        return False
    try:
        pd.to_datetime(sample, infer_datetime_format=True)
        return True
    except Exception:
        return False


class StatisticsEngine:

    @staticmethod
    def build_dataframe(columns: List[str], rows: List[List[Any]]) -> pd.DataFrame:
        if not columns or not rows:
            return pd.DataFrame(columns=columns or [])
        df = pd.DataFrame(rows, columns=columns)
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors="ignore")
            except Exception:
                pass
        return df

    @staticmethod
    def _numeric_cols(df: pd.DataFrame) -> List[str]:
        return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    @staticmethod
    def _profile_column(series: pd.Series) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "name": str(series.name),
            "count": int(len(series)),
            "nulls": int(series.isna().sum()),
        }
        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            if clean.empty:
                out["type"] = "numeric"
                return out
            q1 = float(clean.quantile(0.25))
            q3 = float(clean.quantile(0.75))
            iqr = q3 - q1
            lb, ub = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            out.update({
                "type": "numeric",
                "min": _safe_float(clean.min()),
                "max": _safe_float(clean.max()),
                "mean": _safe_float(clean.mean()),
                "median": _safe_float(clean.median()),
                "std": _safe_float(clean.std()),
                "p25": _safe_float(q1),
                "p75": _safe_float(q3),
                "outlier_count": int(((clean < lb) | (clean > ub)).sum()),
            })
        else:
            vc = series.dropna().value_counts()
            out.update({
                "type": "categorical",
                "unique_count": int(series.nunique()),
                "top_values": [
                    {"value": str(v), "count": int(c)}
                    for v, c in vc.head(5).items()
                ],
            })
        return out

    @staticmethod
    def profile_dataset(df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty:
            return {"row_count": 0, "column_count": 0, "columns": []}
        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": [StatisticsEngine._profile_column(df[c]) for c in df.columns],
        }

    @staticmethod
    def correlation_matrix(df: pd.DataFrame) -> Dict[str, Any]:
        num = StatisticsEngine._numeric_cols(df)
        if len(num) < 2:
            return {"available": False, "reason": "Need at least 2 numeric columns"}
        sub = df[num].dropna()
        if len(sub) < 3:
            return {"available": False, "reason": "Too few rows for correlation"}
        corr = sub.corr(method="pearson")
        strong: List[Dict] = []
        for i, c1 in enumerate(num):
            for c2 in num[i + 1:]:
                r = _safe_float(corr.loc[c1, c2])
                if r is not None and abs(r) >= 0.5:
                    strong.append({
                        "col1": c1, "col2": c2, "r": round(r, 3),
                        "strength": "strong" if abs(r) >= 0.7 else "moderate",
                    })
        matrix = {
            c: {o: _safe_float(corr.loc[c, o]) for o in num}
            for c in num
        }
        return {
            "available": True,
            "matrix": matrix,
            "strong_pairs": sorted(strong, key=lambda x: abs(x["r"]), reverse=True),
        }

    @staticmethod
    def detect_trend(df: pd.DataFrame, date_col: str, value_col: str) -> Dict[str, Any]:
        if date_col not in df.columns or value_col not in df.columns:
            return {"available": False, "reason": "Column not found"}
        try:
            tmp = df.copy()
            tmp["_t"] = pd.to_datetime(tmp[date_col], infer_datetime_format=True, errors="coerce")
        except Exception:
            return {"available": False, "reason": "Cannot parse date column"}
        tmp = tmp.dropna(subset=["_t", value_col]).sort_values("_t")
        if len(tmp) < 3:
            return {"available": False, "reason": "Too few data points"}
        t0 = tmp["_t"].iloc[0]
        x = np.array([(d - t0).days for d in tmp["_t"]], dtype=float)
        y = pd.to_numeric(tmp[value_col], errors="coerce").values
        mask = ~np.isnan(y)
        x, y = x[mask], y[mask]
        if len(x) < 3:
            return {"available": False, "reason": "Too few numeric values"}
        if _SCIPY:
            slope, _, r, p, _ = sp_stats.linregress(x, y)
            return {
                "available": True,
                "slope_per_day": _safe_float(slope),
                "r_squared": _safe_float(r ** 2),
                "p_value": _safe_float(p),
                "significant": bool(p < 0.05),
                "direction": "up" if slope > 0 else ("down" if slope < 0 else "flat"),
                "n_points": int(len(x)),
            }
        # Manual fallback
        n = len(x)
        xm, ym = x.mean(), y.mean()
        slope = float(np.dot(x - xm, y - ym) / (np.dot(x - xm, x - xm) or 1))
        y_pred = slope * x + (ym - slope * xm)
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - ym) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        return {
            "available": True,
            "slope_per_day": _safe_float(slope),
            "r_squared": _safe_float(r2),
            "p_value": None,
            "significant": None,
            "direction": "up" if slope > 0 else ("down" if slope < 0 else "flat"),
            "n_points": int(n),
        }

    @staticmethod
    def compare_groups(df: pd.DataFrame, group_col: str, value_col: str) -> Dict[str, Any]:
        if group_col not in df.columns or value_col not in df.columns:
            return {"available": False, "reason": "Column not found"}
        tmp = df.copy()
        tmp[value_col] = pd.to_numeric(tmp[value_col], errors="coerce")
        tmp = tmp.dropna(subset=[group_col, value_col])
        groups = {
            str(k): grp[value_col].values
            for k, grp in tmp.groupby(group_col)
            if len(grp) >= 2
        }
        if len(groups) < 2:
            return {"available": False, "reason": "Need at least 2 groups with 2+ values each"}
        stats_per_group = {
            name: {
                "mean": _safe_float(vals.mean()),
                "std": _safe_float(vals.std()),
                "count": int(len(vals)),
            }
            for name, vals in groups.items()
        }
        result: Dict[str, Any] = {"available": True, "groups": stats_per_group}
        if _SCIPY:
            keys = list(groups.keys())
            if len(keys) == 2:
                t, p = sp_stats.ttest_ind(groups[keys[0]], groups[keys[1]], equal_var=False)
                result.update({"test": "welch_t", "t_statistic": _safe_float(t),
                                "p_value": _safe_float(p), "significant": bool(p < 0.05)})
            else:
                f, p = sp_stats.f_oneway(*groups.values())
                result.update({"test": "one_way_anova", "f_statistic": _safe_float(f),
                                "p_value": _safe_float(p), "significant": bool(p < 0.05)})
        return result

    @staticmethod
    def auto_analyze(df: pd.DataFrame, intent: str = "") -> Dict[str, Any]:
        if df.empty:
            return {"profile": {"row_count": 0}}
        out: Dict[str, Any] = {"profile": StatisticsEngine.profile_dataset(df)}
        num = StatisticsEngine._numeric_cols(df)
        dates = [c for c in df.columns if _looks_like_date(df[c])]
        cats = [c for c in df.columns if c not in num and c not in dates]
        if len(num) >= 2:
            out["correlation"] = StatisticsEngine.correlation_matrix(df)
        if dates and num:
            out["trend"] = StatisticsEngine.detect_trend(df, dates[0], num[0])
        if cats and num:
            out["group_comparison"] = StatisticsEngine.compare_groups(df, cats[0], num[0])
        return out
