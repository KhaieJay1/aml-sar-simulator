import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from ..models import (
    Customer,
    Transaction,
    SanctionsEntry,
    TypologyAlert,
    TypologyType,
    AlertSeverity
)

def normalize_text(text: str) -> str:
    """Normalize text by lowercasing, stripping punctuation, and extra whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())

def levenshtein_ratio(s1: str, s2: str) -> float:
    """Compute normalized Levenshtein similarity ratio between 0.0 and 1.0."""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    
    len1, len2 = len(s1), len(s2)
    # Initialize DP matrix
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # deletion
                dp[i][j - 1] + 1,      # insertion
                dp[i - 1][j - 1] + cost # substitution
            )

    dist = dp[len1][len2]
    max_len = max(len1, len2)
    return max(0.0, 1.0 - (dist / max_len))

def jaro_winkler_similarity(s1: str, s2: str, prefix_weight: float = 0.1) -> float:
    """Standard Jaro-Winkler similarity widely utilized in KYC / Watchlist screening."""
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    len1, len2 = len(s1), len(s2)
    match_distance = max(len1, len2) // 2 - 1
    if match_distance < 0:
        match_distance = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2

    matches = 0
    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    # Calculate transpositions
    k = 0
    transpositions = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    transpositions //= 2

    # Jaro metric
    jaro = (
        (matches / len1) +
        (matches / len2) +
        ((matches - transpositions) / matches)
    ) / 3.0

    # Winkler prefix scale (common prefix up to 4 characters)
    prefix_len = 0
    for i in range(min(4, len1, len2)):
        if s1[i] == s2[i]:
            prefix_len += 1
        else:
            break

    jw = jaro + (prefix_len * prefix_weight * (1.0 - jaro))
    return min(1.0, max(0.0, jw))

def token_sort_similarity(s1: str, s2: str) -> float:
    """Sorts word tokens before comparing to handle inverted name order."""
    t1 = " ".join(sorted(normalize_text(s1).split()))
    t2 = " ".join(sorted(normalize_text(s2).split()))
    return jaro_winkler_similarity(t1, t2)

def compute_composite_match_score(name1: str, name2: str) -> float:
    """
    Computes industry-standard composite match score combining direct sequence
    similarity (Jaro-Winkler + Levenshtein) and token-sorted similarity.
    This guarantees robust handling of transposed first/last names.
    """
    n1, n2 = normalize_text(name1), normalize_text(name2)
    if n1 == n2:
        return 1.0
    
    jw_direct = jaro_winkler_similarity(n1, n2)
    lev_direct = levenshtein_ratio(n1, n2)
    direct_score = (0.70 * jw_direct) + (0.30 * lev_direct)

    # Token sort handles transposed names ("Smith John" vs "John Smith")
    ts = token_sort_similarity(n1, n2)

    # Best representation governs the score
    score = max(direct_score, ts * 0.98 if ts >= 0.80 else (0.5 * ts + 0.5 * direct_score))
    return round(score, 4)

class SanctionsScreeningEngine:
    """
    Screens customers and counterparties against synthetic Sanctions & PEP Watchlists
    using multi-algorithm fuzzy matching.
    """
    def __init__(self, sanctions_list: List[SanctionsEntry], match_threshold: float = 0.82):
        self.sanctions_list = sanctions_list
        self.threshold = match_threshold

    def screen_name(self, query_name: str) -> List[Tuple[SanctionsEntry, float, str]]:
        """
        Screens a single name against all sanctions entries and aliases.
        Returns list of (SanctionsEntry, match_score, matched_name).
        """
        matches = []
        if not query_name or len(query_name.strip()) < 3:
            return matches

        for entry in self.sanctions_list:
            best_score = compute_composite_match_score(query_name, entry.primary_name)
            matched_on = entry.primary_name

            # Check aliases
            for alias in entry.aliases:
                alias_score = compute_composite_match_score(query_name, alias)
                if alias_score > best_score:
                    best_score = alias_score
                    matched_on = alias

            if best_score >= self.threshold:
                matches.append((entry, best_score, matched_on))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def screen_customers(self, customers: List[Customer]) -> List[TypologyAlert]:
        alerts = []
        for cust in customers:
            # Check PEP flag or watchlist match
            matches = self.screen_name(cust.full_name)
            if matches:
                top_match, score, matched_alias = matches[0]
                risk_score = round(score * 100.0, 1)
                severity = AlertSeverity.CRITICAL if score >= 0.90 else AlertSeverity.HIGH
                
                desc = (
                    f"Sanctions / PEP Watchlist Hit ({score*100:.1f}% match): Customer '{cust.full_name}' "
                    f"matched entry '{top_match.primary_name}' (matched on '{matched_alias}') "
                    f"under program '{top_match.sanctions_program}'. Reason: {top_match.listing_reason}"
                )

                alerts.append(TypologyAlert(
                    alert_id=f"ALT-SNC-{cust.customer_id[:6]}-{datetime.now().strftime('%H%M%S%f')[:8]}",
                    typology=TypologyType.SANCTIONS_PEP_MATCH,
                    customer_id=cust.customer_id,
                    risk_score=risk_score,
                    severity=severity,
                    description=desc,
                    details={
                        "matched_sanction_id": top_match.entry_id,
                        "primary_name": top_match.primary_name,
                        "matched_string": matched_alias,
                        "similarity_score": score,
                        "program": top_match.sanctions_program,
                        "reason": top_match.listing_reason
                    },
                    created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
        return alerts

    def screen_transactions(self, transactions: List[Transaction]) -> List[TypologyAlert]:
        """Screens counterparties in transaction narratives."""
        alerts = []
        seen_counterparties: Dict[str, Tuple[SanctionsEntry, float, str]] = {}

        for tx in transactions:
            cp = tx.counterparty_name
            if not cp or len(cp.strip()) < 3:
                continue

            if cp not in seen_counterparties:
                matches = self.screen_name(cp)
                if matches:
                    seen_counterparties[cp] = matches[0]
                else:
                    seen_counterparties[cp] = None

            match_info = seen_counterparties[cp]
            if match_info:
                top_match, score, matched_alias = match_info
                risk_score = round(score * 100.0, 1)
                severity = AlertSeverity.CRITICAL if score >= 0.90 else AlertSeverity.HIGH

                desc = (
                    f"Sanctions Hit on Counterparty ({score*100:.1f}%): Payment of £{tx.amount:,.2f} "
                    f"to/from '{cp}' matches '{top_match.primary_name}' ({top_match.sanctions_program})."
                )

                alerts.append(TypologyAlert(
                    alert_id=f"ALT-TXSNC-{tx.customer_id[:6]}-{datetime.now().strftime('%H%M%S%f')[:8]}",
                    typology=TypologyType.SANCTIONS_PEP_MATCH,
                    customer_id=tx.customer_id,
                    account_id=tx.account_id,
                    risk_score=risk_score,
                    severity=severity,
                    description=desc,
                    evidence_transactions=[tx.transaction_id],
                    details={
                        "counterparty": cp,
                        "matched_sanction_id": top_match.entry_id,
                        "primary_name": top_match.primary_name,
                        "matched_string": matched_alias,
                        "similarity_score": score,
                        "program": top_match.sanctions_program,
                        "amount": tx.amount
                    },
                    created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

        return alerts
