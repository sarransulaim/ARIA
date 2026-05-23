from typing import Any, Dict, List

import pandas as pd

from app.analysis.statistics import _looks_like_date, _safe_float


class VizRecommender:

    @staticmethod
    def recommend(df: pd.DataFrame, intent: str = "") -> List[Dict[str, Any]]:
        if df.empty:
            return []

        charts: List[Dict[str, Any]] = []
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        date_cols = [c for c in df.columns if _looks_like_date(df[c])]
        cat_cols = [c for c in df.columns if c not in num_cols and c not in date_cols]
        rows_data = df.to_dict(orient="records")

        # Rule 1: date + numerics → line (and area for single metric)
        if date_cols and num_cols:
            date_col = date_cols[0]
            try:
                df_s = df.copy()
                df_s[date_col] = df_s[date_col].astype(str)
                sorted_data = df_s.sort_values(date_col).to_dict(orient="records")
            except Exception:
                sorted_data = rows_data
            charts.append({
                "type": "line",
                "title": f"{', '.join(num_cols[:3])} over time",
                "x_key": date_col,
                "y_keys": num_cols[:3],
                "data": sorted_data[:500],
            })
            if len(num_cols) == 1:
                charts.append({
                    "type": "area",
                    "title": f"{num_cols[0]} trend",
                    "x_key": date_col,
                    "y_keys": num_cols,
                    "data": sorted_data[:500],
                })

        # Rule 2: categorical + 1 numeric → bar (horizontal if >8 cats)
        elif cat_cols and len(num_cols) == 1:
            cat_col, val_col = cat_cols[0], num_cols[0]
            try:
                bar_data = df.sort_values(val_col, ascending=False).to_dict(orient="records")
            except Exception:
                bar_data = rows_data
            charts.append({
                "type": "bar_horizontal" if len(df) > 8 else "bar",
                "title": f"{val_col} by {cat_col}",
                "x_key": cat_col,
                "y_keys": [val_col],
                "data": bar_data[:50],
            })

        # Rule 3: categorical + multiple numerics → grouped bar
        elif cat_cols and len(num_cols) > 1:
            charts.append({
                "type": "bar_grouped",
                "title": f"Metrics by {cat_cols[0]}",
                "x_key": cat_cols[0],
                "y_keys": num_cols[:4],
                "data": rows_data[:50],
            })

        # Rule 4: exactly 2 numerics, no dates/cats → scatter
        elif len(num_cols) == 2 and not date_cols and not cat_cols:
            charts.append({
                "type": "scatter",
                "title": f"{num_cols[0]} vs {num_cols[1]}",
                "x_key": num_cols[0],
                "y_keys": [num_cols[1]],
                "data": rows_data[:500],
            })

        # Rule 5: stat_card per numeric column
        for col in num_cols[:4]:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if series.empty:
                continue
            charts.append({
                "type": "stat_card",
                "title": col,
                "data": {
                    "sum": _safe_float(series.sum()),
                    "mean": _safe_float(series.mean()),
                    "max": _safe_float(series.max()),
                    "count": int(len(series)),
                },
            })

        return charts
